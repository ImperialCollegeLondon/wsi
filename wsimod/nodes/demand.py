# -*- coding: utf-8 -*-
"""Created on Mon Nov 15 14:20:36 2021.

@author: bdobson

Converted to totals BD 2022-05-03
"""
from typing import Any, Dict

from wsimod.core import constants
from wsimod.nodes.nodes import Node


class Demand(Node):
    """"""

    def __init__(
        self,
        name,
        constant_demand=0,
        pollutant_load={},
        data_input_dict={},
    ):
        """Node that generates and moves water. Currently only subclass
        ResidentialDemand is in use.

        Args:
            name (str): node name constant_demand (float, optional): A constant portion
            of demand if no subclass
                is used. Defaults to 0.
            pollutant_load (dict, optional): Pollutant mass per timestep of
            constant_demand.
                Defaults to 0.
            data_input_dict (dict, optional):  Dictionary of data inputs relevant for
                the node (temperature). Keys are tuples where first value is the name of
                the variable to read from the dict and the second value is the time.
                Defaults to {}

        Functions intended to call in orchestration:
            create_demand
        """
        # TODO should temperature be defined in pollutant dict? TODO a lot of this
        # should be moved to ResidentialDemand Assign parameters
        self.constant_demand = constant_demand
        self.pollutant_load = pollutant_load
        # Update args
        super().__init__(name, data_input_dict=data_input_dict)
        # Update handlers
        self.push_set_handler["default"] = self.push_set_deny
        self.push_check_handler["default"] = self.push_check_deny
        self.pull_set_handler["default"] = self.pull_set_deny
        self.pull_check_handler["default"] = self.pull_check_deny

        # Initialise states
        self.total_demand = self.empty_vqip()
        self.total_backup = self.empty_vqip()  # ew
        self.total_received = self.empty_vqip()

        # Mass balance Because we assume demand is always satisfied received water
        # 'disappears' for mass balance and consumed water 'appears' (this makes)
        # introduction of pollutants easy
        self.mass_balance_in.append(lambda: self.total_demand)
        self.mass_balance_out.append(lambda: self.total_backup)
        self.mass_balance_out.append(lambda: self.total_received)

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the sewer.

        Enables a user to override any of the following parameters:
        constant_demand, pollutant_load.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.constant_demand = overrides.pop("constant_demand", self.constant_demand)
        self.pollutant_load.update(overrides.pop("pollutant_load", {}))
        super().apply_overrides(overrides)

    def create_demand(self):
        """Function to call get_demand, which should return a dict with keys that match
        the keys in directions.

        A dict that determines how to push_distributed the generated wastewater/garden
        irrigation. Water is drawn from attached nodes.
        """
        demand = self.get_demand()
        total_requested = 0
        for dem in demand.values():
            total_requested += dem["volume"]

        self.total_received = self.pull_distributed({"volume": total_requested})

        # TODO Currently just assume all water is received and then pushed onwards
        if (total_requested - self.total_received["volume"]) > constants.FLOAT_ACCURACY:
            print(
                "demand deficit of {2} at {0} on {1}".format(
                    self.name, self.t, total_requested - self.total_received["volume"]
                )
            )

        directions = {
            "garden": {"tag": ("Demand", "Garden"), "of_type": "Land"},
            "house": {"tag": "Demand", "of_type": "Sewer"},
            "default": {"tag": "default", "of_type": None},
        }

        # Send water where it needs to go
        for key, item in demand.items():
            # Distribute
            remaining = self.push_distributed(
                item, of_type=directions[key]["of_type"], tag=directions[key]["tag"]
            )
            self.total_backup = self.sum_vqip(self.total_backup, remaining)
            if remaining["volume"] > constants.FLOAT_ACCURACY:
                print("Demand not able to push")

        # Update for mass balance
        for dem in demand.values():
            self.total_demand = self.sum_vqip(self.total_demand, dem)

    def get_demand(self):
        """Holder function to enable constant demand generation.

        Returns:
            (dict): A VQIP that will contain constant demand
        """
        # TODO read/gen demand
        pol = self.v_change_vqip(self.empty_vqip(), self.constant_demand)
        for key, item in self.pollutant_load.items():
            pol[key] = item
        return {"default": pol}

    def end_timestep(self):
        """Reset state variable trackers."""
        self.total_demand = self.empty_vqip()
        self.total_backup = self.empty_vqip()
        self.total_received = self.empty_vqip()


class NonResidentialDemand(Demand):
    """Holder class to enable non-residential demand generation."""

    def get_demand(self):
        """Holder function.

        Returns:
            (dict): A dict of VQIPs, where the keys match with directions
                in Demand/create_demand
        """
        return {"house": self.get_demand()}


