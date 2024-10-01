# -*- coding: utf-8 -*-
"""Created on Mon Nov 15 14:20:36 2021.

@author: bdobson
Converted to totals on 2022-05-03
"""
from typing import Any, Dict

from wsimod.core import constants
from wsimod.nodes.nodes import Node
from wsimod.nodes.tanks import Tank


class WTW(Node):
    """A generic Water Treatment Works (WTW) node.

    This class is a generic water treatment works node. It is intended to be
    subclassed into freshwater and wastewater treatment works (FWTW and WWTW
    respectively).
    """

    def __init__(
        self,
        name,
        treatment_throughput_capacity=10,
        process_parameters={},
        liquor_multiplier={},
        percent_solids=0.0002,
    ):
        """Generic treatment processes that apply temperature a sensitive transform of
        pollutants into liquor and solids (behaviour depends on subclass). Push requests
        are stored in the current_input state variable, but treatment must be triggered
        with treat_current_input. This treated water is stored in the discharge_holder
        state variable, which will be sent different depending on FWTW/WWTW.

        Args:
            name (str): Node name
            treatment_throughput_capacity (float, optional): Amount of volume per
                timestep of water that can be treated. Defaults to 10.
            process_parameters (dict, optional): Dict of dicts for each pollutant.
                Top level key describes pollutant. Next level key describes the
                constant portion of the transform and the temperature sensitive
                exponent portion (see core.py/DecayObj for more detailed
                explanation). Defaults to {}.
            liquor_multiplier (dict, optional): Keys for each pollutant that
                describes how much influent becomes liquor. Defaults to {}.
            percent_solids (float, optional): Proportion of volume that becomes solids.
                All pollutants that do not become effluent or liquor become solids.
                Defaults to 0.0002.

        Functions intended to call in orchestration:
            None (use FWTW or WWTW subclass)

        Key assumptions:
            - Throughput can be modelled entirely with a set capacity.
            - Pollutant reduction for the entire treatment process can be modelled
                primarily with a single (temperature sensitive) transformation for
                each pollutant.
            - Liquor and solids are tracked and calculated with proportional
                multiplier parameters.

        Input data and parameter requirements:
            - `treatment_throughput_capacity`
                _Units_: cubic metres/timestep
            - `process_parameters` contains the constant (non temperature
                sensitive) and exponent (temperature sensitive) transformations
                applied to treated water for each pollutant.
                _Units_: -
            - `liquor_multiplier` and `percent_solids` describe the proportion of
                throughput that goes to liquor/solids.
        """
        # Set/Default parameters
        self.treatment_throughput_capacity = treatment_throughput_capacity
        if len(process_parameters) > 0:
            self.process_parameters = process_parameters
        else:
            self.process_parameters = {
                x: {"constant": 0.01, "exponent": 1.001}
                for x in constants.ADDITIVE_POLLUTANTS
            }
        if len(liquor_multiplier) > 0:
            self._liquor_multiplier = liquor_multiplier
        else:
            self._liquor_multiplier = {x: 0.7 for x in constants.ADDITIVE_POLLUTANTS}
            self._liquor_multiplier["volume"] = 0.03

        self._percent_solids = percent_solids

        # Update args
        super().__init__(name)

        self.process_parameters["volume"] = {"constant": self.calculate_volume()}

        # Update handlers
        self.push_set_handler["default"] = self.push_set_deny
        self.push_check_handler["default"] = self.push_check_deny

        # Initialise parameters
        self.current_input = self.empty_vqip()
        self.treated = self.empty_vqip()
        self.liquor = self.empty_vqip()
        self.solids = self.empty_vqip()

    def calculate_volume(self):
        """Calculate the volume proportion of treated water.

        Returns:
            (float): Volume of treated water
        """
        return 1 - self._percent_solids - self._liquor_multiplier["volume"]

    @property
    def percent_solids(self):
        return self._percent_solids

    @percent_solids.setter
    def percent_solids(self, value):
        self._percent_solids = value
        self.process_parameters["volume"]["constant"] = self.calculate_volume()

    @property
    def liquor_multiplier(self):
        return self._liquor_multiplier

    @liquor_multiplier.setter
    def liquor_multiplier(self, value):
        self._liquor_multiplier.update(value)
        self.process_parameters["volume"]["constant"] = self.calculate_volume()

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        percent_solids, treatment_throughput_capacity, process_parameters (the
        entire dict does not need to be redefined, only changed values need to
        be included), liquor_multiplier (as with process_parameters).

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.percent_solids = overrides.pop("percent_solids", self._percent_solids)
        self.liquor_multiplier = overrides.pop(
            "liquor_multiplier", self._liquor_multiplier
        )
        process_parameters = overrides.pop("process_parameters", {})
        for key, value in process_parameters.items():
            self.process_parameters[key].update(value)

        self.treatment_throughput_capacity = overrides.pop(
            "treatment_throughput_capacity", self.treatment_throughput_capacity
        )
        super().apply_overrides(overrides)

    def get_excess_throughput(self):
        """How much excess treatment capacity is there.

        Returns:
            (float): Amount of volume that can still be treated this timestep
        """
        return max(self.treatment_throughput_capacity - self.current_input["volume"], 0)

    def treat_current_input(self):
        """Run treatment processes this timestep, including temperature sensitive
        transforms, liquoring, solids."""
        # Treat current input
        influent = self.copy_vqip(self.current_input)

        # Calculate effluent, liquor and solids
        discharge_holder = self.empty_vqip()

        # Assume non-additive pollutants are unchanged in discharge and are
        # proportionately mixed in liquor
        for key in constants.NON_ADDITIVE_POLLUTANTS:
            discharge_holder[key] = influent[key]
            self.liquor[key] = (
                self.liquor[key] * self.liquor["volume"]
                + influent[key] * influent["volume"] * self.liquor_multiplier["volume"]
            ) / (
                self.liquor["volume"]
                + influent["volume"] * self.liquor_multiplier["volume"]
            )

        # TODO this should probably just be for process_parameters.keys() to avoid
        # having to declare non changing parameters
        # TODO should the liquoring be temperature sensitive too? As it is the solids
        # will take the brunt of the temperature variability which maybe isn't sensible
        for key in constants.ADDITIVE_POLLUTANTS + ["volume"]:
            if key != "volume":
                # Temperature sensitive transform
                temp_factor = self.process_parameters[key]["exponent"] ** (
                    constants.DECAY_REFERENCE_TEMPERATURE - influent["temperature"]
                )
            else:
                temp_factor = 1
            # Calculate discharge
            discharge_holder[key] = (
                influent[key] * self.process_parameters[key]["constant"] * temp_factor
            )
            # Calculate liquor
            self.liquor[key] = influent[key] * self.liquor_multiplier[key]

        # Calculate solids volume
        self.solids["volume"] = influent["volume"] * self.percent_solids

        # All remaining pollutants go to solids
        for key in constants.ADDITIVE_POLLUTANTS:
            self.solids[key] = influent[key] - discharge_holder[key] - self.liquor[key]

        # Blend with any existing discharge
        self.treated = self.sum_vqip(self.treated, discharge_holder)

        if self.treated["volume"] > self.current_input["volume"]:
            print("more treated than input")

    def end_timestep(self):
        """"""
        # Reset state variables
        self.current_input = self.empty_vqip()
        self.treated = self.empty_vqip()


