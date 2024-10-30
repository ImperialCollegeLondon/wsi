# -*- coding: utf-8 -*-
"""Created on Mon Nov 15 14:20:36 2021.

@author: bdobson Converted to totals on 2022-05-03
"""
import warnings
from math import exp
from typing import Any, Dict

from wsimod.core import constants
from wsimod.nodes.nodes import Node
from wsimod.nodes.tanks import DecayQueueTank, DecayTank, QueueTank, Tank


class Storage(Node):
    """"""

    def __init__(
        self,
        name,
        capacity=0,
        area=0,
        datum=0,
        decays=None,
        initial_storage=0,
        **kwargs,
    ):
        """A Node wrapper for a Tank or DecayTank.

        Args:
            name (str): node name capacity (float, optional): Tank capacity (see
            nodes.py/Tank). Defaults to 0. area (float, optional): Tank area (see
            nodes.py/Tank). Defaults to 0. datum (float, optional): Tank datum (see
            nodes.py/Tank). Defaults to 0. decays (dict, optional): Tank decays if
            needed, (see nodes.py/DecayTank). Defaults to None. initial_storage (float
            or dict, optional): Initial storage (see nodes.py/Tank). Defaults to 0.

        Functions intended to call in orchestration:
            distribute (optional, depends on subclass)
        """
        # Set parameters
        self.initial_storage = initial_storage
        self.capacity = capacity
        self.area = area
        self.datum = datum
        self.decays = decays
        super().__init__(name, **kwargs)

        # Create tank
        if "initial_storage" not in dir(self):
            self.initial_storage = self.empty_vqip()

        if self.decays is None:
            self.tank = Tank(
                capacity=self.capacity,
                area=self.area,
                datum=self.datum,
                initial_storage=self.initial_storage,
            )
        else:
            self.tank = DecayTank(
                capacity=self.capacity,
                area=self.area,
                datum=self.datum,
                initial_storage=self.initial_storage,
                decays=self.decays,
                parent=self,
            )
        # Update handlers
        self.push_set_handler["default"] = self.push_set_storage
        self.push_check_handler["default"] = self.tank.get_excess
        self.pull_set_handler["default"] = lambda vol: self.tank.pull_storage(vol)
        self.pull_check_handler["default"] = self.tank.get_avail

        # Mass balance
        self.mass_balance_ds.append(lambda: self.tank.ds())

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        capacity, area, datum, decays.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        # not using pop as these items need to stay
        # in the overrides to be fed into the tank overrides
        if "capacity" in overrides.keys():
            self.capacity = overrides["capacity"]
        if "area" in overrides.keys():
            self.area = overrides["area"]
        if "datum" in overrides.keys():
            self.datum = overrides["datum"]
        if "decays" in overrides.keys():
            if self.decays is None:
                raise ValueError(
                    "Attempting to override decays on a node initialised without decays"
                )
            self.decays.update(overrides["decays"])
        # apply tank overrides
        self.tank.apply_overrides(overrides)
        super().apply_overrides(overrides)

    def push_set_storage(self, vqip):
        """A node wrapper for the tank push_storage.

        Args:
            vqip (dict): A VQIP amount to push to the tank

        Returns:
            reply (dict): A VQIP amount that was not successfully pushed
        """
        # Update tank
        reply = self.tank.push_storage(vqip)

        return reply

    def distribute(self):
        """Optional function that discharges all tank storage with push_distributed."""
        # Distribute any active storage
        storage = self.tank.pull_storage(self.tank.get_avail())
        retained = self.push_distributed(storage)
        _ = self.tank.push_storage(retained, force=True)
        if retained["volume"] > constants.FLOAT_ACCURACY:
            print("Storage unable to push")

    def get_percent(self):
        """Function that returns the volume in the storage tank expressed as a percent
        of capacity."""
        return self.tank.storage["volume"] / self.tank.capacity

    def end_timestep(self):
        """Update tank states."""
        self.tank.end_timestep()

    def reinit(self):
        """Call tank reinit."""
        # TODO Automate this better
        self.tank.reinit()
        self.tank.storage["volume"] = self.initial_storage
        self.tank.storage_["volume"] = self.initial_storage


