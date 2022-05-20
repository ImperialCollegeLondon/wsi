# -*- coding: utf-8 -*-
"""
Created on Thu May 19 16:42:20 2022

@author: barna
"""
from wsimod.core import constants

class NutrientPool:
    def __init__(self, **kwargs):
        self.init_empty()
        
        self.temperature_dependence_factor = 0
        self.soil_moisture_dependence_factor = 0
        
        self.fraction_manure_to_dissolved_inorganic = self.get_empty_nutrient()
        self.fraction_residue_to_fast = self.get_empty_nutrient()
        self.fraction_dry_n_to_dissolved_inorganic = 0
        
        self.degrhpar = self.get_empty_nutrient()
        self.dishpar = self.get_empty_nutrient()
        self.minfpar = self.get_empty_nutrient()
        self.disfpar = self.get_empty_nutrient()
        self.immobdpar = self.get_empty_nutrient()
        
        self.__dict__.update(kwargs)
        
        self.fraction_manure_to_fast = {x : 1 - self.fraction_manure_to_dissolved_inorganic[x] for x in constants.NUTRIENTS}
        self.fraction_residue_to_humus = {x : 1 - self.fraction_residue_to_fast[x] for x in constants.NUTRIENTS}
        self.fraction_dry_n_to_fast = 1 - self.fraction_dry_n_to_dissolved_inorganic
        
        
        self.fast_pool = NutrientStore()
        self.humus_pool = NutrientStore()
        self.dissolved_inorganic_pool = NutrientStore()
        self.dissolved_organic_pool = NutrientStore()
        self.adsorbed_inorganic_pool = NutrientStore()
        
    def init_empty(self):
        self.empty_nutrient = {x : 0 for x in constants.NUTRIENTS}
        
    def init_store(self):
        self.init_empty()
        self.storage = self.get_empty_nutrient()
    
    def allocate_inorganic_irrigation(self, irrigation):
        self.dissolved_inorganic_pool.receive(irrigation)
        
    def allocate_organic_irrigation(self, irrigation):
        self.dissolved_organic_pool.receive(irrigation)
    
    def allocate_dry_deposition(self, deposition):
        self.fast_pool.storage['N'] += deposition['N'] * self.fraction_dry_n_to_fast
        self.dissolved_inorganic_pool.storage['N'] += deposition['N'] * self.fraction_dry_n_to_dissolved_inorganic
        self.adsorbed_inorganic_pool.storage['P'] += deposition['P']
        
    def allocate_wet_deposition(self, deposition):
        self.dissolved_inorganic_pool.receive(deposition)
        
    def allocate_manure(self, manure):
        self.dissolved_inorganic_pool.receive(self.multiply_nutrients(manure,
                                                                      self.fraction_manure_to_dissolved_inorganic))
        self.fast_pool.receive(self.multiply_nutrients(manure,
                                                       self.fraction_manure_to_fast))
    def allocate_residue(self, residue):
        self.humus.receive(self.multiply_nutrients(residue,
                                                   self.fraction_residue_to_humus))
        self.fast_pool.receive(self.multiply_nutrients(residue,
                                                       self.fraction_residue_to_fast))    
    def allocate_fertiliser(self, fertiliser):
        self.dissolved_inorganic_pool.receive(fertiliser)
        
    def soil_pool_transformation(self):
        self.temp_soil_process(self.degrhpar, self.humus_pool, self.fast_pool)
        self.temp_soil_process(self.dishpar, self.humus_pool, self.dissolved_organic_pool)
        self.temp_soil_process(self.minfpar, self.fast_pool, self.dissolved_inorganic_pool)
        self.temp_soil_process(self.disfpar, self.fast_pool, self.dissolved_organic_pool)
        self.temp_soil_process(self.immobdpar, self.dissolved_organic_pool, self.fast_pool)

    def temp_soil_process(self, parameter, extract_pool, receive_pool):
        to_extract = self.get_empty_nutrient()
        for nutrient in constants.NUTRIENTS:
            to_extract[nutrient] = parameter[nutrient] *\
                                            self.temperature_dependence_factor *\
                                            self.soil_moisture_dependence_factor *\
                                            extract_pool[nutrient]
        to_extract = extract_pool.extract(to_extract)
        receive_pool.receive(to_extract)

    def get_empty_nutrient(self):
        return self.empty_nutrient.copy()
    
    def multiply_nutrients(self, nutrient, factor):
        return {x : nutrient[x] * factor[x] for x in constants.NUTRIENTS}
    
    def receive(self, nutrients):
        for nutrient, amount in nutrients.items():
            self.storage[nutrient] += amount
    
    def extract(self, nutrients):
        reply = self.get_empty_nutrient()
        for nutrient, amount in nutrients.items():
            reply[nutrient] = min(self.storage[nutrient], amount)
            self.storage[nutrient] -= reply[nutrient]

        return reply

class NutrientStore(NutrientPool):
    def __init__(self, **kwargs):
        super().init_store()

#TODO: Adsorption/desorption, denitification, erosion, suspension/runoff/etc.
 