# -*- coding: utf-8 -*-
"""
Created on Sun Aug 14 16:27:14 2022

@author: bdobson
"""

from wsimod.nodes.nodes import Node
from wsimod.core import constants 
class Distribution(Node):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        #Update handlers        
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_check_deny

class UnlimitedDistribution(Distribution):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        #Update handlers        
        self.pull_set_handler['default'] = self.pull_set_unlimited
        self.pull_check_handler['default'] = lambda x : self.v_change_vqip(self.empty_vqip(), constants.UNBOUNDED_CAPACITY)
        
        #States
        self.supplied = self.empty_vqip()
        
        self.mass_balance_in.append(lambda : self.supplied)
        
    def pull_set_unlimited(self, vqip):
        vqip = self.v_change_vqip(self.empty_vqip(), vqip['volume'])
        self.supplied = self.sum_vqip(self.supplied, vqip)
        return vqip
    
    def end_timestep(self):
        self.supplied = self.empty_vqip()