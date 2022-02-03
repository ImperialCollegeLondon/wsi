# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node, Tank
from wsimod.core import constants

class Land(Node):
    
    def __init__(self, **kwargs):
        #Default parameters
        self.surface_timearea = {0 : 1}
        
        self.garden_storage = 0
        self.garden_area = 0
        self.garden_elevation = 10
        
        self.greenspace_storage = 0
        self.greenspace_area = 0
        self.greenspace_elevation = 10
        
        self.impervious_storage = 0
        self.impervious_area = 0
        self.impervious_elevation = 10
        
        #Vol. of water in a tank that is unavailable to evaporation. Must be >0
        #Otherwise, evaporation will remove pollutants if it drops a tank to 0.
        self.unavailable_to_evap = 0.01 
        
        self.tanks = {}
                
        #Update args
        super().__init__(**kwargs)
        
        #Update handlers
        self.push_set_handler['Sewer'] = self.push_set_flood
        self.push_set_handler[('Demand','Garden')] = self.push_set_garden
        self.push_check_handler[('Demand','Garden')] = self.push_check_garden
        self.pull_set_handler[('Demand','RWH')] = self.pull_set_rwh
        
        #Create tanks
        #TODO elegance
        if self.garden_storage > 0:
            self.tanks['garden'] = Tank(capacity = self.garden_storage,
                                        area = self.garden_area,
                                        datum = self.garden_elevation,
                                        unavailable_to_evap = self.unavailable_to_evap)
        
        if self.greenspace_storage > 0:
            self.tanks['greenspace'] = Tank(capacity = self.greenspace_storage,
                                            area = self.greenspace_area,
                                            datum = self.greenspace_elevation,
                                            unavailable_to_evap = self.unavailable_to_evap)
            
        if self.impervious_storage > 0:
            self.tanks['impervious'] = Tank(capacity = self.impervious_storage,
                                            area = self.impervious_area,
                                            datum = self.impervious_elevation,
                                            unavailable_to_evap = self.unavailable_to_evap)
        
        #Initiliase values
        self.total_evaporation = 0
        self.total_runoff = self.empty_vqip()
        
        #Mass balance
        for tank in self.tanks.values():
            self.mass_balance_ds.append(tank.ds)
        self.mass_balance_in.append(lambda : self.total_runoff)
        self.mass_balance_out.append(lambda : self.v_change_vqip(self.empty_vqip(),
                                                                 self.total_evaporation))
        
    def get_runoff(self, surface):
        #surface can be 'garden', 'impervious', 'greenspace'
        precipitation_mm = self.data_input_dict[(self.name, 'precipitation', self.t)]
        total_runoff = self.tanks[surface].area * precipitation_mm * constants.MM_M2_TO_M3
        return self.v_change_vqip(self.pollutant_dict, total_runoff)
    
    def get_evaporation(self, surface = None):
        #surface can be 'garden', 'impervious', 'greenspace'
        #TODO read/gen evap
        depth = 0 #mm
        return depth
    
    def get_infiltration(self, surface = None):
        #surface can be 'garden', 'impervious', 'greenspace'
        #TODO read/gen infiltraiton
        depth = 0 #mm
        return depth
    
    def create_runoff(self):
        #Creates runoff on various surfaces
        
        # 1. Apply rainfall to different surfaces
        # 2. Input pollutants
        # 3. Update tanks
        # 4. Infiltrate
        # 5. Push excess from impervious
                
        for surface, tank in self.tanks.items():
            
            #TODO issue occurs during impervious tank
            
            #Get runoff
            runoff = self.get_runoff(surface)
            self.total_runoff = self.blend_vqip(self.total_runoff, runoff)
            
            
            #Update tanks
            _ = tank.push_storage(runoff, force = True)
            
            #Apply infiltration
            infil = self.get_infiltration(surface)
            #TODO assumes m3 and mm
            infil = {'volume' : infil * tank.area * constants.MM_M2_TO_M3}
            infil = self.v_change_vqip(tank.storage, 
                                       min(tank.get_avail()['volume'],
                                           infil['volume'])
                                       ) #TODO This should probably be done in get_infiltration
            remaining = self.push_distributed(infil,
                                            of_type = ['Groundwater'])
            to_pull = self.v_change_vqip(tank.storage, 
                                         infil['volume'] - remaining['volume'])
            reply = tank.pull_storage(to_pull)
            
            if (reply['volume'] - to_pull['volume']) > constants.FLOAT_ACCURACY:
                print("Error in calculating available tank capacity or pulling from a tank")
                
            #Apply evaporation
            evap = self.get_evaporation(surface)
            evap = evap * tank.area * constants.MM_M2_TO_M3
            evap = tank.evaporate(evap)
            self.total_evaporation += evap
                
        #Drain impervious
        connected = self.get_connected(direction = 'push',
                                       of_type = 'Sewer')
        
        if connected['avail'] > 0:
            total_ponded = self.tanks['impervious'].pull_ponded()
            for key, arc in self.out_arcs_type['Sewer'].items():
                volume_to_arc = total_ponded['volume'] *\
                                connected['allocation'][key] /\
                                connected['priority']
                
                runoff_to_sewer = self.v_change_vqip(total_ponded, 
                                                     volume_to_arc)
                
                leftover = self.empty_vqip()
                for time, normalised in self.surface_timearea.items():
                    runoff_to_sewer_ = self.v_change_vqip(runoff_to_sewer, 
                                                          runoff_to_sewer['volume'] * normalised)
                    runoff_to_sewer_['time'] = time
                    reply = arc.send_push_request(runoff_to_sewer_, tag = 'Land')
                    leftover = self.blend_vqip(leftover, reply)
                
                _ = self.tanks['impervious'].push_storage(leftover, force = True)
        

    
    def push_set_flood(self, vqip):
        #Update flooded volume
        return self.tanks['impervious'].push_storage(vqip, force=True)
    
    def push_set_garden(self, vqip):
        #Respond to a demand node filling excess garden demand
        return self.tanks['garden'].push_storage(vqip, force = True)
    
    def push_check_garden(self, vqip = None):
        #Respond to a garden checking excess before sending water
        excess = self.tanks['garden'].get_excess()
        if vqip is not None:
            excess['volume'] = min(excess['volume'], vqip['volume'])
        return excess
        
    
    def pull_set_rwh(self, vqip):
        #Respond to a pull from demand for RWH
        pass
    
    def end_timestep(self):
        self.total_evaporation = 0
        self.total_runoff = self.empty_vqip()
        
        for tank in self.tanks.values():
            tank.end_timestep()
            
    def reinit(self):
        for tank in self.tanks.values():
            tank.end_timestep()
            tank.reinit()

