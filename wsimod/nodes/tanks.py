"""Module for defining tanks."""

from typing import Any, Dict

from wsimod.arcs.arcs import AltQueueArc, DecayArcAlt
from wsimod.core import constants
from wsimod.core.core import DecayObj, WSIObj


class Tank(WSIObj):
    """"""

    def __init__(self, capacity=0, area=1, datum=10, initial_storage=0):
        """A standard storage object.

        Args:
            capacity (float, optional): Volumetric tank capacity. Defaults to 0.
            area (float, optional): Area of tank. Defaults to 1.
            datum (float, optional): Datum of tank base (not currently used in any
                functions). Defaults to 10.
            initial_storage (optional): Initial storage for tank.
                float: Tank will be initialised with zero pollutants and the float
                    as volume
                dict: Tank will be initialised with this VQIP
                Defaults to 0 (i.e., no volume, no pollutants).
        """
        # Set parameters
        self.capacity = capacity
        self.area = area
        self.datum = datum
        self.initial_storage = initial_storage

        WSIObj.__init__(self)  # Not sure why I do this rather than super()

        # TODO I don't think the outer if statement is needed
        if "initial_storage" in dir(self):
            if isinstance(self.initial_storage, dict):
                # Assume dict is VQIP describing storage
                self.storage = self.copy_vqip(self.initial_storage)
                self.storage_ = self.copy_vqip(
                    self.initial_storage
                )  # Lagged storage for mass balance
            else:
                # Assume number describes initial stroage
                self.storage = self.v_change_vqip(
                    self.empty_vqip(), self.initial_storage
                )
                self.storage_ = self.v_change_vqip(
                    self.empty_vqip(), self.initial_storage
                )  # Lagged storage for mass balance
        else:
            self.storage = self.empty_vqip()
            self.storage_ = self.empty_vqip()  # Lagged storage for mass balance

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the tank.

        Enables a user to override any of the following parameters:
        area, capacity, datum.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.capacity = overrides.pop("capacity", self.capacity)
        self.area = overrides.pop("area", self.area)
        self.datum = overrides.pop("datum", self.datum)
        if len(overrides) > 0:
            print(f"No override behaviour defined for: {overrides.keys()}")

    def ds(self):
        """Should be called by parent object to get change in storage.

        Returns:
            (dict): Change in storage
        """
        return self.ds_vqip(self.storage, self.storage_)

    def pull_ponded(self):
        """Pull any volume that is above the tank's capacity.

        Returns:
            ponded (vqip): Amount of ponded water that has been removed from the
                tank

        Examples:
            >>> constants.ADDITIVE_POLLUTANTS = ['phosphate']
            >>> my_tank = Tank(capacity = 9, initial_storage = {'volume' : 10,
                'phosphate' : 0.2})
            >>> print(my_tank.storage)
            {'volume' : 10, 'phosphate' : 0.2}
            >>> print(my_tank.pull_ponded())
            {'volume' : 1, 'phosphate' : 0.02}
            >>> print(my_tank.storage)
            {'volume' : 9, 'phosphate' : 0.18}
        """
        # Get amount
        ponded = max(self.storage["volume"] - self.capacity, 0)
        # Pull from tank
        ponded = self.pull_storage({"volume": ponded})
        return ponded

    def get_avail(self, vqip=None):
        """Get minimum of the amount of water in storage and vqip (if provided).

        Args:
            vqip (dict, optional): Maximum water required (only 'volume' is used).
                Defaults to None.

        Returns:
            reply (dict): Water available

        Examples:
            >>> constants.ADDITIVE_POLLUTANTS = ['phosphate']
            >>> my_tank = Tank(capacity = 9, initial_storage = {'volume' : 10,
                'phosphate' : 0.2})
            >>> print(my_tank.storage)
            {'volume' : 10, 'phosphate' : 0.2}
            >>> print(my_tank.get_avail())
            {'volume' : 10, 'phosphate' : 0.2}
            >>> print(my_tank.get_avail({'volume' : 1}))
            {'volume' : 1, 'phosphate' : 0.02}
        """
        reply = self.copy_vqip(self.storage)
        if vqip is None:
            # Return storage
            return reply
        else:
            # Adjust storage pollutants to match volume in vqip
            reply = self.v_change_vqip(reply, min(reply["volume"], vqip["volume"]))
            return reply

    def get_excess(self, vqip=None):
        """Get difference between current storage and tank capacity.

        Args:
            vqip (dict, optional): Maximum capacity required (only 'volume' is
                used). Defaults to None.

        Returns:
            (dict): Difference available

        Examples:
            >>> constants.ADDITIVE_POLLUTANTS = ['phosphate']
            >>> my_tank = Tank(capacity = 9, initial_storage = {'volume' : 5,
                'phosphate' : 0.2})
            >>> print(my_tank.get_excess())
            {'volume' : 4, 'phosphate' : 0.16}
            >>> print(my_tank.get_excess({'volume' : 2}))
            {'volume' : 2, 'phosphate' : 0.08}
        """
        vol = max(self.capacity - self.storage["volume"], 0)
        if vqip is not None:
            vol = min(vqip["volume"], vol)

        # Adjust storage pollutants to match volume in vqip
        # TODO the v_change_vqip in the reply here is a weird default (if a VQIP is not
        #   provided)
        return self.v_change_vqip(self.storage, vol)

    def push_storage(self, vqip, force=False):
        """Push water into tank, updating the storage VQIP. Force argument can be used
        to ignore tank capacity.

        Args:
            vqip (dict): VQIP amount to be pushed
            force (bool, optional): Argument used to cause function to ignore tank
                capacity, possibly resulting in pooling. Defaults to False.

        Returns:
            reply (dict): A VQIP of water not successfully pushed to the tank

        Examples:
            >>> constants.ADDITIVE_POLLUTANTS = ['phosphate']
            >>> constants.POLLUTANTS = ['phosphate']
            >>> constants.NON_ADDITIVE_POLLUTANTS = []
            >>> my_tank = Tank(capacity = 9, initial_storage = {'volume' : 5,
                'phosphate' : 0.2})
            >>> my_push = {'volume' : 10, 'phosphate' : 0.5}
            >>> reply = my_tank.push_storage(my_push)
            >>> print(reply)
            {'volume' : 6, 'phosphate' : 0.3}
            >>> print(my_tank.storage)
            {'volume': 9.0, 'phosphate': 0.4}
            >>> print(my_tank.push_storage(reply, force = True))
            {'phosphate': 0, 'volume': 0}
            >>> print(my_tank.storage)
            {'volume': 15.0, 'phosphate': 0.7}
        """
        if force:
            # Directly add request to storage
            self.storage = self.sum_vqip(self.storage, vqip)
            return self.empty_vqip()

        # Check whether request can be met
        excess = self.get_excess()["volume"]

        # Adjust accordingly
        reply = max(vqip["volume"] - excess, 0)
        reply = self.v_change_vqip(vqip, reply)
        entered = self.v_change_vqip(vqip, vqip["volume"] - reply["volume"])

        # Update storage
        self.storage = self.sum_vqip(self.storage, entered)

        return reply

    def pull_storage(self, vqip):
        """Pull water from tank, updating the storage VQIP. Pollutants are removed from
        tank in proportion to 'volume' in vqip (pollutant values in vqip are ignored).

        Args:
            vqip (dict): VQIP amount to be pulled, (only 'volume' key is needed)

        Returns:
            reply (dict): A VQIP water successfully pulled from the tank

        Examples:
            >>> constants.ADDITIVE_POLLUTANTS = ['phosphate']
            >>> my_tank = Tank(capacity = 9, initial_storage = {'volume' : 5,
                'phosphate' : 0.2})
            >>> print(my_tank.pull_storage({'volume' : 6}))
            {'volume': 5.0, 'phosphate': 0.2}
            >>> print(my_tank.storage)
            {'volume': 0, 'phosphate': 0}
        """
        # Pull from Tank by volume (taking pollutants in proportion)
        if self.storage["volume"] == 0:
            return self.empty_vqip()

        # Adjust based on available volume
        reply = min(vqip["volume"], self.storage["volume"])

        # Update reply to vqip (in proportion to concentration in storage)
        reply = self.v_change_vqip(self.storage, reply)

        # Extract from storage
        self.storage = self.extract_vqip(self.storage, reply)

        return reply

    def pull_pollutants(self, vqip):
        """Pull water from tank, updating the storage VQIP. Pollutants are removed from
        tank in according to their values in vqip.

        Args:
            vqip (dict): VQIP amount to be pulled

        Returns:
            vqip (dict): A VQIP water successfully pulled from the tank

        Examples:
            >>> constants.ADDITIVE_POLLUTANTS = ['phosphate']
            >>> my_tank = Tank(capacity = 9, initial_storage = {'volume' : 5,
                'phosphate' : 0.2})
            >>> print(my_tank.pull_pollutants({'volume' : 2, 'phosphate' : 0.15}))
            {'volume': 2.0, 'phosphate': 0.15}
            >>> print(my_tank.storage)
            {'volume': 3, 'phosphate': 0.05}
        """
        # Adjust based on available mass
        for pol in constants.ADDITIVE_POLLUTANTS + ["volume"]:
            vqip[pol] = min(self.storage[pol], vqip[pol])

        # Extract from storage
        self.storage = self.extract_vqip(self.storage, vqip)
        return vqip

    def get_head(self, datum=None, non_head_storage=0):
        """Area volume calculation for head calcuations. Datum and storage that does not
        contribute to head can be specified.

        Args:
            datum (float, optional): Value to add to pressure head in tank.
                Defaults to None.
            non_head_storage (float, optional): Amount of storage that does
                not contribute to generation of head. The tank must exceed
                this value to generate any pressure head. Defaults to 0.

        Returns:
            head (float): Total head in tank

        Examples:
            >>> my_tank = Tank(datum = 10, initial_storage = 5, capacity = 10, area = 2)
            >>> print(my_tank.get_head())
            12.5
            >>> print(my_tank.get_head(non_head_storage = 1))
            12
            >>> print(my_tank.get_head(non_head_storage = 1, datum = 0))
            2
        """
        # If datum not provided use object datum
        if datum is None:
            datum = self.datum

        # Calculate pressure head generating storage
        head_storage = max(self.storage["volume"] - non_head_storage, 0)

        # Perform head calculation
        head = head_storage / self.area + datum

        return head

    def evaporate(self, evap):
        """Wrapper for v_distill_vqip to apply a volumetric subtraction from tank
        storage. Volume removed from storage and no change in pollutant values.

        Args:
            evap (float): Volume to evaporate

        Returns:
            evap (float): Volumetric amount of evaporation successfully removed
        """
        avail = self.get_avail()["volume"]

        evap = min(evap, avail)
        self.storage = self.v_distill_vqip(self.storage, evap)
        return evap

    ##Old function no longer needed (check it is not used anywhere and remove)
    def push_total(self, vqip):
        """

        Args:
            vqip:

        Returns:

        """
        self.storage = self.sum_vqip(self.storage, vqip)
        return self.empty_vqip()

    ##Old function no longer needed (check it is not used anywhere and remove)
    def push_total_c(self, vqip):
        """

        Args:
            vqip:

        Returns:

        """
        # Push vqip to storage where pollutants are given as a concentration rather
        #   than storage
        vqip = self.concentration_to_total(self.vqip)
        self.storage = self.sum_vqip(self.storage, vqip)
        return self.empty_vqip()

    def end_timestep(self):
        """Function to be called by parent object, tracks previously timestep's
        storage."""
        self.storage_ = self.copy_vqip(self.storage)

    def reinit(self):
        """Set storage to an empty VQIP."""
        self.storage = self.empty_vqip()
        self.storage_ = self.empty_vqip()


