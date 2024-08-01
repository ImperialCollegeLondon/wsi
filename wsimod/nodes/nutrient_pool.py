# -*- coding: utf-8 -*-
"""Created on Thu May 19 16:42:20 2022.

@author: barna
"""
from typing import Any, Dict

from wsimod.core import constants


class NutrientPool:
    """"""

    def __init__(
        self,
        fraction_dry_n_to_dissolved_inorganic=0.9,
        degrhpar={"N": 7 * 1e-5, "P": 7 * 1e-6},
        dishpar={"N": 7 * 1e-5, "P": 7 * 1e-6},
        minfpar={"N": 0.00013, "P": 0.000003},
        disfpar={"N": 0.000003, "P": 0.0000001},
        immobdpar={"N": 0.0056, "P": 0.2866},
        fraction_manure_to_dissolved_inorganic={"N": 0.5, "P": 0.1},
        fraction_residue_to_fast={"N": 0.1, "P": 0.1},
    ):
        """A class to track nutrient pools in a soil tank, intended to be initialised
        and called by GrowingSurfaces (see wsimod/nodes/land.py/GrowingSurface) and
        their subclasses. Contains five pools, which have a storage that tracks the mass
        of nutrients. Equations and parameters are based on HYPE.

        Args:
            fraction_dry_n_to_dissolved_inorganic (float, optional): fraction of dry
            nitrogen deposition going into the soil dissolved inorganic nitrogen pool,
            with the rest added to the fast pool. Defaults to 0.9. degrhpar (dict,
            optional): reference humus degradation rate (fraction of humus pool to fast
            pool). Defaults to {'N' : 7 * 1e-5, 'P' : 7 * 1e-6}. dishpar (dict,
            optional): reference humus dissolution rate (fraction of humus pool to
            dissolved organic pool). Defaults to {'N' : 7 * 1e-5, 'P' : 7 * 1e-6}.
            minfpar (dict, optional): reference fast pool mineralisation rate (fraction
            of fast pool to dissolved inorganic pool). Defaults to {'N' : 0.00013, 'P' :
            0.000003}. disfpar (dict, optional): reference fast pool dissolution rate
            (fraction of fast pool to dissolved organic pool). Defaults to {'N' :
            0.000003, 'P' : 0.0000001}. immobdpar (dict, optional): reference
            immobilisation rate (fraction of dissolved inorganic pool to fast pool).
            Defaults to {'N' : 0.0056, 'P' : 0.2866}.
            fraction_manure_to_dissolved_inorganic (dict, optional): fraction of
            nutrients from applied manure to dissolved inorganic pool, with the rest
            added to the fast pool. Defaults to {'N' : 0.5, 'P' : 0.1}.
            fraction_residue_to_fast (dict, optional): fraction of nutrients from
            residue to fast pool, with the rest added to the humus pool. Defaults to
            {'N' : 0.1, 'P' : 0.1}.

        Key assumptions:
             - Four nutrient pools are conceptualised for both nitrogen and phosphorus
                in soil, which includes humus pool, fast pool, dissolved inorganic pool,
                and dissolved organic pool. Humus and fast pool represent immobile pool
                of organic nutrients in the soil with slow and fast turnover,
                respectively. Dissolved inorganic and organic pool represent nutrients
                in dissolved phase in soil water (for phosphorus, dissolved organic pool
                might contain particulate phase). Given that phoshphorus can be adsorbed
                and attached to soil particles, an adsorbed inorganic pool is created
                specifically for phosphorus.
             - The major sources of nutrients to soil are conceptualised as
                - atmospheric deposition:
                    - dry deposition:
                        - for nitrogen, inorganic fraction of dry deposition is added to
                          the dissovled
                           inorganic pool, while the rest is added to the fast pool;
                        - for phosphorus, all is added to adsorbed inorganic pool.
                    - wet deposition: all is added to the dissolved inorganic pool.
                - fertilisers: all added to the dissolved inorganic pool.
                - manure: the inorganic fraction is added to the dissovled inorganic
                  pool, with
                    the rest added to the fast pool.
                - residue: the part with fast turnover is added to the fast pool, with
                  the rest
                    added to the humus pool.
             - Nutrient fluxes between these pools are simulated to represent the
               biochemical processes
                that can transform the nutrients between different forms. These
                processes include - degradation of humus pool to fast pool - dissolution
                of humus pool to dissovled organic pool - mineralisation of fast pool to
                dissolved inorganic pool - dissolution of fast pool to dissolved organic
                pool - immobilisation of dissolved inroganic pool to fast pool The rate
                of these processes are affected by the soil temperature and moisture
                conditions.
             - When soil erosion happens, a portion of both the adsorbed inorganic pool
               and humus pool
                for phosphorus will be eroded as well.

        Input data and parameter requirements:
             - fraction_dry_n_to_dissolved_inorganic,
               fraction_manure_to_dissolved_inorganic, fraction_residue_to_fast.
                _Units_: -, all should in [0-1]
             - degrhpar, dishpar, minfpar, disfpar, immobdpar.
                _Units_: -, all should in [0-1]
        """
        # TODO I don't think anyone will change most of these params... they could maybe
        # just be set here
        self.init_empty()

        # Assign parameters
        self.temperature_dependence_factor = 0
        self.soil_moisture_dependence_factor = 0

        self.fraction_manure_to_dissolved_inorganic = (
            fraction_manure_to_dissolved_inorganic
        )
        self.fraction_residue_to_fast = fraction_residue_to_fast
        self.fraction_dry_n_to_dissolved_inorganic = (
            fraction_dry_n_to_dissolved_inorganic
        )

        self.degrhpar = degrhpar
        self.dishpar = dishpar
        self.minfpar = minfpar
        self.disfpar = disfpar
        self.immobdpar = immobdpar

        self.fraction_manure_to_fast = None
        self.fraction_residue_to_humus = None
        self.fraction_dry_n_to_fast = None
        self.calculate_fraction_parameters()

        # Initialise different pools
        self.fast_pool = NutrientStore()
        self.humus_pool = NutrientStore()
        self.dissolved_inorganic_pool = NutrientStore()
        self.dissolved_organic_pool = NutrientStore()
        self.adsorbed_inorganic_pool = NutrientStore()
        self.pools = [
            self.fast_pool,
            self.humus_pool,
            self.dissolved_inorganic_pool,
            self.dissolved_organic_pool,
            self.adsorbed_inorganic_pool,
        ]

    def calculate_fraction_parameters(self):
        """Update fractions of nutrients input transformed into other forms in soil
        based on the input parameters
        Returns:
            (dict): fraction of manure to fast pool
            (dict): fraction of plant residue to humus pool
            (float): fraction of dry nitrogen deposition to fast pool
        """
        self.fraction_manure_to_fast = {
            x: 1 - self.fraction_manure_to_dissolved_inorganic[x]
            for x in constants.NUTRIENTS
        }
        self.fraction_residue_to_humus = {
            x: 1 - self.fraction_residue_to_fast[x] for x in constants.NUTRIENTS
        }
        self.fraction_dry_n_to_fast = 1 - self.fraction_dry_n_to_dissolved_inorganic

    def apply_overrides(self, overrides=Dict[str, Any]):
        """Override parameters.

        Enables a user to override any of the following parameters:
        eto_to_e, pore_depth.

        Args:
            overrides (Dict[str, Any]): Dict describing which parameters should
                be overridden (keys) and new values (values). Defaults to {}.
        """
        self.fraction_dry_n_to_dissolved_inorganic = overrides.pop(
            "fraction_dry_n_to_dissolved_inorganic",
            self.fraction_dry_n_to_dissolved_inorganic,
        )
        self.fraction_residue_to_fast.update(
            overrides.pop("fraction_residue_to_fast", {})
        )
        self.fraction_manure_to_dissolved_inorganic.update(
            overrides.pop("fraction_manure_to_dissolved_inorganic", {})
        )
        self.degrhpar.update(overrides.pop("degrhpar", {}))
        self.dishpar.update(overrides.pop("dishpar", {}))
        self.minfpar.update(overrides.pop("minfpar", {}))
        self.disfpar.update(overrides.pop("disfpar", {}))
        self.immobdpar.update(overrides.pop("immobdpar", {}))

        self.calculate_fraction_parameters()

    def init_empty(self):
        """Initialise an empty nutrient to be copied."""
        self.empty_nutrient = {x: 0 for x in constants.NUTRIENTS}

    def init_store(self):
        """Initialise an empty store to track nutrients."""
        self.init_empty()
        self.storage = self.get_empty_nutrient()

    def allocate_inorganic_irrigation(self, irrigation):
        """Assign inorganic irrigation, which is assumed to contain dissolved inorganic
        nutrients and thus updates that pool.

        Args:
            irrigation (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via irrigation

        Returns:
            irrigation (dict): irrigation above, because no transformations take place
                (i.e., dissolved inorganic is what is received and goes straight into
                that pool)
        """
        # Update pool
        self.dissolved_inorganic_pool.receive(irrigation)
        return irrigation

    def allocate_organic_irrigation(self, irrigation):
        """Assign organic irrigation, which is assumed to contain dissolved organic
        nutrients and thus updates that pool.

        Args:
            irrigation (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via irrigation

        Returns:
            irrigation (dict): irrigation above, because no transformations take place
                (i.e., dissolved organic is what is received and goes straight into that
                pool)
        """
        # Update pool
        self.dissolved_organic_pool.receive(irrigation)
        return irrigation

    def allocate_dry_deposition(self, deposition):
        """Assign dry deposition, which is assumed to go to both dissolved inorganic
        pool and fast pool (nitrogen) and the adsorbed pool (phosphorus).

        Args:
            deposition (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via dry deposition

        Returns:
            (dict): A dict describing the amount of nutrients that enter the nutrient
                pool in a dissolved form (and thus need to be tracked by the soil water
                tank)
        """
        # Update pools
        self.fast_pool.storage["N"] += deposition["N"] * self.fraction_dry_n_to_fast
        self.dissolved_inorganic_pool.storage["N"] += (
            deposition["N"] * self.fraction_dry_n_to_dissolved_inorganic
        )
        self.adsorbed_inorganic_pool.storage["P"] += deposition["P"]
        return {
            "N": deposition["N"] * self.fraction_dry_n_to_dissolved_inorganic,
            "P": 0,
        }

    def allocate_wet_deposition(self, deposition):
        """Assign wet deposition, which is assumed to contain dissolved inorganic
        nutrients and thus updates that pool.

        Args:
            deposition (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via wet deposition

        Returns:
            deposition (dict): deposition above, because no transformations take place
                (i.e., dissolved inorganic is what is received and goes straight into
                that pool)
        """
        # Update pool
        self.dissolved_inorganic_pool.receive(deposition)
        return deposition

    def allocate_manure(self, manure):
        """Assign manure, which is assumed to go to both dissolved inorganic pool and
        fast pool.

        Args:
            manure (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via manure

        Returns:
            (dict): A dict describing the amount of nutrients that enter the nutrient
                pool in a dissolved form (and thus need to be tracked by the soil water
                tank)
        """
        # Assign a proportion of nutrients to the dissolved inorganic pool
        self.dissolved_inorganic_pool.receive(
            self.multiply_nutrients(manure, self.fraction_manure_to_dissolved_inorganic)
        )
        # Assign a proportion of nutrients to the fast pool
        self.fast_pool.receive(
            self.multiply_nutrients(manure, self.fraction_manure_to_fast)
        )
        return self.multiply_nutrients(
            manure, self.fraction_manure_to_dissolved_inorganic
        )

    def allocate_residue(self, residue):
        """Assign residue, which is assumed to go to both humus pool and fast pool.

        Args:
            residue (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via residue

        Returns:
            (dict): A dict describing the amount of nutrients that enter the nutrient
                pool in a dissolved form (and thus need to be tracked by the soil water
                tank) - i.e., none because fast and humus pool are both solid
        """
        # Assign a proportion of nutrients to the humus pool
        self.humus_pool.receive(
            self.multiply_nutrients(residue, self.fraction_residue_to_humus)
        )
        # Assign a proportion of nutrients to the fast pool
        self.fast_pool.receive(
            self.multiply_nutrients(residue, self.fraction_residue_to_fast)
        )
        return self.empty_nutrient()

    def allocate_fertiliser(self, fertiliser):
        """Assign fertiliser, which is assumed to contain dissolved inorganic nutrients
        and thus updates that pool.

        Args:
            fertiliser (dict): A dict that contains the amount of nutrients entering
                the nutrient pool via fertiliser

        Returns:
            fertiliser (dict): fertiliser above, because no transformations take place
                (i.e., dissolved inorganic is what is received and goes straight into
                that pool)
        """
        self.dissolved_inorganic_pool.receive(fertiliser)
        return fertiliser

    def extract_dissolved(self, proportion):
        """Function to extract some amount of nutrients from all dissolved pools.

        Args:
            proportion (float): proportion of the dissolved nutrient pools to extract

        Returns:
            (dict): A dict of dicts, where the top level distinguishes between organic
                and inorganic nutrients, and the bottom level describes how much
                nutrients (i.e., N and P) have been extracted from those pools
        """
        # Extract from dissolved inorganic pool
        reply_di = self.dissolved_inorganic_pool.extract(
            {
                "N": self.dissolved_inorganic_pool.storage["N"] * proportion,
                "P": self.dissolved_inorganic_pool.storage["P"] * proportion,
            }
        )

        # Extract from dissolved organic pool
        reply_do = self.dissolved_organic_pool.extract(
            {
                "N": self.dissolved_organic_pool.storage["N"] * proportion,
                "P": self.dissolved_organic_pool.storage["P"] * proportion,
            }
        )
        return {"organic": reply_do, "inorganic": reply_di}

    def get_erodable_P(self):
        """Return total phosphorus that can be eroded (i.e., humus and adsorbed
        inorganic pools).

        Returns:
            (float): total phosphorus
        """
        return self.adsorbed_inorganic_pool.storage["P"] + self.humus_pool.storage["P"]

    def erode_P(self, amount_P):
        """Update humus and adsorbed inorganic pools to erode some amount. Removed in
        proportion to amount in both pools.

        Args:
            amount_P (float): Amount of phosphorus to be eroded

        Returns:
            (float): Amount of phosphorus eroded from the humus pool (float): Amount of
            phosphorus eroded from the adsorbed inorganic pool
        """
        # Calculate proportion of adsorbed to be eroded
        fraction_adsorbed = self.adsorbed_inorganic_pool.storage["P"] / (
            self.adsorbed_inorganic_pool.storage["P"] + self.humus_pool.storage["P"]
        )

        # Update nutrients in a dict holder
        request = self.get_empty_nutrient()

        # Update inorganic pool
        request["P"] = amount_P * fraction_adsorbed
        reply_adsorbed = self.adsorbed_inorganic_pool.extract(request)

        # Update humus pool
        request["P"] = amount_P * (1 - fraction_adsorbed)
        reply_humus = self.humus_pool.extract(request)

        return reply_humus["P"], reply_adsorbed["P"]

    def soil_pool_transformation(self):
        """Function to be called by a GrowingSurface that performs and tracks changes
        resulting from soil transformation processes.

        Returns:
            (float): increase in dissolved inorganic nutrients resulting from
                transformations (negative value indicates a decrease)
            (float): increase in dissolved organic nutrients resulting from
                transformations (negative value indicates a decrease)
        """
        # For mass balance purposes, assume fast is inorganic and humus is organic

        # Initialise tracking
        increase_in_dissolved_inorganic = self.get_empty_nutrient()
        increase_in_dissolved_organic = self.get_empty_nutrient()

        # Turnover of humus
        amount = self.temp_soil_process(self.degrhpar, self.humus_pool, self.fast_pool)
        # This is solid inorganic to solid organic... no tracking needed since solid
        # nutrients aren't tracked in mass balance of the surface soil water tank!

        # Dissolution of humus
        amount = self.temp_soil_process(
            self.dishpar, self.humus_pool, self.dissolved_organic_pool
        )
        increase_in_dissolved_organic = self.sum_nutrients(
            increase_in_dissolved_organic, amount
        )

        # Turnover of fast
        amount = self.temp_soil_process(
            self.minfpar, self.fast_pool, self.dissolved_inorganic_pool
        )
        increase_in_dissolved_inorganic = self.sum_nutrients(
            increase_in_dissolved_inorganic, amount
        )

        # Dissolution of fast
        amount = self.temp_soil_process(
            self.disfpar, self.fast_pool, self.dissolved_organic_pool
        )
        increase_in_dissolved_organic = self.sum_nutrients(
            increase_in_dissolved_organic, amount
        )

        # Immobilisation
        amount = self.temp_soil_process(
            self.immobdpar, self.dissolved_inorganic_pool, self.fast_pool
        )
        increase_in_dissolved_inorganic = self.subtract_nutrients(
            increase_in_dissolved_inorganic, amount
        )  # TODO will a negative value affect the consequent processes in growing
        # surface?

        return increase_in_dissolved_inorganic, increase_in_dissolved_organic

    def temp_soil_process(self, parameter, extract_pool, receive_pool):
        """Temperature function to take a parameter, calculate transformation, and
        remove nutrients from the extract pool and update the receive pool.

        Args:
            parameter (dict): A dict containing a parameter for each nutrient for the
            given process
                (units in per timestep)
            extract_pool (NutrientStore): The pool to extract from receive_pool
            (NutrientStore): The pool to receive extracted nutrients

        Returns:
            to_extract (dict): A dict containing the amount extracted of each nutrient
            (for mass
                balance)
        """
        # Initialise nutrients
        to_extract = self.get_empty_nutrient()
        for nutrient in constants.NUTRIENTS:
            # Calculate
            to_extract[nutrient] = (
                parameter[nutrient]
                * self.temperature_dependence_factor
                * self.soil_moisture_dependence_factor
                * extract_pool.storage[nutrient]
            )
        # Update pools
        to_extract = extract_pool.extract(to_extract)
        receive_pool.receive(to_extract)
        return to_extract

    def get_empty_nutrient(self):
        """An efficient way to get an empty nutrient.

        Returns:
            (dict): A dict containing 0 for each nutrient
        """
        return self.empty_nutrient.copy()

    def multiply_nutrients(self, nutrient, factor):
        """Multiply nutrients by factors.

        Args:
            nutrient (dict): Dict of nutrients to multiply factor (dict): Dict of
            factors to multiply for each nutrient

        Returns:
            (dict): Multiplied nutrients
        """
        return {x: nutrient[x] * factor[x] for x in constants.NUTRIENTS}

    def receive(self, nutrients):
        """Update nutrient store by amounts.

        Args:
            nutrients (dict): Amount of nutrients to update store by
        """
        # Increase storage
        for nutrient, amount in nutrients.items():
            self.storage[nutrient] += amount

    def sum_nutrients(self, n1, n2):
        """Sum two nutrients.

        Args:
            n1 (dict): Dict of nutrients n2 (dict): Dict of nutrients

        Returns:
            (dict): Summed nutrients
        """
        reply = self.get_empty_nutrient()
        for nutrient in constants.NUTRIENTS:
            reply[nutrient] = n1[nutrient] + n2[nutrient]
        return reply

    def subtract_nutrients(self, n1, n2):
        """Subtract two nutrients.

        Args:
            n1 (dict): Dict of nutrients to subtract from n2 (dict): Dict of nutrients
            to subtract

        Returns:
            (dict): subtracted nutrients
        """
        reply = self.get_empty_nutrient()
        for nutrient in constants.NUTRIENTS:
            reply[nutrient] = n1[nutrient] - n2[nutrient]
        return reply

    def extract(self, nutrients):
        """Remove nutrients from a store.

        Args:
            nutrients (dict): Dict of nutrients to remove from store

        Returns:
            (dict): amount of nutrients successfully removed
        """
        reply = self.get_empty_nutrient()
        for nutrient, amount in nutrients.items():
            reply[nutrient] = min(self.storage[nutrient], amount)
            self.storage[nutrient] -= reply[nutrient]

        return reply


class NutrientStore(NutrientPool):
    """"""

    def __init__(self):
        """Nutrient store, to be instantiated by a NutrientPool."""
        super().init_store()