class Land_(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.__class__.__name__ = 'Land'
        
        surfaces = self.surfaces.copy()
        self.surfaces = {}
        for sname, surface in surfaces.items():
            self.surfaces[sname] = Surface(**surface)
            self.surfaces[sname].parent = self

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

        #Mass balance
        for surface in self.surfaces.values():
            self.mass_balance_ds.append(surface.ds)
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
            
            #Get percolation
            percolation = surface.pull_percolation()
            temp_tracking['percolation'][sname] = percolation

            #Get subsurface_runoff
            subsurface_runoff = surface.pull_subsurface_runoff()
            temp_tracking['subsurface_runoff'][sname] = subsurface_runoff

            #Get runoff
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

        percolation_remaining = self.push_distributed(self.total_percolation, of_type = ['Groundwater'])
        
        amount_entering_rivers = self.blend_vqip(self.total_surface_runoff, self.total_subsurface_runoff)

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

class Surface(Tank):
    def __init__(self, **kwargs):
        self.area = 0
        self.capacity = 0
        self.datum = 10
        self.subsurface_runoff_coefficient = 0.001
        self.percolation_coefficient = 0.001
        self.evaporation_t = 1 #mm
        self.infiltration_t = 1 #mm

        super().__init__(**kwargs)
        
        # self.pollutant_dict = self.empty_vqip()

    def apply_precipitation_infiltration_evaporation(self):
        #Read data
        precipitation_mm = self.parent.data_input_dict[('precipitation', self.parent.t)]
        
        #Apply evaporation
        evaporation_mm = max(precipitation_mm - self.evaporation_t, 0)
        precipitation_mm -= evaporation_mm
                
        #Apply infiltration
        excess_mm = max(precipitation_mm - self.infiltration_t, 0)
        precipitation_mm -= excess_mm
        
        #If evaporation is less than evaporation_t, then no water is entering tank, no excess
        if evaporation_mm < self.evaporation_t:
            #Take water from tank
            evap_from_tank = (self.evaporation_t - evaporation_mm) * self.area * constants.MM_M2_TO_M3
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
            infiltration = self.v_change_vqip(self.pollutant_dict, infiltration)
            
            #Update tank
            _ = self.push_storage(infiltration, force = True)
            
            #Calculate excess
            excess = excess_mm * self.area * constants.MM_M2_TO_M3
            excess = self.v_change_vqip(self.pollutant_dict, excess)
            
        #evaporation_mm is the portion of water that enters the model and is then evaporated, so it generates no pollution
        evaporation_from_precipitation = evaporation_mm * self.area * constants.MM_M2_TO_M3
        water_entering_model = self.v_change_vqip(self.empty_vqip(), evaporation_from_precipitation)
        
        #Infiltration and excess are the portions of water that enter the model and generate pollution
        water_entering_model = self.blend_vqip(water_entering_model, infiltration)
        water_entering_model = self.blend_vqip(water_entering_model, excess)
        
        return excess, infiltration, evaporation, water_entering_model
    
    def pull_percolation(self):
        #Convert to an amount
        percolation = self.storage['volume'] * self.percolation_coefficient

        #Update tank
        percolation = self.pull_storage({'volume' : percolation})

        return percolation

    def pull_subsurface_runoff(self):
        #Get subsurface_runoff
        subsurface_runoff = self.storage['volume'] * self.subsurface_runoff_coefficient

        #Update tank
        subsurface_runoff = self.pull_storage({'volume' : subsurface_runoff})

        return subsurface_runoff