class Groundwater(Storage):
    """"""

    def __init__(
        self,
        residence_time=200,
        infiltration_threshold=1,
        infiltration_pct=0,
        data_input_dict={},
        **kwargs,
    ):
        # TODO why isn't this using a ResidenceTank?
        """A storage with a residence time for groundwater. Can also infiltrate to
        sewers.

        Args:
            residence_time (float, optional): Residence time (see nodes.py/
                ResidenceTank). Defaults to 200.
            infiltration_threshold (float, optional): Proportion of storage capacity
                that must be exceeded to generate infiltration. Defaults to 1.
            infiltration_pct (float, optional): Proportion of storage above the
                threshold that is square rooted and infiltrated. Defaults to 0.
            data_input_dict (dict, optional): Dictionary of data inputs relevant for
                the node (though I don't think it is used). Defaults to {}.

        Functions intended to call in orchestration:
            infiltrate (before sewers are discharged)

            distribute

        Key assumptions:
            - Conceptualises groundwater as a tank.
            - Baseflow is generated following a residence-time method.
            - Baseflow is sent to `storage.py/River`, `nodes.py/Node` or
                `waste.py/Waste` nodes.
            - Infiltration to `sewer.py/Sewer` nodes occurs when the storage
                in the tank is greater than a specified threshold, at a rate
                proportional to the sqrt of volume above the threshold. (Note, this
                behaviour is __not validated__ and a high uncertainty process in
                general)
            - If `decays` are provided to model water quality transformations,
                see `core.py/DecayObj`.

        Input data and parameter requirements:
            - Groundwater tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
            - Infiltration behaviour determined by an `infiltration_threshold`
                and `infiltration_pct`. _Units_: proportion of capacity
            - Optional dictionary of decays with pollutants as keys and decay
                parameters (a constant and a temperature sensitivity exponent) as
                values. _Units_: -
        """
        self.residence_time = residence_time
        self.infiltration_threshold = infiltration_threshold
        self.infiltration_pct = infiltration_pct
        # TODO not used data_input
        self.data_input_dict = data_input_dict
        super().__init__(**kwargs)

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        residence_time, infiltration_threshold, infiltration_pct.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.residence_time = overrides.pop("residence_time", self.residence_time)
        self.infiltration_threshold = overrides.pop(
            "infiltration_threshold", self.infiltration_threshold
        )
        self.infiltration_pct = overrides.pop("infiltration_pct", self.infiltration_pct)
        super().apply_overrides(overrides)

    def distribute(self):
        """Calculate outflow with residence time and send to Nodes or Rivers."""
        avail = self.tank.get_avail()["volume"] / self.residence_time
        to_send = self.tank.pull_storage({"volume": avail})
        retained = self.push_distributed(to_send, of_type=["Node", "River", "Waste"])
        _ = self.tank.push_storage(retained, force=True)
        if retained["volume"] > constants.FLOAT_ACCURACY:
            print("Storage unable to push")

    def infiltrate(self):
        """Calculate amount of water available for infiltration and send to sewers."""
        # Calculate infiltration
        avail = self.tank.get_avail()["volume"]
        avail = max(avail - self.tank.capacity * self.infiltration_threshold, 0)
        avail = (avail * self.infiltration_pct) ** 0.5

        # Push to sewers
        to_send = self.tank.pull_storage({"volume": avail})
        retained = self.push_distributed(to_send, of_type="Sewer")
        _ = self.tank.push_storage(retained, force=True)
        # Any not sent is left in tank
        if retained["volume"] > constants.FLOAT_ACCURACY:
            # print('unable to infiltrate')
            pass


