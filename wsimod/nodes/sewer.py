# -*- coding: utf-8 -*-
"""Created on Mon Nov 15 14:20:36 2021.

@author: bdobson
Converted to totals on 2022-05-03
"""
from typing import Any, Dict

from wsimod.core import constants
from wsimod.nodes.nodes import Node
from wsimod.nodes.tanks import QueueTank


class Sewer(Node):
    """"""

    def __init__(
        self,
        name,
        capacity=0,
        pipe_time=0,  # Sewer to sewer travel time
        pipe_timearea={0: 1},
        chamber_area=1,
        chamber_floor=10,
        data_input_dict={},
    ):
        """Sewer node that has a QueueTank and storage capacity. Think carefully about
        parameterising this tank, because of course the amount of water that can flow
        through a sewer in a timestep is different in reality than in a.

        steady state (e.g., a sewer that can handle a peak of 6m3/s in practice could
        not handle 6 * 86400 m3 of water in a day because that water does not flow
        uniformly over the day).

        Args:
            name (str): node name
            capacity (float, optional): Sewer tank capacity. Defaults to 0.
            pipe_time (float, optional): Number of timesteps to spend in the queue of
                the sewer tank. Defaults to 0.
            pipe_timearea (dict, optional): Time area diagram that enables flows to
                take a range of different durations to 'traverse' the tank. The keys
                of the dict are the number of timesteps while the values are the
                proportion of flow. E.g., {0 : 0.7, 1 : 0.3} means 70% of flow takes
                0 timesteps and 30% takes 1 timesteps.
            chamber_area (float, optional): Sewer tank area. Defaults to 1.
            chamber_floor (float, optional): Sewer tank datum. Defaults to 10.
            data_input_dict (dict, optional): Dictionary of data inputs relevant for
                the node (though I don't think it is used). Defaults to {}.

        NOTE that currently the queuetank either applies the pipe_timearea
        (push_set_land) OR the pipe_time (push_set_sewer). Though this behaviour
        could be changed by setting the number_of_timesteps property to pipe_time of
        the sewer_tank and removing the pipe_time setting in push_set_sewer.

        Functions intended to call in orchestration:
            make_discharge

        Key assumptions:
            - Sewer networks can be represented in an aggregated manner, where
                the behaviour of collections of manholes/pipes can be captured
                in a single component.
            - Travel time of water received from either `land.py/Land` objects
                or `demand.py/Demand` objects is assumed to be received as a
                non-point source and thus can be represented with the time-area
                method.
            - Travel time of water from an upstream `Sewer` object has a fixed
                travel time through the node.
            - The flow capacity of sewer network can be represented as with a
                `Tank`.
            - The `Sewer` object is not currently biochemically active.

        Input data and parameter requirements:
            - `pipe_timearea` is a dictionary containing the timearea diagram.
                _Units_: duration of flow (in timesteps) and proportion of flow
            - `pipe_time` describes the travel time of water received from upstream
                `Sewer`
                objects.
                _Units_: number of timesteps
            - `capacity`, `chamber_area`, `chamber_datum` describe the dimensions of the
                `Tank` that controls flow.
                _Units_: cubic metres, squared metres, metres
        """
        # Set parameters
        self.capacity = capacity
        self.pipe_time = pipe_time
        self.pipe_timearea = pipe_timearea
        self.chamber_area = chamber_area
        self.chamber_floor = chamber_floor
        # TODO I don't think this is used..
        self.data_input_dict = data_input_dict

        # Update args
        super().__init__(name)

        # Update handlers
        self.push_set_handler["Sewer"] = self.push_set_sewer
        self.push_set_handler["default"] = self.push_set_sewer
        self.push_set_handler["Land"] = self.push_set_land
        self.push_set_handler["Demand"] = self.push_set_land

        self.push_check_handler["default"] = self.push_check_sewer
        self.push_check_handler["Sewer"] = self.push_check_sewer
        self.push_check_handler["Demand"] = self.push_check_sewer
        self.push_check_handler["Land"] = self.push_check_sewer

        # Create sewer tank
        # TODO this might work better as a ResidenceTank (maybe also decay?)
        self.sewer_tank = QueueTank(
            capacity=self.capacity,
            number_of_timesteps=0,
            datum=self.chamber_floor,
            area=self.chamber_area,
        )

        # Mass balance
        self.mass_balance_ds.append(lambda: self.sewer_tank.ds())

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the sewer.

        Enables a user to override any of the following parameters:
        capacity, chamber_area, chamber_floor, pipe_time, pipe_timearea.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.capacity = overrides.pop("capacity", self.capacity)
        self.chamber_area = overrides.pop("chamber_area", self.chamber_area)
        self.chamber_floor = overrides.pop("chamber_floor", self.chamber_floor)
        self.sewer_tank.capacity = self.capacity
        self.sewer_tank.area = self.chamber_area
        self.sewer_tank.datum = self.chamber_floor

        self.pipe_time = overrides.pop("pipe_time", self.pipe_time)
        if "pipe_timearea" in overrides.keys():
            pipe_timearea_sum = sum([v for k, v in overrides["pipe_timearea"].items()])
            if pipe_timearea_sum != 1:
                print(
                    "ERROR: the sum of pipe_timearea in the overrides dict \
			is not equal to 1, please check it"
                )
        self.pipe_timearea = overrides.pop("pipe_timearea", self.pipe_timearea)
        super().apply_overrides(overrides)

    def push_check_sewer(self, vqip=None):
        """Generic push check, simply looks at excess.

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            excess (dict): Sewer tank excess
        """
        # Get excess
        excess = self.sewer_tank.get_excess()
        if vqip is None:
            return excess
        # Limit respone to vqip volume
        excess = self.v_change_vqip(excess, min(excess["volume"], vqip["volume"]))
        return excess

    def push_set_sewer(self, vqip):
        """Generic push request setting that implements basic queue travel time (it does
        NOT implement timearea travel time). Updates the sewer tank storage. Assumes
        that the inflow arc has accurately calculated capacity with push_check_sewer,
        thus the water is forced.

        Args:
            vqip (dict): A VQIP amount of water to push

        Returns:
            (dict): A VQIP amount of water that was not received
        """
        # Sewer to sewer push, update queued tank
        return self.sewer_tank.push_storage(vqip, time=self.pipe_time)

    def push_set_land(self, vqip):
        """Push request that applies pipe_timearea (see __init__ for description). As
        with push_set_sewer, push is also forced. Used to receive flow from land or
        demand that is assumed to occur widely across some kind of sewer catchment.

        Args:
            vqip (dict): A VQIP amount to be pushed

        Returns:
            (dict): A VQIP amount that was not received
        """
        # Land/demand to sewer push, update queued tank

        reply = self.empty_vqip()

        # Iterate over timearea diagram
        for time, normalised in self.pipe_timearea.items():
            vqip_ = self.v_change_vqip(vqip, vqip["volume"] * normalised)
            reply_ = self.sewer_tank.push_storage(vqip_, time=time)
            reply = self.sum_vqip(reply, reply_)

        return reply

    def make_discharge(self):
        """Function to trigger downstream sewer flow.

        Updates sewer tank travel time, pushes to WWTW, then sewer, then CSO. May flood
        land if, after these attempts, the sewer tank storage is above capacity.
        """
        self.sewer_tank.internal_arc.update_queue(direction="push")
        # TODO... do I need to do anything with this backflow... does it ever happen?
        # Discharge to Sewer if possible
        # remaining = self.push_distributed(self.sewer_tank.active_storage,
        #                                 of_type = 'Sewer',
        #                                 tag = 'Sewer')

        # #Discharge to WWTW if possible
        # remaining = self.push_distributed(remaining,
        #                                 of_type = 'WWTW',
        #                                 tag = 'Sewer')

        # #CSO discharge
        # remaining = self.push_distributed(remaining,
        #                                   of_type = ['Node', 'River'])

        remaining = self.push_distributed(self.sewer_tank.active_storage)

        # TODO backflow can cause mass balance errors here

        # Update tank
        sent = self.extract_vqip(self.sewer_tank.active_storage, remaining)
        reply = self.sewer_tank.pull_storage_exact(sent)
        if (reply["volume"] - sent["volume"]) > constants.FLOAT_ACCURACY:
            print("Miscalculated tank storage in discharge")

        # Flood excess
        ponded = self.sewer_tank.pull_ponded()
        if ponded["volume"] > constants.FLOAT_ACCURACY:
            reply_ = self.push_distributed(ponded, of_type=["Land"], tag="Sewer")
            reply_ = self.sewer_tank.push_storage(reply_, time=0, force=True)
            if reply_["volume"]:
                print("ponded water cant reenter")

    def end_timestep(self):
        """Overwrite end_timestep behaviour to update tank variables."""
        self.sewer_tank.end_timestep()

    def reinit(self):
        """Call Tank reinit."""
        self.sewer_tank.reinit()


