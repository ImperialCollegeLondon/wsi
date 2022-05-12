# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
Converted to totals on 2022-05-03

"""
from wsimod.nodes.nodes import Node, Tank, QueueTank, DecayTank, DecayQueueTank
from wsimod.core import constants

class Storage(Node):
    #Basically a wrapper for a tank

    def __init__(self, **kwargs):
        self.initial_storage = 0
        self.storage = 0
        self.area = 0
        self.datum = 10
        self.decays = None
        self.travel_time = 0
        super().__init__(**kwargs)
        
        #Create tank
        if 'initial_storage' not in dir(self):
            self.initial_storage = self.empty_vqip()
        
        if self.decays is None:
            #TODO... renaming storage to capacity here is confusing
            self.tank = Tank(capacity = self.storage,
                                area = self.area,
                                datum = self.datum,
                                initial_storage = self.initial_storage,
                                )
        else:
            self.tank = DecayTank(capacity = self.storage,
                                area = self.area,
                                datum = self.datum,
                                initial_storage = self.initial_storage,
                                decays = self.decays,
                                parent = self,
                                )
        #Update handlers
        self.push_set_handler['default'] = self.push_set_storage
        self.pull_set_handler['default'] = lambda vol : self.tank.pull_storage(vol)
        self.push_check_handler['default'] = self.tank.get_excess
        self.pull_check_handler['default'] = self.tank.get_avail
        
        #Mass balance
        self.mass_balance_ds.append(lambda : self.tank.ds())
    
    def push_set_storage(self, vqip):

        #Update tank
        reply = self.tank.push_storage(vqip)
            
        return reply
    
    def distribute(self):
        #Distribute any active storage
        storage = self.tank.pull_storage(self.tank.get_avail())
        retained = self.push_distributed(storage)
        if retained['volume'] > constants.FLOAT_ACCURACY:
            print('Storage unable to push')
            
    
    def end_timestep(self):
        self.tank.end_timestep()
    
    def reinit(self):
        # TODO Automate this better
        self.tank.reinit()
        self.tank.storage['volume'] = self.initial_storage
        self.tank.storage_['volume'] = self.initial_storage 

class Groundwater(Storage):
    def __init__(self, **kwargs):
        self.residence_time = 200
        self.infiltration_threshold = 1 # %/100 of capacity that node must be exceeding to generate infiltration
        self.infiltration_pct = 0 # %/100 of storage above threshold that is SQRTed and infiltrated
        
        super().__init__(**kwargs)
        
    def distribute(self):
        avail = self.tank.get_avail()['volume'] / self.residence_time
        to_send = self.tank.pull_storage({'volume' : avail})
        retained = self.push_distributed(to_send)
        if retained['volume'] > constants.FLOAT_ACCURACY:
            print('Storage unable to push')
    
    def pull_active(self, volume):
        pass
    def infiltrate(self):
        avail = self.tank.get_avail()['volume']
        avail = max(avail - self.tank.capacity * self.tank.infiltration_threshold, 0)
        avail = (avail * self.infiltration_pct) ** 0.5
        
        to_send = self.pull_active({'volume' : avail})
        retained = self.push_distributed(to_send)
        if retained['volume'] > constants.FLOAT_ACCURACY:
            print('Storage unable to push')
    
class QueueGroundwater(Storage):
    #TODO - no infiltration as yet
    def __init__(self, **kwargs):
        self.timearea = {0 : 1}

        super().__init__(**kwargs)
        self.__class__.__name__ = 'Groundwater'
        self.push_set_handler['default'] = self.push_set_timearea
        self.pull_set_handler['default'] = self.pull_set_active
        self.pull_check_handler['default'] = self.pull_check_active
        if self.decays is None:
            #TODO... renaming storage to capacity here is confusing
            self.tank = QueueTank(capacity = self.storage,
                                             area = self.area,
                                             datum = self.datum,
                                             initial_storage = self.initial_storage,
                                             )
        else:
            self.tank = DecayQueueTank(capacity = self.storage,
                                             area = self.area,
                                             datum = self.datum,
                                             decays = self.decays,
                                             parent = self,
                                             initial_storage = self.initial_storage,
                                             )
    def push_set_timearea(self, vqip):
        reply = self.empty_vqip()
        #Iterate over timearea diagram
        for time, normalised in self.timearea.items():
            vqip_ = self.v_change_vqip(vqip, 
                                       vqip['volume'] * normalised)
            reply_ = self.tank.push_storage(vqip_,
                                            time = time,
                                            force = True) # TODO Should this be forced?
            reply = self.sum_vqip(reply, reply_)
        return reply
        
    def distribute(self):
        _ = self.tank.internal_arc.update_queue(direction = 'push')
        
        remaining = self.push_distributed(self.tank.active_storage)
        
        if remaining['volume'] > constants.FLOAT_ACCURACY:
            print('Groundwater couldnt push all')
        
        #Update tank
        sent = self.tank.active_storage['volume'] - remaining['volume']
        sent = self.v_change_vqip(self.tank.active_storage,
                                  sent)
        reply = self.tank.pull_storage(sent)
        if (reply['volume'] - sent['volume']) > constants.FLOAT_ACCURACY:
            print('Miscalculated tank storage in discharge')
    
    def pull_check_active(self,vqip = None):
        if vqip is None:
            return self.tank.storage
        else:
            reply = min(vqip['volume'], self.tank.storage['volume'])
            return self.v_change_vqip(self.tank.storage, reply)
        
    def pull_set_active(self, vqip):
        
        total_storage = self.tank.storage['volume']
        total_pull = min(self.tank.storage['volume'], vqip['volume'])
        
        if total_pull < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        else:
            pulled = self.empty_vqip()
            #Proportionally take from queue & active storage
            if isinstance(self.tank.internal_arc.queue, dict):
                for t, v in self.tank.internal_arc.queue.items():
                    
                    t_pulled = self.v_change_vqip(self.tank.internal_arc.queue[t], 
                                                  v['volume'] * total_pull / total_storage)
                    
                    self.tank.internal_arc.queue[t] = self.extract_vqip(self.tank.internal_arc.queue[t], t_pulled)
                    pulled = self.sum_vqip(pulled, t_pulled)
                a_pulled = self.v_change_vqip(self.tank.active_storage,
                                              self.tank.active_storage['volume'] * total_pull / total_storage)
                self.tank.active_storage = self.extract_vqip(self.tank.active_storage, a_pulled)
                pulled = self.sum_vqip(pulled, a_pulled)
                
                #Recalculate storage
                self.tank.storage = self.extract_vqip(self.tank.storage, pulled)
                return pulled
            # elif isinstance(self.tank.internal_arc.queue, list):
            #     for req in self.tank.internal_arc.queue:
            #         t_pulled = req['vqtip']['volume'] * total_pull / total_storage
            #         req['vqtip'] = self.v_change_vqip(req['vqtip'], req['vqtip']['volume'] - t_pulled)
            #         pulled += t_pulled
            #     a_pulled = self.tank.active_storage['volume'] * total_pull / total_storage
            #     self.tank.active_storage = self.v_change_vqip(self.tank.active_storage, self.tank.active_storage['volume'] - a_pulled)
            #     pulled += a_pulled
                
            #     #Recalculate storage - doing this differently causes numerical errors
            #     new_v = sum([x['vqtip']['volume'] for x in self.tank.internal_arc.queue])+ self.tank.active_storage['volume']
            #     self.tank.storage = self.v_change_vqip(self.tank.storage, new_v)
            
            
                # return self.v_change_vqip(self.tank.storage, pulled)
            
    
class Abstraction(Storage):
    """
    With a river - abstractions must be placed at abstraction points
    They must have accumulated all upstream flows that are available for abstraction before being abstracted from
    Once abstracted from, they can then distribute
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mrf = 0
        self.pull_set_handler['default'] = self.pull_set_abstraction
    
    def pull_set_abstraction(self, vqip):
        #Calculate MRF before reply TODO
        reply = self.tank.pull_storage(vqip['volume'])
        return reply

