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
    def __init__(**kwargs):
        
        super().__init__(**kwargs)

        #Update handlers
        self.push_set_handler['Sewer'] = self.push_set_flood

        #Initiliase values
        self.total_evaporation = self.empty_vqip()
        self.total_runoff = self.empty_vqip()
        self.total_infiltration = self.empty_vqip()
        self.total_percolation = self.empty_vqip()
        self.total_surface_runoff = self.empty_vqip()

        #Mass balance
        for surface in self.surfaces.values():
            self.mass_balance_ds.append(surface.ds)
        self.mass_balance_in.append(lambda : self.total_runoff)
        self.mass_balance_out.append(lambda : self.total_evaporation)

    def create_runoff(self):
        #Temporary variable to keep track of everything
        temp_tracking = {'runoff' : {},
                                     'evaporation' : {},
                                     'infiltration' : {},
                                     'percolation' : {},
                                     'surface_runoff' : {}}
        
        #Update surfaces
        for surface in self.surfaces.values()
            #Make rain
            runoff = surface.apply_precipitation()
            temp_tracking['runoff'][surface] = runoff

            #Get evaporation
            evaporation = surface.pull_evaporation()
            temp_tracking['evaporation'][surface] = evaporation

            #Get infiltration
            infiltration = surface.pull_infiltration()
            temp_tracking['infiltration'][surface] = infiltration

            #Get percolation
            percolation = surface.pull_percolation()
            temp_tracking['percolation'][surface] = percolation

            #Get runoff
            surface_runoff = surface.pull_ponded()
            temp_tracking['surface_runoff'][surface] = surface_runoff
            
            #Update totals
            self.total_infiltration = self.blend_vqip(self.total_infiltration, infiltration)
            self.total_evaporation = self.blend_vqip(self.total_evaporation, evaporation)
            self.total_runoff = self.blend_vqip(self.total_runoff, runoff)
            self.total_percolation = self.blend_vqip(self.total_percolation, percolation)

            #Drain sewers 
            if surface == 'impervious':
                reply = self.push_distributed(surface_runoff, of_type = ['Sewer'])
                _ = surface.tank.push_storage(reply, force = True)
            else:
                self.total_surface_runoff = self.blend_vqip(self.total_surface_runoff, surface_runoff)

        infiltration_remaining = self.push_distributed(self.total_infiltration, of_type = ['Groundwater'])
        
        amount_entering_rivers = self.blend_vqip(self.total_surface_runoff, self.total_percolation)

        runoff_remaining = self.push_distributed(amount_entering_rivers, of_type = ['Node', 'River']) #TODO seems suspicious.. do I need 'not of type'?

        #Redistribute unsent infiltration
        if infiltration_remaining['volume'] > 0:
            #Calculate proportion
            proportions = {sname : value['volume'] / self.total_infiltration['volume'] for sname, value in temp_tracking['infiltration'].items()}
            self.redistribute_to_surfaces(proportions, temp_tracking['infiltration'], infiltration_remaining['volume'])
            
        #Redistribute amount_entering rivers in proportion to percolation and using percolation concentrations
        if runoff_remaining['volume'] > 0:
            #Calculate proportion
            proportions = {sname : value['volume'] / self.total_percolation['volume'] for sname, value in temp_tracking['percolation'].items()}
            self.redistribute_to_surfaces(proportions, temp_tracking['percolation'], runoff_remaining['volume'])

    def redistribute_to_surfaces(proportions, concentrations, amount):
        for sname, surface in self.surfaces.items():
            #Calculate amount and concentration
            to_send = amount * proportions[sname]['volume']
            to_send = self.v_change_vqip(concentrations[sname], to_send)

            #Update tank
            _ = surface.push_storage(to_send, force = True)

    def end_timestep(self):
        self.total_evaporation = self.empty_vqip()
        self.total_runoff = self.empty_vqip()
        self.total_infiltration = self.empty_vqip()
        self.total_percolation = self.empty_vqip()
        self.total_surface_runoff = self.empty_vqip()

        for surface in self.surfaces.values():
            surface.end_timestep()

class Surface(Tank):
    def __init__(**kwargs):
        self.area = 0
        self.capacity = 0
        self.datum = 10
        self.percolation_coefficient = 0.0001
        self.evaporation_t = 1 #mm
        self.infiltration_t = 1 #mm

        self.pollutant_dict = self.empty_vqip()

        super().__init__(**kwargs)

    def apply_precipitation(self):
        #Read data
        precipitation_mm = self.data_input_dict[(self.name, 'precipitation', self.t)]

        #Convert to recharge
        runoff = self.surface.area * precipitation_mm * constants.MM_M2_TO_M3

        #Apply pollutants
        runoff = self.v_change_vqip(self.pollutant_dict, runoff)

        #Update tank
        _ = self.push_storage(runoff, force = True)

        return runoff
    
    def pull_evaporation(self):
        #Get evaporation (TODO maybe read data here... or something smart)
        evaporation_mm = self.evaporation_t

        #Convert to an amount
        evaporation = self.surface.area * evaporation_mm * constants.MM_M2_TO_M3

        #Update tank
        evaporation = self.evaporate(evaporation)

        return evaporation
    
    def pull_infiltration(self):
       #Get infiltration (TODO maybe read data here... or something smart)
        infiltration_mm = self.infiltration_t

        #Convert to an amount
        infiltration = self.surface.area * infiltration_mm * constants.MM_M2_TO_M3

        #Update tank
        infiltration = self.pull_storage(infiltration)

        return infiltration

    def pull_percolation(self):
        #Get percolation
        percolation = self.storage['volume'] * self.percolation_coefficient

        #Update tank
        percolation = self.pull_storage(percolation)

        return percolation

    def push_set_flood(self, vqip):
        #Update flooded volume
        return self.surfaces['impervious'].push_storage(vqip, force=True)