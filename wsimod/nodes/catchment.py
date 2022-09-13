# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson

Converted to totals on 2022-05-03

"""
from wsimod.nodes.nodes import Node
from wsimod.core import constants

class Catchment(Node):
    def __init__(self, 
                        name,
                        data_input_dict = {},
                        ):
        """Node that reads input data to create VQIPs that are pushed downstream and 
        tracks abstractions made from the node, adjusting pushes accordingly.

        Args:
            name (str): Node name
            data_input_dict (dict, optional): Dictionary of data inputs relevant for 
                the node. Keys are tuples where first value is the name of the 
                variable to read from the dict and the second value is the time. 
                Defaults to {}.
        """
        
        #Update args
        super().__init__(name)
        self.data_input_dict = data_input_dict

        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_abstraction
        self.pull_check_handler['default'] = self.pull_check_abstraction
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_set_deny
        
        #Mass balance
        self.mass_balance_in.append(lambda : self.get_flow())
        
    def get_flow(self):
        """Read volume data (assumed in m3/s), convert to m3/dt, read pollutant data

        Returns:
            vqip (dict): Return read data as a VQIP
        """
        #TODO (if used) - note that if flow is < float accuracy then it won't 
        #get pushed, and the pollutants will 'disappear', causing a mass balance error
        vqip = {'volume' : self.data_input_dict[('flow',
                                               self.t)]}
        vqip['volume'] *= constants.M3_S_TO_M3_DT #preprocess to SI
        for pollutant in constants.POLLUTANTS:
            vqip[pollutant] = self.data_input_dict[(pollutant,
                                                   self.t)] * vqip['volume']
        return vqip
    
    def route(self):
        """Send any water that has not already been abstracted downstream
        """
        #Get amount of water
        avail = self.pull_avail()
        #Route excess flow onwards
        reply = self.push_distributed(avail)
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('Catchment unable to route')
    
    def pull_avail(self):
        """Water available for abstraction (Read data and subtract pre-existing 
        abstractions)

        Returns:
            avail (dict): A VQIP of water available for abstraction
        """

        #Get available vqip
        avail = self.get_flow()
        
        #Remove abstractions already made
        for name, arc in self.out_arcs.items():
            avail = self.v_change_vqip(avail, avail['volume'] - arc.vqip_in['volume'])
        
        return avail
    
    def pull_check_abstraction(self, vqip = None):
        """Check wrapper for pull_avail that updates response if VQIP is given

        Args:
            vqip (dict, optional): A VQIP that is compared with pull_avail and the 
                minimum is returned. Only the 'volume' key is used. Defaults to None.

        Returns:
            avail (dict): A VQIP of water available for abstraction
        """
        #Respond to abstraction check request
        avail = self.pull_avail()
        
        if vqip:
            avail = self.v_change_vqip(avail, 
                                       min(avail['volume'], vqip['volume']))
        
        return avail
    
    def pull_set_abstraction(self, vqip):
        """Request set wrapper for pull_avail where VQIP is specified

        Args:
            vqip (dict): A VQIP of water to pull. Only the 'volume' key is used.

        Returns:
            avail (dict): A VQIP of water abstracted
        """
        #Respond to abstraction set request
        avail = self.pull_avail()
        avail = self.v_change_vqip(avail, 
                                       min(avail['volume'], vqip['volume']))
        
        return avail