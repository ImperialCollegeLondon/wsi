# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node, QueueTank
from wsimod.core import constants

class Compartment(Node):
    def __init__(self, **kwargs):
        #Default parameters
        self.timearea = {0 : 1}
        self.tank_storage = 0
        self.outlet_time = 0
        self.tank_area = 1
        self.tank_floor = 10
        
        #Update args
        super().__init__(**kwargs)
        
        #Update handlers
        self.push_set_handler['default'] = self.push_set_timearea
    
        #Create sewer tank
        self.tank = QueueTank(capacity = self.tank_storage,
                                    number_of_timesteps = 0,
                                    datum = self.tank_floor,
                                    area = self.tank_area)
        
        #Mass balance
        self.mass_balance_ds.append(lambda : self.tank.ds())
    
    def push_set_timearea(self, vqip):
        #Land/demand to sewer push, update queued tank
        
        reply = self.empty_vqip()
        
        #Iterate over timearea diagram
        for time, normalised in self.timearea.items():
            vqip_ = self.v_change_vqip(vqip, 
                                       vqip['volume'] * normalised)
            reply_ = self.tank.push_storage(vqip_,
                                                  time = time,
                                                  force = True) # TODO Should this be forced?
            reply = self.blend_vqip(reply, reply_)
        
        return reply
    #THIS IS WELL UNFINISHED...
    def make_discharge(self):
        
        #Discharge downstream
        remaining = self.push_distributed(self.tank.active_storage,
                                        of_type = ['Sewer',
                                                   'WWTW'],
                                        tag = 'Sewer')
        #CSO discharge
        remaining = self.push_distributed(remaining,
                                          of_type = ['Node'])
        
        #Update tank
        sent = self.sewer_tank.active_storage['volume'] - remaining['volume']
        sent = self.v_change_vqip(self.sewer_tank.active_storage,
                                  sent)
        reply = self.sewer_tank.pull_storage(sent)
        if (reply['volume'] - sent['volume']) > constants.FLOAT_ACCURACY:
            print('Miscalculated tank storage in discharge')
            
        #Flood excess
        ponded = self.sewer_tank.pull_ponded()
        if ponded['volume'] > constants.FLOAT_ACCURACY:
            n_out_arcs = len(self.out_arcs_type['Land'])
            for key, arc in self.out_arcs_type['Land'].items():
                #This just pushes sequentially
                to_flood = self.v_change_vqip(ponded, 
                                              ponded['volume'] / n_out_arcs)
                reply_ = arc.send_push_request(to_flood,
                                                 direction = 'push',
                                                 tag = 'Sewer')
            
                if reply_['volume'] > constants.FLOAT_ACCURACY:
                    print('Land rejected a sewer push')
        
    def end_timestep(self):
        self.sewer_tank.end_timestep()