class QueueGroundwater(Storage):
    """"""

    # TODO - no infiltration as yet
    def __init__(self, timearea={0: 1}, data_input_dict={}, **kwargs):
        """Alternate formulation of Groundwater that uses a timearea property to enable
        more nonlinear time behaviour of baseflow routing. Uses the QueueTank or
        DecayQueueTank (see nodes.py/Tank subclassses).

        NOTE: abstraction behaviour from this kind of node need careful checking

        Args:
            timearea (dict, optional): Time area diagram that enables flows to
                take a range of different durations to 'traverse' the tank. The keys of
                the dict are the number of timesteps while the values are the proportion
                of flow. E.g., {0 : 0.7, 1 : 0.3} means 70% of flow takes 0 timesteps
                and 30% takes 1 timesteps. Defaults to {0 : 1}.
            data_input_dict (dict, optional): Dictionary of data inputs relevant for
                the node (though I don't think it is used). Defaults to {}.

        Functions intended to call in orchestration:
            distribute

        Key assumptions:
            - Conceptualises groundwater as a tank.
            - Baseflow is generated following a timearea method.
            - Baseflow is sent to `storage.py/River`, `nodes.py/Node` or
                `waste.py/Waste` nodes.
            - No infiltration to sewers is modelled.
            - If `decays` are provided to model water quality transformations,
                see `core.py/DecayObj`.

        Input data and parameter requirements:
            - Groundwater tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
            - `timearea` is a dictionary containing the timearea diagram.
                _Units_: duration of flow (in timesteps) and proportion of flow
            - Optional dictionary of decays with pollutants as keys and decay
                parameters (a constant and a temperature sensitivity exponent) as
                values. _Units_: -
        """
        self.timearea = timearea
        # TODO not used
        self.data_input_dict = data_input_dict
        super().__init__(**kwargs)
        # Label as Groundwater class so that other nodes treat it the same
        self.__class__.__name__ = "Groundwater"
        # Update handlers
        self.push_set_handler["default"] = self.push_set_timearea
        self.pull_set_handler["default"] = self.pull_set_active
        self.pull_check_handler["default"] = self.pull_check_active
        # Enable decay
        if self.decays is None:
            self.tank = QueueTank(
                capacity=self.capacity,
                area=self.area,
                datum=self.datum,
                initial_storage=self.initial_storage,
            )
        else:
            self.tank = DecayQueueTank(
                capacity=self.capacity,
                area=self.area,
                datum=self.datum,
                decays=self.decays,
                parent=self,
                initial_storage=self.initial_storage,
            )

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        timearea.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.timearea = overrides.pop("timearea", self.timearea)
        super().apply_overrides(overrides)

    def push_set_timearea(self, vqip):
        """Push setting that enables timearea behaviour, (see __init__ for
        description).Used to receive flow that is assumed to occur widely across some
        kind of catchment.

        Args:
            vqip (dict): A VQIP that has been pushed

        Returns:
            reply (dict): A VQIP amount that was not successfuly receivesd
        """
        reply = self.empty_vqip()
        # Iterate over timearea diagram TODO timearea diagram behaviour be generalised
        # across nodes
        for time, normalised in self.timearea.items():
            vqip_ = self.v_change_vqip(vqip, vqip["volume"] * normalised)
            reply_ = self.tank.push_storage(vqip_, time=time)
            reply = self.sum_vqip(reply, reply_)
        return reply

    def distribute(self):
        """Update internal arc, push active_storage onwards, update tank."""
        _ = self.tank.internal_arc.update_queue(direction="push")

        remaining = self.push_distributed(self.tank.active_storage)

        if remaining["volume"] > constants.FLOAT_ACCURACY:
            print("Groundwater couldnt push all")

        # Update tank
        sent = self.tank.active_storage["volume"] - remaining["volume"]
        sent = self.v_change_vqip(self.tank.active_storage, sent)
        reply = self.tank.pull_storage(sent)
        if (reply["volume"] - sent["volume"]) > constants.FLOAT_ACCURACY:
            print("Miscalculated tank storage in discharge")

    def infiltrate(self):
        """"""
        pass

    def pull_check_active(self, vqip=None):
        """A pull check that returns the active storage.

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            (dict): A VQIP amount that is available to pull
        """
        if vqip is None:
            return self.tank.active_storage
        else:
            reply = min(vqip["volume"], self.tank.active_storage["volume"])
            return self.v_change_vqip(self.tank.active_storage, reply)

    def pull_set_active(self, vqip):
        # TODO - this is quite weird behaviour, and inconsistent with pull_check_active
        """Pull proportionately from both the active storage and the queue. Adjudging
        groundwater abstractions to not be particularly sensitive to the within
        catchment travel time.

        Args:
            vqip (dict): A VQIP amount to be pulled (only volume key is used)

        Returns:
            pulled (dict): A VQIP amount that was successfully pulled
        """
        # Calculate actual pull
        total_storage = self.tank.storage["volume"]
        total_pull = min(self.tank.storage["volume"], vqip["volume"])

        if total_pull < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        else:
            # Track total pull in pulled
            pulled = self.empty_vqip()
            # Iterate over queue
            if isinstance(self.tank.internal_arc.queue, dict):
                for t, v in self.tank.internal_arc.queue.items():
                    # Pull proportionately
                    t_pulled = self.v_change_vqip(
                        self.tank.internal_arc.queue[t],
                        v["volume"] * total_pull / total_storage,
                    )
                    # Reduce queue VQIPs
                    self.tank.internal_arc.queue[t] = self.extract_vqip(
                        self.tank.internal_arc.queue[t], t_pulled
                    )
                    # Track pull
                    pulled = self.sum_vqip(pulled, t_pulled)
                # Pull also from active storage
                a_pulled = self.v_change_vqip(
                    self.tank.active_storage,
                    self.tank.active_storage["volume"] * total_pull / total_storage,
                )
                self.tank.active_storage = self.extract_vqip(
                    self.tank.active_storage, a_pulled
                )
                pulled = self.sum_vqip(pulled, a_pulled)

                # Recalculate storage
                self.tank.storage = self.extract_vqip(self.tank.storage, pulled)
                return pulled
            # elif isinstance(self.tank.internal_arc.queue, list): for req in
            #     self.tank.internal_arc.queue: t_pulled = req['vqtip']['volume'] *
            #         total_pull / total_storage req['vqtip'] =
            #         self.v_change_vqip(req['vqtip'], req['vqtip']['volume'] -
            #         t_pulled) pulled += t_pulled a_pulled =
            #     self.tank.active_storage['volume'] * total_pull / total_storage
            #     self.tank.active_storage =
            #     self.v_change_vqip(self.tank.active_storage,
            #     self.tank.active_storage['volume'] - a_pulled) pulled += a_pulled

            #     #Recalculate storage - doing this differently causes numerical errors
            #     new_v = sum([x['vqtip']['volume'] for x in
            #     self.tank.internal_arc.queue])+ self.tank.active_storage['volume']
            #     self.tank.storage = self.v_change_vqip(self.tank.storage, new_v)

            # return self.v_change_vqip(self.tank.storage, pulled)


