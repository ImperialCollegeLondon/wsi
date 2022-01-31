# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node
from wsimod.core import constants

class Demand(Node):
    def __init__(self, **kwargs):
        #Default parameters
        self.gardening_efficiency = 0.6 * 0.7 #Watering efficiency by Crop factor

        #Update args
        super().__init__(**kwargs)
        
        #Update handlers
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_check_deny
        self.pull_set_handler['default'] = self.pull_set_deny
        self.pull_check_handler['default'] = self.pull_check_deny
        
        #Initialise states
        self.total_demand = self.empty_vqip()
        self.total_backup = self.empty_vqip() #ew
        self.total_received = self.empty_vqip()
        
        #Mass balance
        # Because we assume demand is always satisfied
        # received water 'disappears' for mass balance
        # and consumed water 'appears'
        self.mass_balance_in.append(lambda : self.total_demand)
        self.mass_balance_out.append(lambda : self.total_backup)
        self.mass_balance_out.append(lambda : self.total_received) 
        
    def create_demand(self):
        demand = self.get_demand()
        total_requested = 0
        for dem in demand.values():
            total_requested += dem['volume']
            
        self.total_received = self.pull_distributed({'volume' : total_requested})
        #TODO Currently just assume all water is received and then pushed onwards
        
        directions = {'garden' : {'tag' : ('Demand',
                                           'Garden'),
                                  'of_type' : 'Land'},
                      'house' : {'tag' : 'Demand',
                                 'of_type' : 'Sewer'}}
        
        
        #Send water where it needs to go
        for key, item in demand.items():
            remaining = self.push_distributed(item,
                                              of_type = directions[key]['of_type'],
                                              tag = directions[key]['tag']
                                              )
            
            if remaining['volume'] > constants.FLOAT_ACCURACY:
                print('Demand not able to push')
                self.total_backup = self.blend_vqip(self.total_backup, remaining)
                
        #Update for mass balance
        for dem in demand.values():
            self.total_demand = self.blend_vqip(self.total_demand, 
                                                dem)
                
    def get_constant_demand(self):
        #TODO read/gen demand
        return self.empty_vqip()
    
    def end_timestep(self):
        self.total_demand = self.empty_vqip()
        self.total_backup = self.empty_vqip()
        
class NonResidentialDemand(Demand): 
        
    def get_demand(self):
        return self.get_constant_demand()             

class ResidentialDemand(Demand):
    
    def get_demand(self):
        water_output = {}        
                
        water_output['garden'] = self.get_garden_demand()        
        water_output['house'] = self.get_house_demand()      
        
        return water_output

    
    def get_garden_demand(self):
        """
        Calculate garden water demand in the current timestep by get_connected
        to all attached land nodes. The preference along the arc between a 
        demand and land node should be the percentage of garden area in a 
        given land node that consists of gardens in 'self' demand node.
        
        Returns
        -------
        vqip : Blended vqip of garden water use (including pollutants) to be 
            pushed to land
            
        Example
        -------
        garden_water_use = self.get_garden_demand()
        """
        excess = self.get_connected(direction = 'push',
                                    of_type = 'Land', 
                                    tag = ('Demand', 
                                           'Garden')
                                    )['priority']
        
        excess = self.excess_to_garden_demand(excess)
        vqip = self.apply_gardening_pollutants(excess)
        return vqip
    
    def apply_gardening_pollutants(self, excess):
        #TODO do
        vqip = self.empty_vqip()
        return self.v_change_vqip(vqip, excess)
        
        
    def excess_to_garden_demand(self, excess):
        #TODO Anything more than this needed?
        # (yes - population presence if included!)
        
        return excess * self.gardening_efficiency
    
    def get_house_demand(self):
        consumption = self.population * self.per_capita
        return self.v_change_vqip(self.pollutant_dict, consumption)