class ResidenceTank(Tank):
    """"""

    def __init__(self, residence_time=2, **kwargs):
        """A tank that has a residence time property that limits storage pulled from the
        'pull_outflow' function.

        Args:
            residence_time (float, optional): Residence time, in theory given
                in timesteps, in practice it just means that storage /
                residence time can be pulled each time pull_outflow is called.
                Defaults to 2.
        """
        self.residence_time = residence_time
        super().__init__(**kwargs)

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the residencetank.

        Enables a user to override any of the following parameters:
        residence_time.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.residence_time = overrides.pop("residence_time", self.residence_time)
        super().apply_overrides(overrides)

    def pull_outflow(self):
        """Pull storage by residence time from the tank, updating tank storage.

        Returns:
            outflow (dict): A VQIP with volume of pulled volume and pollutants
                proportionate to the tank's pollutants
        """
        # Calculate outflow
        outflow = self.storage["volume"] / self.residence_time
        # Update pollutant amounts
        outflow = self.v_change_vqip(self.storage, outflow)
        # Remove from tank
        outflow = self.pull_storage(outflow)
        return outflow


class DecayTank(Tank, DecayObj):
    """"""

    def __init__(self, decays={}, parent=None, **kwargs):
        """A tank that has DecayObj functions. Decay occurs in end_timestep, after
        updating state variables. In this sense, decay is occurring at the very
        beginning of the timestep.

        Args:
            decays (dict): A dict of dicts containing a key for each pollutant that
                decays and, within that, a key for each parameter (a constant and
                exponent)
            parent (object): An object that can be used to read temperature data from
        """
        # Store parameters
        self.parent = parent

        # Initialise Tank
        Tank.__init__(self, **kwargs)

        # Initialise decay object
        DecayObj.__init__(self, decays)

        # Update timestep and ds functions
        self.end_timestep = self.end_timestep_decay
        self.ds = self.decay_ds

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the decaytank.

        Enables a user to override any of the following parameters:
        decays.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.decays.update(overrides.pop("decays", {}))
        super().apply_overrides(overrides)

    def end_timestep_decay(self):
        """Update state variables and call make_decay."""
        self.total_decayed = self.empty_vqip()
        self.storage_ = self.copy_vqip(self.storage)

        self.storage = self.make_decay(self.storage)

    def decay_ds(self):
        """Track storage and amount decayed.

        Returns:
            ds (dict): A VQIP of change in storage and total decayed
        """
        ds = self.ds_vqip(self.storage, self.storage_)
        ds = self.sum_vqip(ds, self.total_decayed)
        return ds


