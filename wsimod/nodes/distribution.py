# -*- coding: utf-8 -*-
"""
Created on Sun Aug 14 16:27:14 2022

@author: bdobson
"""

from wsimod.nodes.nodes import Node
from wsimod.core import constants 
class Distribution(Node):
    def __init__(self,**kwargs):
        """A Node that cannot be pushed to. Intended to pass calls to FWTW - though this currently relies on the user to connect it properly

        Functions intended to call in orchestration:
            None
        
        Key assumptions:
            - No distribution processes yet represented, this class is just 
                for conveyance.
        
        Input data and parameter requirements:
            - None
        """
        super().__init__(**kwargs)
        #Update handlers        
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_check_deny

class UnlimitedDistribution(Distribution):
    def __init__(self,**kwargs):
        """A distribution node that provides unlimited water while tracking pass 
        balance

        Functions intended to call in orchestration:
            None
        
        Key assumptions:
            - Water demand is always satisfied.
        
        Input data and parameter requirements:
            - None
        """
        super().__init__(**kwargs)
        #Update handlers        
        self.pull_set_handler['default'] = self.pull_set_unlimited
        self.pull_check_handler['default'] = lambda x : self.v_change_vqip(self.empty_vqip(), constants.UNBOUNDED_CAPACITY)
        
        #States
        self.supplied = self.empty_vqip()
        
        self.mass_balance_in.append(lambda : self.supplied)
        
    def pull_set_unlimited(self, vqip):
        """Respond that VQIP was fulfilled and update state variables for mass balance

        Args:
            vqip (dict): A VQIP amount to request

        Returns:
            vqip (dict): A VQIP amount that was supplied
        """
        #TODO maybe need some pollutant concentrations?
        vqip = self.v_change_vqip(self.empty_vqip(), vqip['volume'])
        self.supplied = self.sum_vqip(self.supplied, vqip)
        return vqip
    
    def end_timestep(self):
        """Update state variables
        """
        self.supplied = self.empty_vqip()