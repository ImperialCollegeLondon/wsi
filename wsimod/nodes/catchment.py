# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node
from wsimod.core import constants

class Catchment(Node):
    def __init__(self, **kwargs):
        #Update args
        super().__init__(**kwargs)
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_abstraction
        self.pull_check_handler['default'] = self.pull_check_abstraction
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_set_deny
        
        #Mass balance
        self.mass_balance_in.append(lambda : self.get_flow())
        
    def get_flow(self):
        vqip = {'volume' : self.data_input_dict[('flow',
                                               self.t)]}
        vqip['volume'] *= constants.M3_S_TO_M3_DT
        for pollutant in constants.POLLUTANTS:
            vqip[pollutant] = self.data_input_dict[(pollutant,
                                                   self.t)]
        return vqip
    
    def route(self):
        #Route excess flow onwards
        avail = self.pull_avail()
        reply = self.push_distributed(avail)
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('Catchment unable to route')
    
    def pull_avail(self):
        #Get available vqip
        avail = self.get_flow()
        
        for name, arc in self.out_arcs.items():
            avail['volume'] -= arc.vqip_in['volume']
        
        return avail
    
    def pull_check_abstraction(self, vqip = None):
        #Respond to abstraction check request
        avail = self.pull_avail()
        
        if vqip:
            avail['volume'] = min(avail['volume'], vqip['volume'])
        
        return avail
    
    def pull_set_abstraction(self, vqip):
        #Respond to abstraction set request
        avail = self.pull_avail()
        avail['volume'] = min(avail['volume'], vqip['volume'])
        
        return avail