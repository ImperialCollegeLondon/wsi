# -*- coding: utf-8 -*-
"""
Created on Sat Dec 31 09:49:39 2022

@author: leyan
"""

from wsimod.nodes.nodes import Node
from wsimod.core import constants

class Discharge_point(Node):
    def __init__(self,
                        name,
                        effluent_conc = {},
                        effluent_volume = 500,
                        **kwargs):
        """A tank that has a residence time property that limits storage 
        pulled from the 'pull_outflow' function

        Args:
            residence_time (float, optional): Residence time, in theory given 
                in timesteps, in practice it just means that storage / 
                residence time can be pulled each time pull_outflow is called. 
                Defaults to 2.
        """
        
        super().__init__(name, **kwargs)
        
        self.effluent = self.empty_vqip()
        self.effluent['volume'] = effluent_volume
        for pol in effluent_conc.keys():
            if pol in constants.ADDITIVE_POLLUTANTS:
                self.effluent[pol] = effluent_conc[pol] * effluent_volume
            elif pol in constants.NON_ADDITIVE_POLLUTANTS:
                self.effluent[pol] = effluent_conc[pol]
        
        self.mass_balance_in = [lambda : self.empty_vqip()]
        self.mass_balance_out = [lambda : self.empty_vqip()]
        self.mass_balance_ds = [lambda : self.empty_vqip()]    
        
    def make_discharge(self):
        
        _ = self.push_distributed(self.effluent)
        
        return self.empty_vqip()