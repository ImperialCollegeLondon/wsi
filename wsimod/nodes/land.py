# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node, Tank, QueueTank
from wsimod.core import constants

class Land(Node):
    def __init__(self, **kwargs):
        self.subsurface_timearea = {0 : 0.3,
                                    1 : 0.3,
                                    2 : 0.2,
                                    3 : 0.1,
                                    4 : 0.1}
        
        surfaces_ = kwargs['surfaces'].copy()
        surfaces = {}
        for sname, surface in surfaces_.items():
            surfaces[sname] = Surface(**surface)
            surfaces[sname].parent = self
            
        super().__init__(**kwargs)
        
        #A different change (e.g.)

        
        self.surfaces = surfaces

        #Update handlers
        self.push_set_handler['Sewer'] = self.push_set_flood
        self.push_set_handler[('Demand','Garden')] = self.push_set_garden
        self.push_check_handler[('Demand','Garden')] = self.push_check_garden
        
        #Initiliase values
        self.total_evaporation = 0
        self.total_precipitation = self.empty_vqip()
        self.total_infiltration = self.empty_vqip()
        self.total_percolation = self.empty_vqip()
        self.total_subsurface_runoff = self.empty_vqip()
        self.total_surface_runoff = self.empty_vqip()
        
        self.subsurface_flow = QueueTank(capacity = constants.UNBOUNDED_CAPACITY,
                                              area = constants.UNBOUNDED_CAPACITY,
                                              datum = 0,
                                              number_of_timesteps = 0
                                              )
        
        
         
        #Mass balance (this is so untidy... must be a better way)
        self.mass_balance_in = [self.total_in]
        self.mass_balance_out = [self.total_out]
        self.mass_balance_ds = [lambda : self.empty_vqip()]
        
        for surface in self.surfaces.values():
            self.mass_balance_ds.append(surface.ds)
            self.mass_balance_in.append(surface.get_deposition)
            
        self.mass_balance_ds.append(self.subsurface_flow.ds)
        self.mass_balance_in.append(lambda : self.total_precipitation)
        self.mass_balance_out.append(lambda : self.v_change_vqip(self.empty_vqip(), self.total_evaporation))
        
    def create_runoff(self):
        #Temporary variable to keep track of everything
        temp_tracking = {'precipitation' : {},
                            'infiltration' : {},
                            'evaporation' : {},
                            'percolation' : {},
                            'subsurface_runoff' : {},
                            'surface_runoff' : {}}
        
        #Update surfaces
        for sname, surface in self.surfaces.items():
            #Make rain
            surface_excess, infiltration, evaporation, precipitation = surface.apply_precipitation_infiltration_evaporation()
            temp_tracking['precipitation'][sname] = precipitation
            temp_tracking['evaporation'][sname] = evaporation
            temp_tracking['infiltration'][sname] = infiltration
            
            # ponded = surface.pull_ponded()
            # percolation = self.v_change_vqip(ponded,ponded['volume'] * surface.percolation_coefficient)
            # subsurface_runoff = self.v_change_vqip(ponded,ponded['volume'] * (1 - surface.percolation_coefficient))
            # surface_runoff = surface_excess
            
            # Get percolation (slow flow) and subsurface runoff (quick flow)
            percolation, subsurface_runoff = surface.pull_outflows()
            temp_tracking['percolation'][sname] = percolation
            temp_tracking['subsurface_runoff'][sname] = subsurface_runoff
            
            # #Get runoff
            surface_runoff = self.blend_vqip(surface.pull_ponded(), surface_excess)
            temp_tracking['surface_runoff'][sname] = surface_runoff
            
            #Update totals
            self.total_percolation = self.blend_vqip(self.total_percolation, percolation)
            self.total_infiltration = self.blend_vqip(self.total_infiltration, infiltration)
            self.total_evaporation += evaporation
            self.total_precipitation = self.blend_vqip(self.total_precipitation, precipitation)
            self.total_subsurface_runoff = self.blend_vqip(self.total_subsurface_runoff, subsurface_runoff)

            #Drain sewers 
            if surface == 'impervious':
                reply = self.push_distributed(surface_runoff, of_type = ['Sewer'])
                _ = surface.tank.push_storage(reply, force = True)
            else:
                self.total_surface_runoff = self.blend_vqip(self.total_surface_runoff, surface_runoff)

        
        for time, normalised in self.subsurface_timearea.items():
            subsurface_runoff_ = self.v_change_vqip(self.total_subsurface_runoff, 
                                                    self.total_subsurface_runoff['volume'] * normalised)
            reply = self.subsurface_flow.push_storage(subsurface_runoff_,
                                                      time = time) # TODO Should this be forced?
            if reply['volume'] > constants.FLOAT_ACCURACY:
                print('weird for subsurface')
        
        
        subsurface_runoff_leaving = self.subsurface_flow.pull_storage(self.subsurface_flow.active_storage)
        
        percolation_remaining = self.push_distributed(self.total_percolation, of_type = ['Groundwater'])
        
        amount_entering_rivers = self.blend_vqip(self.total_surface_runoff, subsurface_runoff_leaving)

        runoff_remaining = self.push_distributed(amount_entering_rivers, of_type = ['Node']) #TODO seems suspicious.. do I need 'not of type'?

        #Redistribute unsent percolation
        if percolation_remaining['volume'] > constants.FLOAT_ACCURACY:
            print('infiltraiton remaining')
            #Calculate proportion
            proportions = {sname : value['volume'] / self.total_percolation['volume'] for sname, value in temp_tracking['percolation'].items()}
            self.redistribute_to_surfaces(proportions, temp_tracking['percolation'], percolation_remaining['volume'])
            
        #Redistribute amount_entering rivers in proportion to subsurface_runoff and using subsurface_runoff concentrations
        if runoff_remaining['volume'] > constants.FLOAT_ACCURACY:
            print('runoff to river remaining')
            #Calculate proportion
            proportions = {sname : value['volume'] / self.total_subsurface_runoff['volume'] for sname, value in temp_tracking['subsurface_runoff'].items()}
            self.redistribute_to_surfaces(proportions, temp_tracking['subsurface_runoff'], runoff_remaining['volume'])
        
        
        
        
    def redistribute_to_surfaces(self, proportions, concentrations, amount):
        for sname, surface in self.surfaces.items():
            #Calculate amount and concentration
            to_send = amount * proportions[sname]
            to_send = self.v_change_vqip(concentrations[sname], to_send)

            #Update tank
            _ = surface.push_storage(to_send, force = True)

    def push_set_flood(self, vqip):
        #Update flooded volume
        return self.surfaces['impervious'].push_storage(vqip, force=True)
    
    def push_set_garden(self, vqip):
        #Respond to a demand node filling excess garden demand
        return self.surfaces['garden'].push_storage(vqip, force = True)
    
    def push_check_garden(self, vqip = None):
        #Respond to a garden checking excess before sending water
        excess = self.surfaces['garden'].get_excess()
        if vqip is not None:
            excess['volume'] = min(excess['volume'], vqip['volume'])
        return excess
    
    def reinit(self):
        for surface in self.surfaces.values():
            surface.end_timestep()
            surface.reinit()

    def end_timestep(self):
        self.total_evaporation = 0
        self.total_precipitation = self.empty_vqip()
        self.total_infiltration = self.empty_vqip()
        self.total_percolation = self.empty_vqip()
        self.total_subsurface_runoff = self.empty_vqip()
        self.total_surface_runoff = self.empty_vqip()
        
        for surface in self.surfaces.values():
            surface.end_timestep()
        self.subsurface_flow.end_timestep()
        
