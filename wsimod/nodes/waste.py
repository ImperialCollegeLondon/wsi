# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node
from wsimod.core import constants

class Waste(Node):
    def __init__(self, **kwargs):
        #Update args
        super().__init__(**kwargs)
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_deny
        self.pull_check_handler['default'] = self.pull_check_deny
        self.push_set_handler['default'] = self.push_set_accept
        self.push_check_handler['default'] = self.push_check_accept
        
        #Mass balance
        self.mass_balance_out = [lambda : self.total_in()]
        
    def push_set_accept(self, vqip):
        #Returns all request accepted
        return self.empty_vqip()
    
    def push_check_accept(self, vqip = None):
        #Returns unbounded available push capacity
        if not vqip:
            vqip = self.empty_vqip()
            vqip['volume'] = constants.UNBOUNDED_CAPACITY
        return vqip