class EnfieldFoulSewer(Sewer):
    """"""

    # TODO: combine with sewer
    def __init__(
        self,
        name,
        capacity=0,
        pipe_time=0,  # Sewer to sewer travel time
        pipe_timearea={0: 1},
        chamber_area=1,
        chamber_floor=10,
        data_input_dict={},
    ):
        """Alternate legacy sewer class...

        I dont think this is needed any more.
        """
        # TODO above

        super().__init__(
            name,
            capacity=capacity,
            pipe_time=pipe_time,
            pipe_timearea=pipe_timearea,
            chamber_area=chamber_area,
            chamber_floor=chamber_floor,
            data_input_dict=data_input_dict,
        )
        self.__class__.__name__ = "Sewer"

    def make_discharge(self):
        """"""
        _ = self.sewer_tank.internal_arc.update_queue(direction="push")

        # Discharge downstream
        if (
            self.sewer_tank.storage["volume"]
            > self.storm_exchange * self.sewer_tank.capacity
        ):
            exchange_v = min(
                (1 - self.storm_exchange) * self.sewer_tank.capacity,
                self.sewer_tank.active_storage["volume"],
            )
            exchange = self.v_change_vqip(self.sewer_tank.active_storage, exchange_v)
            remaining = self.push_distributed(exchange)
            sent_to_exchange = self.v_change_vqip(
                self.sewer_tank.active_storage, exchange_v - remaining["volume"]
            )
            self.sewer_tank.pull_storage(sent_to_exchange)

        remaining = self.push_distributed(
            self.sewer_tank.active_storage, of_type=["Waste"]
        )

        # Update tank
        sent = self.sewer_tank.active_storage["volume"] - remaining["volume"]
        sent = self.v_change_vqip(self.sewer_tank.active_storage, sent)
        reply = self.sewer_tank.pull_storage(sent)
        if (reply["volume"] - sent["volume"]) > constants.FLOAT_ACCURACY:
            print("Miscalculated tank storage in discharge")