class Surface(Tank):
    def __init__(self, **kwargs):
        self.area = 0
        self.capacity = 0
        self.datum = 10
        self.quick_slow_split = 0.5 #Higher number increases quick flow, lower number increases slow flow
        self.infiltration_t = 50 #mm
        self.wilting_point = 100 #mm
        self.crop_coeffient = 1
        self.decays = {}
        super().__init__(**kwargs)
        
        #Convert wilting point to amount that storage must be exceeded to generate quick/fast flow
        self.wilting_point *= (self.area * constants.MM_TO_M)
        
        #Give deposition pollutant dict negligible volume
        self.pollutant_dict = self.total_to_concentration(self.v_change_vqip(self.pollutant_dict, self.unavailable_to_evap/10))
    
    def get_deposition(self):
        return self.pollutant_dict
    
    
    def apply_precipitation_infiltration_evaporation(self):
        #Apply pollutants
        _ = self.push_storage(self.get_deposition(), force = True)
        
        #Read data
        precipitation_mm = self.parent.data_input_dict[('precipitation', self.parent.t)]
        
        #Apply evaporation
        evaporation_t = self.parent.data_input_dict[('et0', self.parent.t)]*self.crop_coefficient
        evaporation_mm = min(evaporation_t, precipitation_mm)
        precipitation_mm -= evaporation_mm
                
        #Apply infiltration
        excess_mm = max(precipitation_mm - self.infiltration_t, 0)
        precipitation_mm -= excess_mm
        
        #If evaporation is less than evaporation_t, then no water is entering tank, no excess
        if evaporation_mm < evaporation_t:
            #Take water from tank
            evap_from_tank = (evaporation_t - evaporation_mm) * self.area * constants.MM_M2_TO_M3
            evap_from_tank = self.evaporate(evap_from_tank)
            
            #Combine to calculate total evaporation
            evaporation = evap_from_tank + evaporation_mm * self.area * constants.MM_M2_TO_M3
            
            #No water entering tank
            infiltration = self.empty_vqip()
            
            #No excess
            excess = self.empty_vqip()
            
            
            
        else:
            #Calculate evaporation
            evaporation = evaporation_mm * self.area * constants.MM_M2_TO_M3
            
            #Calculate infiltration
            infiltration = precipitation_mm * self.area * constants.MM_M2_TO_M3
            infiltration = self.v_change_vqip(self.empty_vqip(), infiltration)
            
            #Update tank
            _ = self.push_storage(infiltration, force = True)
            
            #Calculate excess
            excess = excess_mm * self.area * constants.MM_M2_TO_M3
            excess = self.v_change_vqip(self.empty_vqip(), excess)
            
        #evaporation_mm is the portion of water that enters the model and is then evaporated, so it generates no pollution
        evaporation_from_precipitation = evaporation_mm * self.area * constants.MM_M2_TO_M3
        water_entering_model = self.v_change_vqip(self.empty_vqip(), evaporation_from_precipitation)
        
        #Infiltration and excess are the portions of water that enter the model and generate pollution
        water_entering_model = self.blend_vqip(water_entering_model, infiltration)
        water_entering_model = self.blend_vqip(water_entering_model, excess)
        
        return excess, infiltration, evaporation, water_entering_model
    
    def pull_outflows(self):
        #Amount of water above wilting point
        u = max(self.storage['volume'] - self.wilting_point, 0)
        
        #Convert to an amount
        subsurface_runoff = u * self.quick_slow_split
        percolation = u * (1 - self.quick_slow_split)
        
        #Update tank
        percolation = self.pull_storage({'volume' : percolation})
        subsurface_runoff = self.pull_storage({'volume' : subsurface_runoff})
        return percolation, subsurface_runoff