class QueueTank(Tank):
    """"""

    def __init__(self, number_of_timesteps=0, **kwargs):
        """A tank with an internal queue arc, whose queue must be completed before
        storage is available for use. The storage that has completed the queue is under
        the 'active_storage' property.

        Args:
            number_of_timesteps (int, optional): Built in delay for the internal
                queue - it is always added to the queue time, although delay can be
                provided with pushes only. Defaults to 0.
        """
        # Set parameters
        self.number_of_timesteps = number_of_timesteps

        super().__init__(**kwargs)
        self.end_timestep = self._end_timestep
        self.active_storage = self.copy_vqip(self.storage)

        # TODO enable queue to be initialised not empty
        self.out_arcs = {}
        self.in_arcs = {}
        # Create internal queue arc
        self.internal_arc = AltQueueArc(
            in_port=self, out_port=self, number_of_timesteps=self.number_of_timesteps
        )
        # TODO should mass balance call internal arc (is this arc called in arc mass
        #   balance?)

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the queuetank.

        Enables a user to override any of the following parameters:
        number_of_timesteps.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.number_of_timesteps = overrides.pop(
            "number_of_timesteps", self.number_of_timesteps
        )
        self.internal_arc.number_of_timesteps = self.number_of_timesteps
        super().apply_overrides(overrides)

    def get_avail(self):
        """Return the active_storage of the tank.

        Returns:
            (dict): VQIP of active_storage
        """
        return self.copy_vqip(self.active_storage)

    def push_storage(self, vqip, time=0, force=False):
        """Push storage into QueueTank, applying travel time, unless forced.

        Args:
            vqip (dict): A VQIP of the amount to push
            time (int, optional): Number of timesteps to spend in queue, in addition
                to number_of_timesteps property of internal_arc. Defaults to 0.
            force (bool, optional): Force property that will ignore tank capacity
                and ignore travel time. Defaults to False.

        Returns:
            reply (dict): A VQIP of water that could not be received by the tank
        """
        if force:
            # Directly add request to storage, skipping queue
            self.storage = self.sum_vqip(self.storage, vqip)
            self.active_storage = self.sum_vqip(self.active_storage, vqip)
            return self.empty_vqip()

        # Push to QueueTank
        reply = self.internal_arc.send_push_request(vqip, force=force, time=time)
        # Update storage
        # TODO storage won't be accurately tracking temperature..
        self.storage = self.sum_vqip(
            self.storage, self.v_change_vqip(vqip, vqip["volume"] - reply["volume"])
        )
        return reply

    def pull_storage(self, vqip):
        """Pull storage from the QueueTank, only water in active_storage is available.
        Returning water pulled and updating tank states. Pollutants are removed from
        tank in proportion to 'volume' in vqip (pollutant values in vqip are ignored).

        Args:
            vqip (dict): VQIP amount to pull, only 'volume' property is used

        Returns:
            reply (dict): VQIP amount that was pulled
        """
        # Adjust based on available volume
        reply = min(vqip["volume"], self.active_storage["volume"])

        # Update reply to vqip
        reply = self.v_change_vqip(self.active_storage, reply)

        # Extract from active_storage
        self.active_storage = self.extract_vqip(self.active_storage, reply)

        # Extract from storage
        self.storage = self.extract_vqip(self.storage, reply)

        return reply

    def pull_storage_exact(self, vqip):
        """Pull storage from the QueueTank, only water in active_storage is available.
        Pollutants are removed from tank in according to their values in vqip.

        Args:
            vqip (dict): A VQIP amount to pull

        Returns:
            reply (dict): A VQIP amount successfully pulled
        """
        # Adjust based on available
        reply = self.copy_vqip(vqip)
        for pol in ["volume"] + constants.ADDITIVE_POLLUTANTS:
            reply[pol] = min(reply[pol], self.active_storage[pol])

        # Pull from QueueTank
        self.active_storage = self.extract_vqip(self.active_storage, reply)

        # Extract from storage
        self.storage = self.extract_vqip(self.storage, reply)
        return reply

    def push_check(self, vqip=None, tag="default"):
        """Wrapper for get_excess but applies comparison to volume in VQIP.
        Needed to enable use of internal_arc, which assumes it is connecting nodes .
        rather than tanks.
        NOTE: this is intended only for use with the internal_arc. Pushing to
        QueueTanks should use 'push_storage'.

        Args:
            vqip (dict, optional): VQIP amount to push. Defaults to None.
            tag (str, optional): Tag, see Node, don't think it should actually be
                used for a QueueTank since there are no handlers. Defaults to
                'default'.

        Returns:
            excess (dict): a VQIP amount of excess capacity
        """
        # TODO does behaviour for volume = None need to be defined?
        excess = self.get_excess()
        if vqip is not None:
            excess["volume"] = min(vqip["volume"], excess["volume"])
        return excess

    def push_set(self, vqip, tag="default"):
        """Behaves differently from normal push setting, it assumes sufficient tank
        capacity and receives VQIPs that have reached the END of the internal_arc.
        NOTE: this is intended only for use with the internal_arc. Pushing to
        QueueTanks should use 'push_storage'.

        Args:
            vqip (dict): VQIP amount to push
            tag (str, optional): Tag, see Node, don't think it should actually be
                used for a QueueTank since there are no handlers. Defaults to
                'default'.

        Returns:
            (dict): Returns empty VQIP, indicating all water received (since it
                assumes capacity was checked before entering the internal arc)
        """
        # Update active_storage (since it has reached the end of the internal_arc)
        self.active_storage = self.sum_vqip(self.active_storage, vqip)

        return self.empty_vqip()

    def _end_timestep(self):
        """Wrapper for end_timestep that also ends the timestep in the internal_arc."""
        self.internal_arc.end_timestep()
        self.internal_arc.update_queue()
        self.storage_ = self.copy_vqip(self.storage)

    def reinit(self):
        """Zeros storages and arc."""
        self.internal_arc.reinit()
        self.storage = self.empty_vqip()
        self.storage_ = self.empty_vqip()
        self.active_storage = self.empty_vqip()