class Reservoir(Storage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def make_abstractions(self):
        reply = self.pull_distributed(self.tank.get_excess())
        spill = self.tank.push_storage(reply)
        if spill['volume'] > constants.FLOAT_ACCURACY:
            print('Spill at reservoir')

class RiverReservoir(Reservoir):
    def __init__(self, **kwargs):
        self.environmental_flow = 0
        self.total_environmental_satisfied = 0
        
        super().__init__(**kwargs)
        
        self.push_set_handler['default'] = self.push_set_river_reservoir
        self.push_check_handler['default'] = self.push_check_river_reservoir
        self.end_timestep = self.end_timestep_
        
        self.__class__.__name__ = 'Reservoir'
        
    def push_set_river_reservoir(self, vqip):
        #Apply normal reservoir storage
        spill = self.push_set_storage(vqip)
        
        #Send spill downstream
        reply = self.push_distributed(spill) #of_type = Node?
        
        self.total_environmental_satisfied += (spill['volume'] - reply['volume'])
        
        return reply
    
    def push_check_river_reservoir(self, vqip = None):
        downstream_availability = self.get_connected(direction = 'push')['avail']
        excess = self.tank.get_excess()
        
        new_v = excess['volume'] + downstream_availability
        if vqip is not None:
            new_v = min(vqip['volume'], new_v)
            
        excess = self.v_change_vqip(excess, new_v)
        
        return excess
        
    
    def satisfy_environmental(self):
        to_satisfy = max(self.environmental_flow - self.total_environmental_satisfied, 0)
        environmental = self.tank.pull_storage({'volume' : to_satisfy})
        reply = self.push_distributed(environmental)
        if reply['volume'] > 0:
            print('warning: environmental not able to push')
            
        self.total_environmental_satisfied += environmental['volume']
        
    def end_timestep_(self):
        self.tank.end_timestep()
        self.total_environmental_satisfied = 0