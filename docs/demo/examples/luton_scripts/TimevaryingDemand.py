# -*- coding: utf-8 -*-
"""
Created on Sun Dec 24 10:09:12 2023

@author: leyan
"""

from wsimod.nodes.demand import Demand

class TimevaryingDemand(Demand):
    def __init__(self,
                        **kwargs):
        """Node that generates time-varying water demand specified by data input.

        Args:
            data_input_dict (dict, optional):  This must contains 'demand' along with the original 
            input vairables (e.g., 'temperature')
        
        Functions intended to call in orchestration:
            create_demand
        """
        #Update args
        
        super().__init__(**kwargs)
    
    def get_demand(self):
        """Holder function to enable constant demand generation

        Returns:
            (dict): A VQIP that will contain constant demand
        """
        #TODO read/gen demand
        self.constant_demand = self.get_data_input('demand')
        pol = self.v_change_vqip(self.empty_vqip(), self.constant_demand)
        for key, item in self.pollutant_load.items():
            pol[key] = item
        return {'default' : pol}