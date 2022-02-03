# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node, QueueTank
from wsimod.core import constants

class Sewer(Node):
    def __init__(self, **kwargs):
        #Default parameters
        self.node_storage = 0
        self.pipe_storage = 0
        self.pipe_time = 1 #Sewer to sewer travel time
        self.pipe_timearea = {0 : 1}
        self.chamber_area = 1
        self.chamber_floor = 10
        
        #Update args
        super().__init__(**kwargs)
        
        #Update handlers
        self.push_set_handler['Sewer'] = self.push_set_sewer
        self.push_set_handler['default'] = self.push_set_sewer
        self.push_set_handler['Land'] = self.push_set_land
        self.push_set_handler['Demand'] = self.push_set_land
        
        self.push_check_handler['default'] = self.push_check_sewer
        self.push_check_handler['Sewer'] = self.push_check_sewer
        self.push_check_handler['Demand'] = self.push_check_sewer
        self.push_check_handler['Land'] = self.push_check_sewer
        
        #Create sewer tank
        self.sewer_tank = QueueTank(capacity = self.node_storage + self.pipe_storage,
                                    number_of_timesteps = 0,
                                    datum = self.chamber_floor,
                                    area = self.chamber_area)
        
        #Mass balance
        self.mass_balance_ds.append(lambda : self.sewer_tank.ds())
    
    def push_check_sewer(self, vqip = None):
        excess = self.sewer_tank.get_excess()
        if vqip is None:
            return excess
        
        excess['volume'] = min(excess['volume'], vqip['volume'])
        return excess
        
    def push_set_sewer(self, vqip):
        #Sewer to sewer push, update queued tank
        return self.sewer_tank.push_storage(vqip, 
                                            time = self.pipe_time,
                                            force = True) # TODO Should this be forced?
    
    def push_set_land(self, vqip):
        #Land/demand to sewer push, update queued tank
        
        reply = self.empty_vqip()
        
        #Iterate over timearea diagram
        for time, normalised in self.pipe_timearea.items():
            vqip_ = self.v_change_vqip(vqip, 
                                       vqip['volume'] * normalised)
            reply_ = self.sewer_tank.push_storage(vqip_,
                                                  time = time,
                                                  force = True) # TODO Should this be forced?
            reply = self.blend_vqip(reply, reply_)
        
        return reply
    
    def make_discharge(self):
        _ = self.sewer_tank.internal_arc.update_queue(direction = 'push')
        
        #Discharge downstream
        remaining = self.push_distributed(self.sewer_tank.active_storage,
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
    
    def reinit(self):
        self.sewer_tank.reinit()

class EnfieldFoulSewer(Sewer):
    #TODO: combine with sewer
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__class__.__name__ = 'Sewer'
        
    def make_discharge(self):
        _ = self.sewer_tank.internal_arc.update_queue(direction = 'push')
        
        #Discharge downstream
        if self.sewer_tank.storage['volume'] > self.storm_exchange * self.sewer_tank.capacity:
            exchange_v = min((1 - self.storm_exchange) * self.sewer_tank.capacity, 
                             self.sewer_tank.active_storage['volume'])
            exchange = self.v_change_vqip(self.sewer_tank.active_storage, exchange_v)
            remaining = self.push_distributed(exchange)
            sent_to_exchange = self.v_change_vqip(self.sewer_tank.active_storage, exchange_v - remaining['volume'])
            sent_to_exchange_ = self.sewer_tank.pull_storage(sent_to_exchange)
            
            
        remaining = self.push_distributed(self.sewer_tank.active_storage,
                                        of_type = ['Waste'])

        #Update tank
        sent = self.sewer_tank.active_storage['volume'] - remaining['volume']
        sent = self.v_change_vqip(self.sewer_tank.active_storage,
                                  sent)
        reply = self.sewer_tank.pull_storage(sent)
        if (reply['volume'] - sent['volume']) > constants.FLOAT_ACCURACY:
            print('Miscalculated tank storage in discharge')