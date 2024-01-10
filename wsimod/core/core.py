# -*- coding: utf-8 -*-
"""Created on Wed Apr  7 15:44:48 2021.

@author: Barney

Converted to totals on Thur Apr 21 2022
"""
from math import log10

from wsimod.core import constants


class WSIObj:
    """"""

    def __init__(self):
        """WSIObj is the base object of everything in WSIMOD. It is used to perform VQIP
        operations and mass balance checking behaviour.

        RSE has suggested that it would make more sense to leave VQIP operations as
        regular functions in a module or associated them with a VQIP class.

        Predefining empty_vqip_predefined in a class object is sensible though because
        it is the foundation of many operations, and copying a dict is many times
        quicker than copying a class.

        For now I will leave WSIObj as the base object, but this may change.
        """
        # Predefine empty concentrations because copying is quicker than defining
        self.empty_vqip_predefined = dict.fromkeys(constants.POLLUTANTS + ["volume"], 0)

    def empty_vqip(self):
        """Return a copy of the predefined empty vqip. All pollutants and volume
        initialised in a dict and set to 0.

        Returns:
            empty_vqip_predefined (dict): Copy of empty_vqip_predefined

        Examples:
            >>> obj = WSIObj()
            >>> obj.empty_vqip()
        """
        return self.empty_vqip_predefined.copy()

    def copy_vqip(self, t):
        """Wrapper to copy VQIP.

        Args:
            t (dict): A VQIP

        Returns:
            (dict): A copy of t
        """
        return t.copy()

    def blend_vqip(self, c1, c2):
        """Blends together two VQIPs that are assumed to have pollutant entries set as
        pollution concentrations, blending occurs with proportionate mixing.

        NOTE: VQIPs in WSIMOD in general store pollution as a total rather than a
        concentration. So you should only blend if you are doing it intentionally and
        know what you're doing. This won't do anything on VQIPs with 0 volume.

        Args:
            c1 (dict): A VQIP where pollutant entries are concentrations c2 (dict): A
            VQIP where pollutant entries are concentrations

        Returns:
            c (dict): A new VQIP where c1 and c2 have been proportionately blended
        """
        # Blend two vqips given as concentrations
        c = self.empty_vqip()

        c["volume"] = c1["volume"] + c2["volume"]
        if c["volume"] > 0:
            for pollutant in constants.POLLUTANTS:
                c[pollutant] = (
                    c1[pollutant] * c1["volume"] + c2[pollutant] * c2["volume"]
                ) / c["volume"]

        return c

    def sum_vqip(self, t1, t2):
        """Combines two VQIPs where pollutant entries are assumed to be given as mass.
        Volume and additive pollutants are summed while non additive pollutants are
        proportionately blended.

        Args:
            t1 (dict): A VQIP where pollutant entries are mass totals t2 (dict): A VQIP
            where pollutant entries are mass totals

        Returns:
            t (dict): A VQIP that is the sum of t1 and t2 (except for non-additive
                pollutants)

        Examples:
            >>> t1 = {'phosphate' : 0.25, 'volume' : 100, 'temperature' : 10}
            >>> t2 = {'phosphate' : 0.25, 'volume' : 10, 'temperature' : 15}
            >>> t = sum_vqip(t1, t2)
            >>> print(t)
            {'phosphate' : 0.5, 'volume' : 110, 'temperature' : 10.45}
        """
        # Sum two vqips given as totals
        t = self.copy_vqip(t1)
        t["volume"] += t2["volume"]
        for pollutant in constants.ADDITIVE_POLLUTANTS:
            t[pollutant] += t2[pollutant]

        if t["volume"] > 0:
            # Assume proportional blending of non additive pollutants
            for pollutant in constants.NON_ADDITIVE_POLLUTANTS:
                t[pollutant] = (
                    t2[pollutant] * t2["volume"] + t1[pollutant] * t1["volume"]
                ) / t["volume"]

        return t

    def concentration_to_total(self, c):
        """Convert a VQIP that has pollutant entries as concentrations into mass totals.

        Args:
            c (dict): A VQIP where pollutant entries are concentrations

        Returns:
            c (dict): A VQIP where pollutant entries are mass totals
        """
        c = self.copy_vqip(c)
        for pollutant in constants.ADDITIVE_POLLUTANTS:
            # Multiply concentration by volume to get mass for additive pollutants
            c[pollutant] *= c["volume"]
        return c

    def total_to_concentration(self, t):
        """Converts a VQIP that has pollutant entries as mass totals into
        concentrations. Note, that this won't work for VQIPs with 0 volume.

        Args:
            t (dict): A VQIP where pollutant entries are mass totals

        Returns:
            c (dict): A VQIP where pollutant entries are concentrations
        """
        c = self.copy_vqip(t)
        for pollutant in constants.ADDITIVE_POLLUTANTS:
            # Divide concentration by volume to get concentration for additive
            # pollutants
            c[pollutant] /= c["volume"]
        return c

    def extract_vqip(self, t1, t2):
        """Extract one VQIP from another where both VQIPs have pollutants as mass
        totals. Each volume and additive pollutant is directly subtracted.

        Args:
            t1 (dict): A VQIP where pollutant entries are mass totals to subtract
                from
            t2 (dict): A VQIP where pollutant entries are mass totals to subtract

        Returns:
            t (dict): A copy of t1 where each additive pollutant and volume has had
                t2 subtracted from it

        Examples:
            >>> t1 = {'phosphate' : 0.25, 'volume' : 100, 'temperature' : 10}
            >>> t2 = {'phosphate' : 0.25, 'volume' : 10, 'temperature' : 15}

            >>> t = extract_vqip(t1, t2)
            >>> print(t)
            {'phosphate' : 0, 'volume' : 90, 'temperature' : 10}
        """
        # TODO should probably be called 'subtract_vqip' TODO need to analyse uses of
        # this to see if it is sensible to do something for non additive
        t = self.copy_vqip(t1)
        # Directly subtract t2 from t1 for vol and additive pollutants
        for pol in constants.ADDITIVE_POLLUTANTS + ["volume"]:
            t[pol] -= t2[pol]

        return t

    def extract_vqip_c(self, c1, c2):
        """Extract one VQIP from another where both VQIPs have pollutants as
        concentrations. Operation performed for volume and additive pollutants.

        NOTE: VQIPs in WSIMOD in general store pollution as a total rather than a
        concentration. So you should only work with concentrations if you are doing it
        intentionally and know what you're doing.

        Args:
            c1 (dict): A VQIP where pollutant entries are concentrations to subtract
                from
            c2 (dict): A VQIP where pollutant entries are concentrations to subtract

        Returns:
            c (dict): A copy of c1 where each additive pollutant and volume has had
                c2 proportionately extracted from it
        """
        c = self.copy_vqip(c1)

        c1 = self.concentration_to_total(c1)
        c2 = self.concentration_to_total(c2)
        c["volume"] = c1["volume"] - c2["volume"]
        if c["volume"] > 0:
            for pollutant in constants.ADDITIVE_POLLUTANTS:
                # Subtract c2 from c1 for vol and additive pollutants
                c[pollutant] = (c1[pollutant] - c2[pollutant]) / c["volume"]

        return c

    def v_distill_vqip(self, t, v):
        """Directly remove a volume from a VQIP.

        Args:
            t (dict): A VQIP where pollutant entries are mass totals to remove
                volume from
            v (float): Volume to remove

        Returns:
            t (dict): Updated VQIP
        """
        # Distill v from t
        t = self.copy_vqip(t)
        t["volume"] -= v
        return t

    def v_distill_vqip_c(self, c, v):
        """Directly remove a volume from a VQIP, where pollutant entries are
        concentrations.

        NOTE: VQIPs in WSIMOD in general store pollution as a total rather than a
        concentration. So you should only work with concentrations if you are doing it
        intentionally and know what you're doing.

        Args:
            c (dict): A VQIP where pollutant entries are concentrations to remove
                volume from
            v (float): Volume to remove

        Returns:
            c (dict): Updated VQIP
        """
        # Distill v from c
        c = self.copy_vqip(c)
        d = self.empty_vqip()
        d["volume"] = -v
        c_ = self.blend_vqip(c, d)
        # Directly copy non additive pollutants
        for pollutant in constants.NON_ADDITIVE_POLLUTANTS:
            c_[pollutant] = c[pollutant]
        return c_

    def v_change_vqip(self, t, v):
        """Change the volume of a VQIP, where pollutants are mass totals, and update
        pollutant values in proportion to the change in volume.

        Args:
            t (dict): A VQIP where pollutant entries are mass totals to get
                pollutant concentrations from
            v (float): Volume from t to get proportionate pollutant values in

        Returns:
            (dict): A VQIP with v volume and pollutions in proportion to t

        Examples:
            You want to extract 10m3 from 100m3 of water (store), to do this you need to
            understand how much phosphate to extract in addition to volume.

            >>> store = {'volume' : 100, 'phosphate' : 0.25}
            >>> to_extract = v_change_vqip(store, 10)

            >>> print(to_extract)
            {'volume': 10, 'phosphate': 0.025}
        """
        t = self.copy_vqip(t)
        if t["volume"] > 0:
            # change all values of t by volume v in proportion to volume of t
            ratio = v / t["volume"]
            t["volume"] *= ratio
            for pol in constants.ADDITIVE_POLLUTANTS:
                t[pol] *= ratio

        else:
            # Assign volume directly
            t["volume"] = v
        return t

    def v_change_vqip_c(self, c, v):
        """Change the volume of a VQIP, where pollutants are concentrations.

        NOTE: VQIPs in WSIMOD in general store pollution as a total rather than a
        concentration. So you should only work with concentrations if you are doing it
        intentionally and know what you're doing.

        Args:
            c (dict): A VQIP where pollutant entries are concentrations v (float):
            Volume to change c's volume to

        Returns:
            c (dict): A new VQIP with volume udpated
        """
        # Change volume of vqip
        c = self.copy_vqip(c)
        c["volume"] = v
        return c

    def ds_vqip(self, t, t_):
        """Get difference between each additive pollutant and volume for VQIPs where
        pollutants are given as mass totals.

        Args:
            t (dict): A VQIP where pollutant entries are mass totals to subtract
                values from
            t_ (_type_): A VQIP where pollutant entries are mass totals to subtract

        Returns:
            ds (dict): Difference between t and t_ in mass totals

        Examples:
            >>> t1 = {'phosphate' : 0.25, 'volume' : 100, 'temperature' : 10}
            >>> t2 = {'phosphate' : 0.2, 'volume' : 90, 'temperature' : 9}

            >>> t = ds_vqip(t1, t2)
            >>> print(t)
            {'phosphate' : 0.05, 'volume' : 10, 'temperature' : 0}
        """
        ds = self.empty_vqip()
        for pol in constants.ADDITIVE_POLLUTANTS + ["volume"]:
            ds[pol] = t[pol] - t_[pol]
        return ds

    def ds_vqip_c(self, c, c_):
        """Get difference between each additive pollutant and volume for VQIPs where
        pollutants are given as concentrations but difference is given as mass totals.

        NOTE: VQIPs in WSIMOD in general store pollution as a total rather than a
        concentration. So you should only work with concentrations if you are doing it
        intentionally and know what you're doing.

        Args:
            c (dict): A VQIP where pollutant entries are concentrations to subtract
                values from
            c_ (_type_): A VQIP where pollutant entries are concentrations to
                subtract

        Returns:
            ds (dict): Difference between c and c_ in mass totals
        """
        ds = self.empty_vqip()
        ds["volume"] = c["volume"] - c_["volume"]
        for pol in constants.ADDITIVE_POLLUTANTS:
            ds[pol] = c["volume"] * c[pol] - c_["volume"] * c_[pol]
        # TODO what about non-additive ...
        return ds

    def compare_vqip(self, t1, t2):
        """Compare two VQIPs and check if the difference between each key is less ' than
        constants.FLOAT_ACCURACY.

        Args:
            t1 (dict): A VQIP t2 (dict): A VQIP

        Returns:
            bool: True if the difference is less for each key, False otherwise
        """
        reply = True
        for v in t1.keys():
            if abs(t1[v] - t2[v]) > constants.FLOAT_ACCURACY:
                reply = False
        return reply

    def mass_balance(self):
        """Call all mass balance functions and compare to see if discrepancy (i.e., if
        in_ != (out_ + ds_) for volume or for any additive pollutant).

        Comparison is performed in the magnitude of the largest value of in_, ds_ or
        out_. And so judgement should be exercised as to whether a mass balance has
        actually occurred

        Returns:
            in_ (dict): A VQIP of the total from mass_balance_in functions ds_ (dict): A
            VQIP of the total from mass_balance_ds functions out_ (dict): A VQIP of the
            total from mass_balance_out functions

        Raises:
            Message if mass balance does not close to constants.FLOAT_ACCURACY
        """
        # Iterate over mass_balance_in functions, summing values in in_
        in_ = self.empty_vqip()
        for f in self.mass_balance_in:
            in_ = self.sum_vqip(in_, f())

        # Iterate over mass_balance_out functions, summing values in out_
        out_ = self.empty_vqip()
        for f in self.mass_balance_out:
            out_ = self.sum_vqip(out_, f())

        # Iterate over mass_balance_ds functions, summing values in ds_
        ds_ = self.empty_vqip()
        for f in self.mass_balance_ds:
            ds_f = f()
            for v in constants.ADDITIVE_POLLUTANTS + ["volume"]:
                ds_[v] += ds_f[v]

        # Iterate over volume and additive pollutants to perform comparison
        for v in ["volume"] + constants.ADDITIVE_POLLUTANTS:
            # Find the largest value of in_, out_, ds_
            largest = max(in_[v], out_[v], ds_[v])

            if largest > constants.FLOAT_ACCURACY:
                # Convert perform comparison in a magnitude to match the largest value
                magnitude = 10 ** int(log10(largest))
                in_10 = in_[v] / magnitude
                out_10 = out_[v] / magnitude
                ds_10 = ds_[v] / magnitude
            else:
                in_10 = in_[v]
                ds_10 = ds_[v]
                out_10 = out_[v]

            if abs(in_10 - ds_10 - out_10) > constants.FLOAT_ACCURACY:
                # Print mass balance error Print actual difference rather than magnitude
                # comparison to enable user judgement

                print(
                    "mass balance error for {0} of {1} in {2}".format(
                        v, in_[v] - ds_[v] - out_[v], self.name
                    )
                )

        return in_, ds_, out_


