# -*- coding: utf-8 -*-
"""
Created on Fri May 20 08:58:58 2022

@author: Barney
"""
from wsimod.nodes.nodes import Node, Tank, DecayTank, QueueTank
from wsimod.nodes.nutrient_pool import NutrientPool
from wsimod.core import constants
import sys

class Land_(Node):
    def __init__(self, **kwargs):
        surfaces_ = kwargs['surfaces'].copy()
        surfaces = []
        for surface in surfaces_:
            surface['parent'] = self
            surfaces.append(getattr(sys.modules[__name__], surface['type'])(**surface))
        self.surfaces = surfaces

    def run(self):
        for surface in self.surfaces:
            surface.run()
    
    def get_data_input(self, var):
        return self.data_input_dict[(var, self.t)]
    
class Surface(Tank):
    def __init__(self, **kwargs):
        #TODO EVERYONE INHERITS THIS DEPTH VALUE... FIX THAT
        self.depth = 0
        
        #Parameters
        self.fraction_dry_deposition_to_DIN = 0.9 #TODO may or may not be handled in preprocessing
        
        super().__init__(**kwargs)
        
        
        self.capacity = self.depth * self.area

        self.fraction_dry_deposition_to_DON = 1 - self.fraction_dry_deposition_to_DIN
        
        self.inflows = [self.atmospheric_deposition,
                        self.precipitation_deposition]
        self.processes = [lambda x: None]
        self.outflows = [lambda x: None]
        
    def run(self):
        for f in self.inflows + self.processes + self.outflows:
            f()
        #TODO can probably incorporate mass balance here?
    
    def get_data_input(self, var):
        return self.parent.get_data_input(var)
    
    def deposition_to_tank(self, vqip):
        _ = self.push_storage(vqip, force = True)
        
    
    def atmospheric_deposition(self):
        nhx = self.get_data_input('nhx-dry') * self.area
        nox = self.get_data_input('nox-dry') * self.area
        
        vqip = self.empty_vqip()
        #TODO convert to nitrate/nitrite/ammonia and push to tank. See SWAT
        vqip['ammonia'] = nhx
        vqip['nitrogen'] = nox
        
        self.deposition_to_tank(vqip)
        
        
    def precipitation_deposition(self):
        nhx = self.get_data_input('nhx-wet') * self.area
        nox = self.get_data_input('nox-wet') * self.area
        
        vqip = self.empty_vqip()
        #TODO convert to nitrate/nitrite/ammonia and push to tank. See SWAT
        vqip['ammonia'] = nhx
        vqip['nitrogen'] = nox
        
        self.deposition_to_tank(vqip)
        
class ImperviousSurface(Surface):
    def __init__(self, **kwargs):
        self.pore_depth = 0 #Need a way to say 'depth means pore depth'
        kwargs['depth'] = kwargs['pore_depth'] # TODO Need better way to handle this
        
        super().__init__(**kwargs)
        
        self.inflows.append(self.urban_deposition)
        self.inflows.append(self.precipitation_evaporation)
        
        self.outflows.append(self.push_to_sewers)
    
    def urban_deposition(self):
        pass
    
    def precipitation_evaporation(self):
        pass
    
    def push_to_sewers(self):
        pass
    
class PerviousSurface(Surface):
    def __init__(self, **kwargs):
        self.field_capacity = 0 #depth of water when water level is above this, recharge/percolation are generated
        self.infiltration_capacity = 0 #depth of precipitation that can enter tank per timestep
        self.percolation_coefficient = 0 #proportion of water above field capacity that can goes to percolation
        self.subsurface_coefficient = 0 #proportion of water above field capacity that can goes to subsurface flow
        self.decays = 0 #generic decay parameters
        
        #TODO what should these params be?
        self.soil_temp_w_prev = 0.3 #previous timestep weighting
        self.soil_temp_w_air = 0.3 #air temperature weighting
        self.soil_temp_cons = 3 #deep soil temperature * weighting
        
        kwargs['depth'] = kwargs['field_capacity'] # TODO Need better way to handle this
        
        super().__init__(**kwargs)
        
        self.inflows.append(self.precipitation_infiltration_evaporation) #work out runoff
        
        self.processes.append(self.calculate_soil_temperature) # Calculate soil temp + dependence factor
        self.processes.append(self.decay) #apply generic decay
        self.processes.append(self.hydrology) #work out how much is going to subsurface flow/percolation
        
        self.outflows.append(self.push_to_rivers)

    def precipitation_infiltration_evaporation(self):
        pass
    
    def calculate_soil_temperature(self):
        auto = self.storage['temperature'] * self.soil_temp_w_prev
        air = self.get_data_input('temperature') * self.soil_temp_w_air
        self.soil_storage['temperature'] = auto + air + self.soil_temp_cons
    
    def decay(self):
        pass
    
    def hydrology(self):
        pass

    def push_to_rivers(self):
        pass

class CropSurface(PerviousSurface):
    def __init__(self, **kwargs):
        self.stage_dates = [] #dates when crops are planted/growing/harvested
        self.crop_factor = [] #coefficient to do with ET, associated with stages
        self.ET_depletion_factor = 0 #To do with water availability, p from FAOSTAT
        self.rooting_depth = 0 #To do with water availability, Zr from FAOSTAT
        self.wilting_point = 0 #Depth of water when added to field capacity, water is available for plants+evaporation but not drainage
        
        self.nutrient_parameters = {}
        
        kwargs['depth'] = kwargs['field_capacity'] + kwargs['wilting_point'] # TODO Need better way to handle this
        
        super().__init__(**kwargs)
        
        self.nutrient_pool = NutrientPool(**self.nutrient_parameters)
        
        self.inflows.append(self.fertiliser)
        self.inflows.append(self.manure)
        
        self.processes.append(self.soil_moisture_dependence_factor)
        self.processes.append(self.nutrient_pool.soil_pool_transformation)
        
        #TODO possibly move these into nutrient pool
        self.processes.append(self.suspension)
        self.processes.append(self.erosion)
        self.processes.append(self.denitrification)
        self.processes.append(self.adsorption)
    
    def soil_moisture_dependence_factor(self):
        pass
    
    def fertiliser(self):
        pass
    
    def manure(self):
        pass
    
    def suspension(self):
        pass
    
    def erosion(self):
        pass
    
    def denitrification(self):
        pass
    
    def adsorption(self):
        pass
    
    def deposition_to_tank(self, vqip):
        #Distribute between surfaces
        pass
    

    
class IrrigationSurface(CropSurface):
    def __init__(self, **kwargs):
        self.irrigation_cover = 0 #proportion area irrigated
        self.irrigation_efficiency = 0 #proportion of demand met
        
        super().__init__(**kwargs)
        
        self.inflows.append(self.calculate_irrigation)
        self.inflows.append(self.satisfy_irrigation)
        
        self.processes.append(self.crop_uptake)
        
    def calculate_irrigation(self):
        pass
    
    def crop_uptake(self):
        pass
    
    def satisfy_irrigation(self):
        pass

class GardenSurface(IrrigationSurface):
    #TODO - probably a simplier version of this is useful, building just on pervioussurface
    def __init__(self, **kwargs):
        self.satisfy_irrigation = self.pull_from_distribution
        
        super().__init__(**kwargs)
        
    def pull_from_distribution(self):
        pass