class DecayQueueTank(QueueTank):
    """"""

    def __init__(self, decays={}, parent=None, number_of_timesteps=1, **kwargs):
        """Adds a DecayAltArc in QueueTank to enable decay to occur within the
        internal_arc queue.

        Args:
            decays (dict): A dict of dicts containing a key for each pollutant and,
                within that, a key for each parameter (a constant and exponent)
            parent (object): An object that can be used to read temperature data from
            number_of_timesteps (int, optional): Built in delay for the internal
                queue - it is always added to the queue time, although delay can be
                provided with pushes only. Defaults to 0.
        """
        # Initialise QueueTank
        super().__init__(number_of_timesteps=number_of_timesteps, **kwargs)
        # Replace internal_arc with a DecayArcAlt
        self.internal_arc = DecayArcAlt(
            in_port=self,
            out_port=self,
            number_of_timesteps=number_of_timesteps,
            parent=parent,
            decays=decays,
        )

        self.end_timestep = self._end_timestep

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the decayqueuetank.

        Enables a user to override any of the following parameters:
        number_of_timesteps, decays.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.number_of_timesteps = overrides.pop(
            "number_of_timesteps", self.number_of_timesteps
        )
        self.internal_arc.number_of_timesteps = self.number_of_timesteps
        self.internal_arc.decays.update(overrides.pop("decays", {}))
        super().apply_overrides(overrides)

    def _end_timestep(self):
        """End timestep wrapper that removes decayed pollutants and calls internal
        arc."""
        # TODO Should the active storage decay if decays are given (probably.. though
        #   that sounds like a nightmare)?
        self.storage = self.extract_vqip(self.storage, self.internal_arc.total_decayed)
        self.storage_ = self.copy_vqip(self.storage)
        self.internal_arc.end_timestep()