class WWTW(WTW):
    """Wastewater Treatment Works (WWTW) node."""

    def __init__(
        self,
        stormwater_storage_capacity=10,
        stormwater_storage_area=1,
        stormwater_storage_elevation=10,
        **kwargs,
    ):
        """A wastewater treatment works wrapper for WTW. Contains a temporary stormwater
        storage tank. Liquor is combined with current_effluent and re- treated while
        solids leave the model.

        Args:
            stormwater_storage_capacity (float, optional): Capacity of stormwater tank.
                Defaults to 10.
            stormwater_storage_area (float, optional): Area of stormwater tank.
                Defaults to 1.
            stormwater_storage_elevation (float, optional): Datum of stormwater tank.
                Defaults to 10.

        Functions intended to call in orchestration:
            calculate_discharge

            make_discharge

        Key assumptions:
            - See `wtw.py/WTW` for treatment.
            - When `treatment_throughput_capacity` is exceeded, water is first sent
                to a stormwater storage tank before denying pushes. Leftover water
                in this tank aims to be treated in subsequent timesteps.
            - Can be pulled from to simulate active wastewater effluent use.

        Input data and parameter requirements:
            - See `wtw.py/WTW` for treatment.
            - Stormwater tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
        """
        # Set parameters
        self.stormwater_storage_capacity = stormwater_storage_capacity
        self.stormwater_storage_area = stormwater_storage_area
        self.stormwater_storage_elevation = stormwater_storage_elevation

        # Update args
        super().__init__(**kwargs)

        self.end_timestep = self.end_timestep_

        # Update handlers
        self.pull_set_handler["default"] = self.pull_set_reuse
        self.pull_check_handler["default"] = self.pull_check_reuse
        self.push_set_handler["Sewer"] = self.push_set_sewer
        self.push_check_handler["Sewer"] = self.push_check_sewer
        self.push_check_handler["default"] = self.push_check_sewer
        self.push_set_handler["default"] = self.push_set_sewer

        # Create tank
        self.stormwater_tank = Tank(
            capacity=self.stormwater_storage_capacity,
            area=self.stormwater_storage_area,
            datum=self.stormwater_storage_elevation,
        )

        # Initialise states
        self.liquor_ = self.empty_vqip()
        self.previous_input = self.empty_vqip()
        self.current_input = self.empty_vqip()  # TODO is this not done in WTW?

        # Mass balance
        self.mass_balance_out.append(lambda: self.solids)  # Assume these go to landfill
        self.mass_balance_ds.append(lambda: self.stormwater_tank.ds())
        self.mass_balance_ds.append(
            lambda: self.ds_vqip(self.liquor, self.liquor_)
        )  # Change in liquor

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Apply overrides to the stormwater tank and WWTW.

        Enables a user to override any parameter of the stormwater tank, and
        then calls any overrides in WTW.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.stormwater_storage_capacity = overrides.pop(
            "stormwater_storage_capacity", self.stormwater_storage_capacity
        )
        self.stormwater_storage_area = overrides.pop(
            "stormwater_storage_area", self.stormwater_storage_area
        )
        self.stormwater_storage_elevation = overrides.pop(
            "stormwater_storage_elevation", self.stormwater_storage_elevation
        )
        self.stormwater_tank.area = self.stormwater_storage_area
        self.stormwater_tank.capacity = self.stormwater_storage_capacity
        self.stormwater_tank.datum = self.stormwater_storage_elevation
        super().apply_overrides(overrides)

    def calculate_discharge(self):
        """Clear stormwater tank if possible, and call treat_current_input."""
        # Run WWTW model

        # Try to clear stormwater
        # TODO (probably more tidy to use push_set_sewer? though maybe less
        # computationally efficient)
        excess = self.get_excess_throughput()
        if (self.stormwater_tank.get_avail()["volume"] > constants.FLOAT_ACCURACY) & (
            excess > constants.FLOAT_ACCURACY
        ):
            to_pull = min(excess, self.stormwater_tank.get_avail()["volume"])
            to_pull = self.v_change_vqip(self.stormwater_tank.storage, to_pull)
            cleared_stormwater = self.stormwater_tank.pull_storage(to_pull)
            self.current_input = self.sum_vqip(self.current_input, cleared_stormwater)

        # Run processes
        self.current_input = self.sum_vqip(self.current_input, self.liquor)
        self.treat_current_input()

    def make_discharge(self):
        """Discharge treated effluent."""
        reply = self.push_distributed(self.treated)
        self.treated = self.empty_vqip()
        if reply["volume"] > constants.FLOAT_ACCURACY:
            _ = self.stormwater_tank.push_storage(reply, force=True)
            print("WWTW couldnt push")

    def push_check_sewer(self, vqip=None):
        """Check throughput and stormwater tank capacity.

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            (dict): excess
        """
        # Get excess
        excess_throughput = self.get_excess_throughput()
        excess_tank = self.stormwater_tank.get_excess()
        # Combine tank and throughput
        vol = excess_tank["volume"] + excess_throughput
        # Update volume
        if vqip is None:
            vqip = self.empty_vqip()
        else:
            vol = min(vol, vqip["volume"])

        return self.v_change_vqip(vqip, vol)

    def push_set_sewer(self, vqip):
        """Receive water, first try to update current_input, and then stormwater tank.

        Args:
            vqip (dict): A VQIP amount to be treated and then stored

        Returns:
            (dict): A VQIP amount of water that was not treated
        """
        # Receive water from sewers
        vqip = self.copy_vqip(vqip)
        # Check if can directly be treated
        sent_direct = self.get_excess_throughput()

        sent_direct = min(sent_direct, vqip["volume"])

        sent_direct = self.v_change_vqip(vqip, sent_direct)

        self.current_input = self.sum_vqip(self.current_input, sent_direct)

        if sent_direct["volume"] == vqip["volume"]:
            # If all added to input, no problem
            return self.empty_vqip()

        # Next try temporary storage
        vqip = self.v_change_vqip(vqip, vqip["volume"] - sent_direct["volume"])

        vqip = self.stormwater_tank.push_storage(vqip)

        if vqip["volume"] < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        else:
            # TODO what to do here ???
            return vqip

    def pull_set_reuse(self, vqip):
        """Enables WWTW to receive pulls of the treated water (i.e., for wastewater
        reuse or satisfaction of environmental flows). Intended to be called in between
        calculate_discharge and make_discharge.

        Args:
            vqip (dict): A VQIP amount to be pulled (only 'volume' key is used)

        Returns:
            reply (dict): Amount of water that has been pulled
        """
        # Satisfy request with treated (volume)
        reply_vol = min(vqip["volume"], self.treated["volume"])
        # Update pollutants
        reply = self.v_change_vqip(self.treated, reply_vol)
        # Update treated
        self.treated = self.v_change_vqip(
            self.treated, self.treated["volume"] - reply_vol
        )
        return reply

    def pull_check_reuse(self, vqip=None):
        """Pull check available water. Simply returns the previous timestep's treated
        throughput. This is of course inaccurate (which may lead to slightly longer
        calulcations), but it is much more flexible. This hasn't been recently tested so
        it might be that returning treated would be fine (and more accurate!).

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            (dict): A VQIP amount of water available. Currently just the previous
                timestep's treated throughput
        """
        # Respond to request of water for reuse/MRF
        return self.copy_vqip(self.treated)

    def end_timestep_(self):
        """End timestep function to update state variables."""
        self.liquor_ = self.copy_vqip(self.liquor)
        self.previous_input = self.copy_vqip(self.current_input)
        self.current_input = self.empty_vqip()
        self.solids = self.empty_vqip()
        self.stormwater_tank.end_timestep()


