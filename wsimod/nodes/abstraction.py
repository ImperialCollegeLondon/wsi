# -*- coding: utf-8 -*-
"""
Created on Fri Nov 19 15:56:47 2021

@author: Barney
"""

from wsimod.nodes.nodes import Node

class Abstraction(Node):
    #A node that won't push up an abstraction when routing

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.push_set_handler = {'default' : self.push_distributed_abstraction}
    
    def push_distributed_abstraction(self, vqip, of_type = None, tag = 'default'):
        
        if not of_type:
            of_type = ['Node','Waste','Abstraction']
            
        return self.push_distributed(vqip, of_type, tag)
