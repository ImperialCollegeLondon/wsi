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