class River(Storage):
    """"""

    # TODO non-day timestep
    def __init__(
        self,
        depth=2,
        length=200,
        width=20,
        velocity=0.2 * constants.M_S_TO_M_DT,
        damp=0.1,
        mrf=0,
        **kwargs,
    ):
        """Node that contains extensive in-river biochemical processes.

        Args:
            depth (float, optional): River tank depth. Defaults to 2. length (float,
            optional): River tank length. Defaults to 200. width (float, optional):
            River tank width. Defaults to 20. velocity (float, optional): River velocity
            (if someone wants to calculate
                this on the fly that would also work). Defaults to
                0.2*constants.M_S_TO_M_DT.
            damp (float, optional): Flow delay and attentuation parameter. Defaults
                to 0.1.
            mrf (float, optional): Minimum required flow in river (volume per timestep),
                can limit pulls made to the river. Defaults to 0.

        Functions intended to call in orchestration:
            distribute

        Key assumptions:
             - River is conceptualised as a water tank that receives flows from various
                sources (e.g., runoffs from urban and rural land, baseflow from
                groundwater), interacts with water infrastructure (e.g., abstraction for
                irrigation and domestic supply, sewage and treated effluent discharge),
                and discharges flows downstream. It has length and width as shape
                parameters, average velocity to indicate flow speed and capacity to
                indicate the maximum storage limit.
             - Flows from different sources into rivers will fully mix. River tank is
               assumed to
                have delay and attenuation effects when generate outflows. These effects
                are simulated based on the average velocity.
             - In-river biochemical processes are simulated as sources/sinks of
               nutrients
                in the river tank, including - denitrification (for nitrogen) -
                phytoplankton absorption/release (for nitrogen and phosphorus) -
                macrophyte uptake (for nitrogen and phosphorus) These processes are
                affected by river temperature.

        Input data and parameter requirements:
             - depth, length, width
                _Units_: m
             - velocity
                _Units_: m/day
             - damping coefficient
                _Units_: -
             - minimum required flow
                _Units_: m3/day
        """
        # Set parameters
        self.depth = depth
        if depth != 2:
            warnings.warn(
                "warning: the depth parameter is unused by River nodes because it is \
		intended for capacity to be unbounded. It may be removed in a future version."
            )
        self.length = length  # [m]
        self.width = width  # [m]
        self.velocity = velocity  # [m/dt]
        self.damp = damp  # [>=0] flow delay and attenuation
        self.mrf = mrf
        area = length * width  # [m2]

        capacity = (
            constants.UNBOUNDED_CAPACITY
        )  # TODO might be depth * area if flood indunation is going to be simulated

        # Required in cases where 'area' conflicts with length*width
        kwargs["area"] = area
        # Required in cases where 'capacity' conflicts with depth*area
        kwargs["capacity"] = capacity

        super().__init__(**kwargs)

        # TODO check units TODO Will a user want to change any of these? Wide variety of
        # river parameters (from HYPE)
        self.uptake_PNratio = 1 / 7.2  # [-] P:N during crop uptake
        self.bulk_density = 1300  # [kg/m3] soil density
        self.denpar_w = 0.0015  # 0.001, # [kg/m2/day] reference denitrification rate
        # in water course
        self.T_wdays = 5  # [days] weighting constant for river temperature calculation
        # (similar to moving average period)
        self.halfsatINwater = (
            1.5 * constants.MG_L_TO_KG_M3
        )  # [kg/m3] half saturation parameter for denitrification in river
        self.T_10_days = []  # [degree C] average water temperature of 10 days
        self.T_20_days = []  # [degree C] average water temperature of 20 days
        self.TP_365_days = []  # [degree C] average water temperature of 20 days
        self.hsatTP = 0.05 * constants.MG_L_TO_KG_M3  # [kg/m3]
        self.limpppar = 0.1 * constants.MG_L_TO_KG_M3  # [kg/m3]
        self.prodNpar = 0.001  # [kg N/m3/day] nitrogen production/mineralisation rate
        self.prodPpar = (
            0.0001  # [kg N/m3/day] phosphorus production/mineralisation rate
        )
        self.muptNpar = 0.001  # [kg/m2/day] nitrogen macrophyte uptake rate
        self.muptPpar = 0.0001  # 0.01, # [kg/m2/day] phosphorus macrophyte uptake rate

        self.max_temp_lag = 20
        self.lagged_temperatures = []

        self.max_phosphorus_lag = 365
        self.lagged_total_phosphorus = []

        self.din_components = ["ammonia", "nitrate"]
        # TODO need a cleaner way to do this depending on whether e.g., nitrite is
        # included

        # Initialise paramters
        self.current_depth = 0  # [m]
        # self.river_temperature = 0 # [degree C] self.river_denitrification = 0 #
        # [kg/day] self.macrophyte_uptake_N = 0 # [kg/day] self.macrophyte_uptake_P = 0
        # # [kg/day] self.sediment_particulate_phosphorus_pool = 60000 # [kg]
        # self.sediment_pool = 1000000 # [kg] self.benthos_source_sink = 0 # [kg/day]
        # self.t_res = 0 # [day] self.outflow = self.empty_vqip()

        # Update end_teimstep
        self.end_timestep = self.end_timestep_

        # Update handlers
        self.push_set_handler["default"] = self.push_set_river
        self.push_check_handler["default"] = self.push_check_accept

        self.pull_check_handler["default"] = self.pull_check_river
        self.pull_set_handler["default"] = self.pull_set_river

        # TODO - RiparianBuffer
        self.pull_check_handler[("RiparianBuffer", "volume")] = self.pull_check_fp

        # Update mass balance
        self.bio_in = self.empty_vqip()
        self.bio_out = self.empty_vqip()

        self.mass_balance_in.append(lambda: self.bio_in)
        self.mass_balance_out.append(lambda: self.bio_out)

    # TODO something like this might be needed if you want sewers backing up from river
    # height... would need to incorporate expected river outflow def get_dt_excess(self,
    #     vqip = None): reply = self.empty_vqip() reply['volume'] =
    #     self.tank.get_excess()['volume'] + self.tank.get_avail()['volume'] *
    #     self.get_riverrc() if vqip is not None: reply['volume'] = min(vqip['volume'],
    #         reply['volume']) return reply

    # def push_set_river(self, vqip): vqip_ = vqip.copy() vqip_ =
    #     self.v_change_vqip(vqip_, min(vqip_['volume'],
    #     self.get_dt_excess()['volume'])) _ = self.tank.push_storage(vqip_, force=True)
    #     return self.extract_vqip(vqip, vqip_)

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        timearea.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        overwrite_params = set(
            [
                "length",
                "width",
                "velocity",
                "damp",
                "mrf",
                "uptake_PNratio",
                "bulk_density",
                "denpar_w",
                "T_wdays",
                "halfsatINwater",
                "hsatTP",
                "limpppar",
                "prodNpar",
                "prodPpar",
                "muptNpar",
                "muptPpar",
                "max_temp_lag",
                "max_phosphorus_lag",
            ]
        )

        for param in overwrite_params.intersection(overrides.keys()):
            setattr(self, param, overrides.pop(param))

        if "area" in overrides.keys():
            warnings.warn(
                "WARNING: specifying area is depreciated in overrides \
		for river, please specify length and width instead"
            )
        overrides["area"] = self.length * self.width
        if "capacity" in overrides.keys():
            warnings.warn(
                "ERROR: specifying capacity is depreciated in overrides \
		for river, it is always set as unbounded capacity"
            )
        overrides["capacity"] = constants.UNBOUNDED_CAPACITY
        super().apply_overrides(overrides)

    def pull_check_river(self, vqip=None):
        """Check amount of water that can be pulled from river tank and upstream.

        Args:
            vqip (dict, optional): Maximum water required (only 'volume' is used)

        Returns:
            avail (dict): A VQIP amount that can be pulled
        """
        # Get storage
        avail = self.tank.get_avail()

        # Check incoming
        upstream = self.get_connected(direction="pull", of_type=["River", "Node"])
        avail["volume"] += upstream["avail"]

        # convert mrf from volume/timestep to discrete value
        mrf = self.mrf / self.get_riverrc()

        # Apply mrf
        avail_vol = max(avail["volume"] - mrf, 0)
        if vqip is None:
            avail = self.v_change_vqip(avail, avail_vol)
        else:
            avail = self.v_change_vqip(avail, min(avail_vol, vqip["volume"]))

        return avail

    def pull_set_river(self, vqip):
        """Pull from river tank and upstream, acknowledging MRF with pull_check.

        Args:
            vqip (dict): A VQIP amount to pull (only volume key used)

        Returns:
            (dict): A VQIP amount that was pulled
        """
        # Calculate available pull
        avail = self.pull_check_river(vqip)

        # Take first from tank
        pulled = self.tank.pull_storage(avail)

        # Take remaining from upstream
        to_pull = {"volume": avail["volume"] - pulled["volume"]}
        pulled_ = self.pull_distributed(to_pull, of_type=["River", "Node"])

        reply = self.sum_vqip(pulled, pulled_)

        return reply

    def push_set_river(self, vqip):
        """Push to river tank, currently forced.

        Args:
            vqip (dict): A VQIP amount to push

        Returns:
            (dict): A VQIP amount that was not successfully received
        """
        _ = self.tank.push_storage(vqip, force=True)
        return self.empty_vqip()

    def update_depth(self):
        """Recalculate depth."""
        self.current_depth = self.tank.storage["volume"] / self.area

    def get_din_pool(self):
        """Get total dissolved inorganic nitrogen from tank storage.

        Returns:
            (float): total din
        """
        return sum(
            [self.tank.storage[x] for x in self.din_components]
        )  # TODO + self.tank.storage['nitrite'] but nitrite might not be modelled...
        # need some ways to address this

    def biochemical_processes(self):
        """Runs all biochemical processes and updates pollutant amounts.

        Returns:
            in_ (dict): A VQIP amount that represents total gain in pollutant amounts
            out_ (dict): A VQIP amount that represents total loss in pollutant amounts
        """
        # TODO make more modular
        self.update_depth()

        self.tank.storage["temperature"] = (1 - 1 / self.T_wdays) * self.tank.storage[
            "temperature"
        ] + (1 / self.T_wdays) * self.get_data_input("temperature")

        # Update lagged temperatures
        if len(self.lagged_temperatures) > self.max_temp_lag:
            del self.lagged_temperatures[0]
        self.lagged_temperatures.append(self.tank.storage["temperature"])

        # Update lagged total phosphorus
        if len(self.lagged_total_phosphorus) > self.max_phosphorus_lag:
            del self.lagged_total_phosphorus[0]
        total_phosphorus = (
            self.tank.storage["phosphate"] + self.tank.storage["org-phosphorus"]
        )
        self.lagged_total_phosphorus.append(total_phosphorus)

        # Check if any water
        if self.tank.storage["volume"] < constants.FLOAT_ACCURACY:
            # Assume these only do something when there is water
            return (self.empty_vqip(), self.empty_vqip())

        if self.tank.storage["temperature"] <= 0:
            # Seems that these things are only active when above freezing
            return (self.empty_vqip(), self.empty_vqip())

        # Denitrification
        tempfcn = 2 ** ((self.tank.storage["temperature"] - 20) / 10)
        if self.tank.storage["temperature"] < 5:
            tempfcn *= self.tank.storage["temperature"] / 5

        din = self.get_din_pool()
        din_concentration = din / self.tank.storage["volume"]
        confcn = din_concentration / (
            din_concentration + self.halfsatINwater
        )  # [kg/m3]
        denitri_water = (
            self.denpar_w * self.area * tempfcn * confcn
        )  # [kg/day] #TODO convert to per DT

        river_denitrification = min(
            denitri_water, 0.5 * din
        )  # [kg/day] max 50% kan be denitrified
        din_ = din - river_denitrification  # [kg]

        # Update mass balance
        in_ = self.empty_vqip()
        out_ = self.empty_vqip()
        if din > 0:
            for pol in self.din_components:
                # denitrification
                loss = (din - din_) / din * self.tank.storage[pol]
                out_[pol] += loss
                self.tank.storage[pol] -= loss

        din = self.get_din_pool()

        # Calculate moving averages TODO generalise
        temp_10_day = sum(self.lagged_temperatures[-10:]) / 10
        temp_20_day = sum(self.lagged_temperatures[-20:]) / 20
        total_phos_365_day = sum(self.lagged_total_phosphorus) / self.max_phosphorus_lag

        # Calculate coefficients
        tempfcn = (
            (self.tank.storage["temperature"]) / 20 * (temp_10_day - temp_20_day) / 5
        )
        if (total_phos_365_day - self.limpppar + self.hsatTP) > 0:
            totalphosfcn = (total_phos_365_day - self.limpppar) / (
                total_phos_365_day - self.limpppar + self.hsatTP
            )
        else:
            totalphosfcn = 0

        # Mineralisation/production TODO this feels like it could be much tidier
        minprodN = (
            self.prodNpar * totalphosfcn * tempfcn * self.area * self.current_depth
        )  # [kg N/day]
        minprodP = (
            self.prodPpar
            * totalphosfcn
            * tempfcn
            * self.area
            * self.current_depth
            * self.uptake_PNratio
        )  # [kg N/day]
        if minprodN > 0:
            # production (inorg -> org)
            minprodN = min(
                0.5 * din, minprodN
            )  # only half pool can be used for production
            minprodP = min(
                0.5 * self.tank.storage["phosphate"], minprodP
            )  # only half pool can be used for production

            # Update mass balance
            out_["phosphate"] = minprodP
            self.tank.storage["phosphate"] -= minprodP
            in_["org-phosphorus"] = minprodP
            self.tank.storage["org-phosphorus"] += minprodP
            if din > 0:
                for pol in self.din_components:
                    loss = minprodN * self.tank.storage[pol] / din
                    out_[pol] += loss
                    self.tank.storage[pol] -= loss

            in_["org-nitrogen"] = minprodN
            self.tank.storage["org-nitrogen"] += minprodN

        else:
            # mineralisation (org -> inorg)
            minprodN = min(0.5 * self.tank.storage["org-nitrogen"], -minprodN)
            minprodP = min(0.5 * self.tank.storage["org-phosphorus"], -minprodP)

            # Update mass balance
            in_["phosphate"] = minprodP
            self.tank.storage["phosphate"] += minprodP
            out_["org-phosphorus"] = minprodP
            self.tank.storage["org-phosphorus"] -= minprodP
            if din > 0:
                for pol in self.din_components:
                    gain = minprodN * self.tank.storage[pol] / din
                    in_[pol] += gain
                    self.tank.storage[pol] += gain

            out_["org-nitrogen"] = minprodN
            self.tank.storage["org-nitrogen"] -= minprodN

        din = self.get_din_pool()

        # macrophyte uptake temperature dependence factor
        tempfcn1 = (max(0, self.tank.storage["temperature"]) / 20) ** 0.3
        tempfcn2 = (self.tank.storage["temperature"] - temp_20_day) / 5
        tempfcn = max(0, tempfcn1 * tempfcn2)

        macrouptN = self.muptNpar * tempfcn * self.area  # [kg/day]
        macrophyte_uptake_N = min(0.5 * din, macrouptN)
        if din > 0:
            for pol in self.din_components:
                loss = macrophyte_uptake_N * self.tank.storage[pol] / din
                out_[pol] += loss
                self.tank.storage[pol] -= loss

        macrouptP = (
            self.muptPpar * tempfcn * max(0, totalphosfcn) * self.area
        )  # [kg/day]
        macrophyte_uptake_P = min(0.5 * self.tank.storage["phosphate"], macrouptP)
        out_["phosphate"] += macrophyte_uptake_P
        self.tank.storage["phosphate"] -= macrophyte_uptake_P

        # TODO source/sink for benthos sediment P suspension/resuspension
        return in_, out_

    def get_riverrc(self):
        """Get river outflow coefficient (i.e., how much water leaves the tank in this
        timestep).

        Returns:
            riverrc (float): outflow coeffficient
        """
        # Calculate travel time
        total_time = self.length / self.velocity
        # Apply damp
        kt = self.damp * total_time  # [day]
        if kt != 0:
            riverrc = 1 - kt + kt * exp(-1 / kt)  # [-]
        else:
            riverrc = 1
        return riverrc

    def calculate_discharge(self):
        """"""
        if "nitrate" in constants.POLLUTANTS:
            # TODO clumsy Run biochemical processes
            in_, out_ = self.biochemical_processes()
            # Mass balance
            self.bio_in = in_
            self.bio_out = out_

    def distribute(self):
        """Run biochemical processes, track mass balance, and distribute water."""
        # self.calculate_discharge() Get outflow
        outflow = self.tank.pull_storage(
            {"volume": self.tank.storage["volume"] * self.get_riverrc()}
        )
        # Distribute outflow
        reply = self.push_distributed(outflow, of_type=["River", "Node", "Waste"])
        _ = self.tank.push_storage(reply, force=True)
        if reply["volume"] > constants.FLOAT_ACCURACY:
            print("river cant push: {0}".format(reply["volume"]))

    def pull_check_fp(self, vqip=None):
        """

        Args:
            vqip:

        Returns:

        """
        # TODO Pull checking for riparian buffer, needs updating update river depth
        self.update_depth()
        return self.current_depth, self.area, self.width, self.river_tank.storage

    def end_timestep_(self):
        """Update state variables."""
        self.tank.end_timestep()
        self.bio_in = self.empty_vqip()
        self.bio_out = self.empty_vqip()