class ResidentialDemand(Demand):
    """"""

    def __init__(
        self,
        population=1,
        pollutant_load={},
        per_capita=0.12,
        gardening_efficiency=0.6 * 0.7,  # Watering efficiency by irrigated area
        data_input_dict={},  # For temperature
        constant_temp=30,
        constant_weighting=0.2,
        **kwargs,
    ):
        """Subclass of demand with functions to handle internal and external water use.

        Args:
            population (float, optional): population of node. Defaults to 1. per_capita
            (float, optional): Volume per person per timestep of water
                used. Defaults to 0.12.
            pollutant_load (dict, optional): Mass per person per timestep of
                different pollutants generated. Defaults to {}.
            gardening_efficiency (float, optional): Value between 0 and 1 that
                translates irrigation demand from GardenSurface into water requested
                from the distribution network. Should account for percent of garden that
                is irrigated and the efficacy of people in meeting their garden water
                demand. Defaults to 0.6*0.7.
            data_input_dict (dict, optional):  Dictionary of data inputs relevant for
                the node (temperature). Keys are tuples where first value is the name of
                the variable to read from the dict and the second value is the time.
                Defaults to {}
            constant_temp (float, optional): A constant temperature associated with
                generated water. Defaults to 30
            constant_weighting (float, optional): Proportion of temperature that is
                made up from by constant_temp. Defaults to 0.2.

        Key assumptions:
            - Per capita calculations to generate demand based on population.
            - Pollutant concentration of generated demand uses a fixed mass per person
              per timestep.
            - Temperature of generated wastewater is based partially on air temperature
              and partially on a constant.
            - Can interact with `land.py/GardenSurface` to simulate garden water use.

        Input data and parameter requirements:
            - `population`.
                _Units_: n
            - `per_capita`.
                _Units_: m3/timestep
            - `data_input_dict` should contain air temperature at model timestep.
                _Units_: C
        """
        self.gardening_efficiency = gardening_efficiency
        self.population = population
        self.per_capita = per_capita
        self.constant_weighting = constant_weighting
        self.constant_temp = constant_temp
        super().__init__(
            data_input_dict=data_input_dict, pollutant_load=pollutant_load, **kwargs
        )
        # Label as Demand class so that other nodes treat it the same
        self.__class__.__name__ = "Demand"

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the sewer.

        Enables a user to override any of the following parameters:
        gardening_efficiency, population, per_capita, constant_weighting, constant_temp.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.gardening_efficiency = overrides.pop(
            "gardening_efficiency", self.gardening_efficiency
        )
        self.population = overrides.pop("population", self.population)
        self.per_capita = overrides.pop("per_capita", self.per_capita)
        self.constant_weighting = overrides.pop(
            "constant_weighting", self.constant_weighting
        )
        self.constant_temp = overrides.pop("constant_temp", self.constant_temp)
        super().apply_overrides(overrides)

    def get_demand(self):
        """Overwrite get_demand and replace with custom functions.

        Returns:
            (dict): A dict of VQIPs, where the keys match with directions
                in Demand/create_demand
        """
        water_output = {}

        water_output["garden"] = self.get_garden_demand()
        water_output["house"] = self.get_house_demand()

        return water_output

    def get_garden_demand(self):
        """Calculate garden water demand in the current timestep by get_connected to all
        attached land nodes. This check should return garden water demand. Applies
        irrigation coefficient. Can function when a single population node is connected
        to multiple land nodes, however, the capacity and preferences of arcs should be
        updated to reflect what is possible based on area.

        Returns:
            vqip (dict): A VQIP of garden water use (including pollutants) to be
                pushed to land
        """
        # Get garden water demand
        excess = self.get_connected(
            direction="push", of_type="Land", tag=("Demand", "Garden")
        )["avail"]

        # Apply garden_efficiency
        excess = self.excess_to_garden_demand(excess)

        # Apply any pollutants
        vqip = self.apply_gardening_pollutants(excess)
        return vqip

    def apply_gardening_pollutants(self, excess):
        """Holder function to apply pollutants (i.e., presumably fertiliser) to the
        garden.

        Args:
            excess (float): A volume of water applied to a garden

        Returns:
            (dict): A VQIP of water that includes pollutants to be sent to land
        """
        # TODO Fertilisers are currently applied in the land node... which is
        # preferable?
        vqip = self.empty_vqip()
        vqip["volume"] = excess
        return vqip

    def excess_to_garden_demand(self, excess):
        """Apply garden_efficiency.

        Args:
            excess (float): Volume of water required to satisfy garden irrigation

        Returns:
            (float): Amount of water actually applied to garden
        """
        # TODO Anything more than this needed? (yes - population presence if eventually
        # included!)

        return excess * self.gardening_efficiency

    def get_house_demand(self):
        """Per capita calculations for household wastewater generation. Applies weighted
        temperature calculation.

        Returns:
            (dict): A VQIP containg foul water
        """
        # TODO water that is consumed but not sent onwards as foul Total water required
        consumption = self.population * self.per_capita
        # Apply pollutants
        foul = self.copy_vqip(self.pollutant_load)
        # Scale to population
        for pol in constants.ADDITIVE_POLLUTANTS:
            foul[pol] *= self.population
        # Update volume and temperature (which is weighted based on air temperature and
        # constant_temp)
        foul["volume"] = consumption
        foul["temperature"] = (
            self.get_data_input("temperature") * (1 - self.constant_weighting)
            + self.constant_temp * self.constant_weighting
        )
        return foul