class FWTW(WTW):
    """"""

    def __init__(
        self,
        service_reservoir_storage_capacity=10,
        service_reservoir_storage_area=1,
        service_reservoir_storage_elevation=10,
        service_reservoir_initial_storage=0,
        data_input_dict={},
        **kwargs,
    ):
        """A freshwater treatment works wrapper for WTW. Contains service reservoirs
        that treated water is released to and pulled from. Cannot allow deficit (thus
        any deficit is satisfied by water entering the model 'via other means'). Liquor
        and solids are sent to sewers.

        Args:
            service_reservoir_storage_capacity (float, optional): Capacity of service
                reservoirs. Defaults to 10.
            service_reservoir_storage_area (float, optional): Area of service
                reservoirs. Defaults to 1.
            service_reservoir_storage_elevation (float, optional): Datum of service
                reservoirs. Defaults to 10.
            service_reservoir_initial_storage (float or dict, optional): initial
                storage of service reservoirs (see nodes.py/Tank for details).
                Defaults to 0.
            data_input_dict (dict, optional): Dictionary of data inputs relevant for
                the node (though I don't think it is used). Defaults to {}.

        Functions intended to call in orchestration:
            treat_water

        Key assumptions:
            - See `wtw.py/WTW` for treatment.
            - Stores treated water in a service reservoir tank, with a single tank
                per `FWTW` node.
            - Aims to satisfy a throughput that would top up the service reservoirs
                until full.
            - Currently, will not allow a deficit, thus introducing water from
                'other measures' if pulls cannot fulfil demand. Behaviour under a
                deficit should be determined and validated before introducing.

        Input data and parameter requirements:
            - See `wtw.py/WTW` for treatment.
            - Service reservoir tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
        """
        # Default parameters
        self.service_reservoir_storage_capacity = service_reservoir_storage_capacity
        self.service_reservoir_storage_area = service_reservoir_storage_area
        self.service_reservoir_storage_elevation = service_reservoir_storage_elevation
        self.service_reservoir_initial_storage = service_reservoir_initial_storage
        # TODO don't think data_input_dict is used
        self.data_input_dict = data_input_dict

        # Update args
        super().__init__(**kwargs)
        self.end_timestep = self.end_timestep_

        # Update handlers
        self.pull_set_handler["default"] = self.pull_set_fwtw
        self.pull_check_handler["default"] = self.pull_check_fwtw

        self.push_set_handler["default"] = self.push_set_deny
        self.push_check_handler["default"] = self.push_check_deny

        # Initialise parameters
        self.total_deficit = self.empty_vqip()
        self.total_pulled = self.empty_vqip()
        self.previous_pulled = self.empty_vqip()
        self.unpushed_sludge = self.empty_vqip()

        # Create tanks
        self.service_reservoir_tank = Tank(
            capacity=self.service_reservoir_storage_capacity,
            area=self.service_reservoir_storage_area,
            datum=self.service_reservoir_storage_elevation,
            initial_storage=self.service_reservoir_initial_storage,
        )
        # self.service_reservoir_tank.storage['volume'] =
        # self.service_reservoir_inital_storage
        # self.service_reservoir_tank.storage_['volume'] =
        # self.service_reservoir_inital_storage

        # Mass balance
        self.mass_balance_in.append(lambda: self.total_deficit)
        self.mass_balance_ds.append(lambda: self.service_reservoir_tank.ds())
        self.mass_balance_out.append(lambda: self.unpushed_sludge)

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Apply overrides to the service reservoir tank and FWTW.

        Enables a user to override any parameter of the service reservoir tank, and
        then calls any overrides in WTW.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.service_reservoir_storage_capacity = overrides.pop(
            "service_reservoir_storage_capacity",
            self.service_reservoir_storage_capacity,
        )
        self.service_reservoir_storage_area = overrides.pop(
            "service_reservoir_storage_area", self.service_reservoir_storage_area
        )
        self.service_reservoir_storage_elevation = overrides.pop(
            "service_reservoir_storage_elevation",
            self.service_reservoir_storage_elevation,
        )

        self.service_reservoir_tank.capacity = self.service_reservoir_storage_capacity
        self.service_reservoir_tank.area = self.service_reservoir_storage_area
        self.service_reservoir_tank.datum = self.service_reservoir_storage_elevation
        super().apply_overrides(overrides)

    def treat_water(self):
        """Pulls water, aiming to fill service reservoirs, calls WTW
        treat_current_input, avoids deficit, sends liquor and solids to sewers."""
        # Calculate how much water is needed
        target_throughput = self.service_reservoir_tank.get_excess()
        target_throughput = min(
            target_throughput["volume"], self.treatment_throughput_capacity
        )

        # Pull water
        throughput = self.pull_distributed({"volume": target_throughput})

        # Calculate deficit (assume is equal to difference between previous treated
        # throughput and current throughput)
        # TODO think about this a bit more
        deficit = max(target_throughput - throughput["volume"], 0)
        # deficit = max(self.previous_pulled['volume'] - throughput['volume'], 0)
        deficit = self.v_change_vqip(self.previous_pulled, deficit)

        # Introduce deficit
        self.current_input = self.sum_vqip(throughput, deficit)

        # Track deficit
        self.total_deficit = self.sum_vqip(self.total_deficit, deficit)

        if self.total_deficit["volume"] > constants.FLOAT_ACCURACY:
            print(
                "Service reservoirs not filled at {0} on {1}".format(self.name, self.t)
            )

        # Run treatment processes
        self.treat_current_input()

        # Discharge liquor and solids to sewers
        push_back = self.sum_vqip(self.liquor, self.solids)
        rejected = self.push_distributed(push_back, of_type="Sewer")
        self.unpushed_sludge = self.sum_vqip(self.unpushed_sludge, rejected)
        if rejected["volume"] > constants.FLOAT_ACCURACY:
            print("nowhere for sludge to go")

        # Send water to service reservoirs
        excess = self.service_reservoir_tank.push_storage(self.treated)
        _ = self.service_reservoir_tank.push_storage(excess, force=True)
        if excess["volume"] > 0:
            print("excess treated water")

    def pull_check_fwtw(self, vqip=None):
        """Pull checks query service reservoirs.

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            (dict): A VQIP of availability in service reservoirs
        """
        return self.service_reservoir_tank.get_avail(vqip)

    def pull_set_fwtw(self, vqip):
        """Pull treated water from service reservoirs.

        Args:
            vqip (dict): a VQIP amount to pull

        Returns:
            pulled (dict): A VQIP amount that was successfully pulled
        """
        # Pull
        pulled = self.service_reservoir_tank.pull_storage(vqip)
        # Update total_pulled this timestep
        self.total_pulled = self.sum_vqip(self.total_pulled, pulled)
        return pulled

    def end_timestep_(self):
        """Update state variables."""
        self.service_reservoir_tank.end_timestep()
        self.total_deficit = self.empty_vqip()
        self.previous_pulled = self.copy_vqip(self.total_pulled)
        self.total_pulled = self.empty_vqip()
        self.treated = self.empty_vqip()
        self.unpushed_sludge = self.empty_vqip()

    def reinit(self):
        """Call tank reinit."""
        self.service_reservoir_tank.reinit()