class Reservoir(Storage):
    """"""

    def __init__(self, **kwargs):
        """Storage node that makes abstractions by calling pull_distributed.

        Functions intended to call in orchestration:
            make_abstractions (before any river routing)

        Key assumptions:
            - Conceptualised as a `Tank`.
            - Recharged only via pumped abstractions.
            - Evaporation/precipitation onto surface area currently ignored.
            - If `decays` are provided to model water quality transformations,
                see `core.py/DecayObj`.

        Input data and parameter requirements:
            - Tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
            - Optional dictionary of decays with pollutants as keys and decay
                parameters (a constant and a temperature sensitivity exponent) as
                values. _Units_: -
        """
        super().__init__(**kwargs)

    def make_abstractions(self):
        """Pulls water and updates tanks."""
        reply = self.pull_distributed(self.tank.get_excess())
        spill = self.tank.push_storage(reply)
        _ = self.tank.push_storage(spill, force=True)
        if spill["volume"] > constants.FLOAT_ACCURACY:
            print("Spill at reservoir by {0}".format(spill["volume"]))


class RiverReservoir(Reservoir):
    """"""

    def __init__(self, environmental_flow=0, **kwargs):
        """A reservoir with a natural river inflow, includes an environmental downstream
        flow to satisfy.

        Args:
            environmental_flow (float, optional): Downstream environmental flow.
                Defaults to 0.

        Functions intended to call in orchestration:
                make_abstractions (if any)

                satisfy_environmental (before river routing.. possibly before
                    downstream river abstractions depending on licence)

        Key assumptions:
            - Conceptualised as a `Tank`.
            - Recharged via pumped abstractions and receives water from
                inflowing arcs.
            - Reservoir aims to satisfy a static `environmental_flow`.
            - If tank capacity is exceeded, reservoir spills downstream
                towards `nodes.py/Node`, `storage.py/River` or `waste.py/Waste` nodes.
                Spill counts towards `environmental_flow`.
            - Evaporation/precipitation onto surface area currently ignored.
            - Currently, if a reservoir satisfies a pull from a downstream
                node, it does __not__ count towards `environmental_flow`.
            - If `decays` are provided to model water quality transformations,
                see `core.py/DecayObj`.

        Input data and parameter requirements:
            - Tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
            - `environmental_flow`
                _Units_: cubic metres/timestep
            - Optional dictionary of decays with pollutants as keys and decay
                parameters (a constant and a temperature sensitivity exponent) as
                values. _Units_: -
        """
        # Parameters
        self.environmental_flow = environmental_flow
        super().__init__(**kwargs)

        # State variables
        self.total_environmental_satisfied = 0

        self.push_set_handler["default"] = self.push_set_river_reservoir
        self.push_check_handler["default"] = self.push_check_river_reservoir
        self.end_timestep = self.end_timestep_

        self.__class__.__name__ = "Reservoir"

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        environmental_flow.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.environmental_flow = overrides.pop(
            "environmental_flow", self.environmental_flow
        )
        super().apply_overrides(overrides)

    def push_set_river_reservoir(self, vqip):
        """Receive water.

        Args:
            vqip (dict): A VQIP amount to be received

        Returns:
            reply (dict): A VQIP amount that was not successfully received
        """
        # Apply normal reservoir storage We do this under the assumption that spill is
        # mixed in with the reservoir If the reservoir can't spill everything you'll get
        # some weird numbers in reply, but if your reservoir can't spill as much as you
        # like then you should probably be pushing the right amount through
        # push_check_river_reservoir Some cunning could probably avoid this by checking
        # vqip, but this is a serious edge case
        _ = self.tank.push_storage(vqip, force=True)
        spill = self.tank.pull_ponded()

        # Send spill downstream
        reply = self.push_distributed(spill, of_type=["Node", "River", "Waste"])

        # Use spill to satisfy downstream flow
        self.total_environmental_satisfied += spill["volume"] - reply["volume"]

        return reply

    def push_check_river_reservoir(self, vqip=None):
        """A push check to receive water, assumes spill may occur and checks downstream
        capacity.

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            excess (dict): A VQIP amount of water that cannot be received
        """
        # Check downstream capacity (i.e., that would be spilled)
        downstream_availability = self.get_connected(
            direction="push", of_type=["Node", "River", "Waste"]
        )["avail"]
        # Check excess capacity in the reservoir
        excess = self.tank.get_excess()
        # Combine excess and downstream in response
        new_v = excess["volume"] + downstream_availability
        if vqip is not None:
            new_v = min(vqip["volume"], new_v)
        # Update to vqip
        excess = self.v_change_vqip(excess, new_v)

        return excess

    def satisfy_environmental(self):
        """Satisfy environmental flow downstream."""
        # Calculate how much environmental flow is yet to satisfy #(some may have been
        # already if pull-and-take abstractions have taken place)
        to_satisfy = max(
            self.environmental_flow - self.total_environmental_satisfied, 0
        )
        # Pull from tank
        environmental = self.tank.pull_storage({"volume": to_satisfy})
        # Send downstream
        reply = self.push_distributed(environmental)
        _ = self.tank.push_storage(reply, force=True)
        if reply["volume"] > constants.FLOAT_ACCURACY:
            print("warning: environmental not able to push")

        # Update satisfaction
        self.total_environmental_satisfied += environmental["volume"]

    def end_timestep_(self):
        """Udpate state varibles."""
        self.tank.end_timestep()
        self.total_environmental_satisfied = 0