class DecayObj(WSIObj):
    """"""

    # TODO - internet says this is a bad idea (diamond will occur when a Node - a type
    # of WSIObj inherits a DecayObj - also a type of WSIObj). The reason diamonds are
    # problems is because there can be conflicts in functions. But I don't want anyone
    # to overwrite WSIObj functions so I don't see an issue?
    def __init__(self, decays):
        """A WSIObj that has decay functions built in.

        Args:
            decays (dict): A dict of dicts containing a key for each pollutant that
            decays
                and, within that, a key for each parameter (a constant and exponent)

        Examples:
            The 'constant' parameter represents what proportion of an amount will
            decrease each time make_decay is called. Lower value will reduce decay.
            Bounded between 0 and 1. The 'exponent' parameter represents how temperature
            sensitive the decay is. The higher the value, the more pollution occurs at
            higher values. Values expected to vary between 1 (no temperature
            sensitivity) and 1.1 (high temperature sensitivity).

            >>> decays = {'phosphate' : {'constant' : 0.001, 'exponent' : 1.005}}

        Raises:
            Message if no access to temperature data
        """
        # Store decays
        self.decays = decays
        super().__init__()

        # Identify parent object to read temperature data
        if "parent" in dir(self):
            self.data_input_object = self.parent
        elif "in_port" in dir(self):
            self.data_input_object = self.in_port
        else:
            print("warning: decay object cannot access temperature data")

        self.total_decayed = self.empty_vqip()

    def make_decay(self, vqip):
        """Make decay, reading tempature and updating pollutant amounts. A wrapper for
        generic_temperature_decay.

        Args:
            vqip (dict): A VQIP to decay where pollutants are given as mass totals

        Returns:
            vqip_ (dict): A VQIP with pollutant amounts updated
        """
        # Read temperature data
        temperature = self.data_input_object.data_input_dict[
            ("temperature", self.data_input_object.t)
        ]
        # Make decay
        vqip_, diff = self.generic_temperature_decay(vqip, self.decays, temperature)
        # Update total_decayed for mass balance checking
        self.total_decayed = self.sum_vqip(self.total_decayed, diff)
        return vqip_

    def generic_temperature_decay(self, t, d, temperature):
        """Performs temperature sensitive pollutant decay calculations for a VQIP where
        pollutants are given as mass totals.

        Args:
            t (dict): A VQIP to decay where pollutants are given as mass totals d
            (dict): decays in a DecayObj temperature (float): temperature

        Returns:
            t (dict): A VQIP with updated pollutant values diff (dict): A VQIP storing
            the change in pollutant values (decreases
                stored as positive numbers)
        """
        t = self.copy_vqip(t)
        diff = self.empty_vqip()
        # Iterate over pollutants in d (keys)
        for pol, pars in d.items():
            # Perform calculation
            diff[pol] = t[pol] * min(
                pars["constant"]
                * pars["exponent"]
                ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE),
                1,
            )
            # Update VQIP
            t[pol] -= diff[pol]

        return t, diff

    def generic_temperature_decay_c(self, c, d, temperature):
        """Performs temperature sensitive pollutant decay calculations for a VQIP where
        pollutants are given as concentrations.

        Args:
            c (dict): A VQIP to decay where pollutants are given as concentrations. d
            (dict): decays in a DecayObj temperature (float): temperature

        Returns:
            t (dict): A VQIP with updated pollutant values (pollutants as
                concentrations)
            diff (dict): A VQIP storing the change in pollutant values (decreases
                stored as positive numbers). Pollutants as mass totals.
        """
        c = self.copy_vqip(c)
        diff = self.empty_vqip()
        for pol, pars in d.items():
            diff[pol] = c[pol] * min(
                pars["constant"]
                * pars["exponent"]
                ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE),
                1,
            )
            c[pol] -= diff[pol]

            diff[pol] *= c["volume"]
        return c, diff
