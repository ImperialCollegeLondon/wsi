# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 08:43:32 2021

@author: Barney

Converted to totals on Thur Apr 21 2022

"""

from wsimod.core import constants, WSIObj, DecayObj
from wsimod.nodes import nodes

class Arc(WSIObj):
    def __init__(self,**kwargs):
        #Default essential parameters
        self.name = None
        self.in_port = None
        self.out_port = None
        self.capacity = constants.UNBOUNDED_CAPACITY
        self.preference = 1
        
        #Update args
        super().__init__(**kwargs)
        
        if self.name in dir(nodes):
            print('Warning: arc name should not take a node class name')
        
        #Initialise states
        self.flow_in = 0
        self.flow_out = 0
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        
        #Update ports
        self.in_port.out_arcs[self.name] = self
        self.out_port.in_arcs[self.name] = self
        
        out_type = self.out_port.__class__.__name__
        in_type = self.in_port.__class__.__name__
        
        
        if hasattr(self.in_port, "out_arcs_type"):
            self.in_port.out_arcs_type[out_type][self.name] = self
   
        if hasattr(self.out_port, "in_arcs_type"):
            self.out_port.in_arcs_type[in_type][self.name] = self
        
        #Mass balance checking
        self.mass_balance_in = [lambda : self.vqip_in]
        self.mass_balance_out = [lambda : self.vqip_out]
        self.mass_balance_ds = [lambda : self.empty_vqip()]

    def arc_mass_balance(self):
        '''
        Checks mass balance for inflows/outflows/storage change in an arc

        Returns
        -------
        Note: pollutants in return vqips are take absolute values, 
              not concentrations
        
        in_ (vqip) Total vqip of vqip_in and other inputs
        out_ (vqip): Total vqip of vqip_out and other outputs
        ds_ (vqip): Total vqip of change in arc
        
        Example
        -------
        arc_in, arc_out, arc_ds = my_arc.arc_mass_balance()
        
        Raises
        ------
        Message if mass balance does not close to constants.FLOAT_ACCURACY
        '''
        
        in_, ds_, out_ = self.mass_balance()
        return in_, ds_, out_
    
    def send_push_request(self, vqip, tag = 'default', force = False):
        #TODO force doesn't appear to do anything here
        vqip = self.copy_vqip(vqip)
        
        
        #Apply pipe capacity
        if force:
            not_pushed = self.empty_vqip()
        else:
            excess_in = self.get_excess(direction = 'push', vqip = vqip, tag = tag)
            not_pushed = self.v_change_vqip(vqip, 
                                            max(vqip['volume'] - excess_in['volume'], 0))
        
        
        #Don't attempt to send volume that exceeds capacity
        vqip = self.extract_vqip(vqip, not_pushed)
        
        #Set push
        reply = self.out_port.push_set(vqip, tag)
        
        #Update total amount successfully sent
        vqip = self.extract_vqip(vqip, reply)
        
        #Combine non-sent water
        reply = self.sum_vqip(reply, not_pushed)
        
        #Update mass balance
        self.flow_in += vqip['volume']
        self.flow_out = self.flow_in
        
        self.vqip_in = self.sum_vqip(self.vqip_in, vqip)
        self.vqip_out = self.vqip_in
        
        return reply
    
    def send_pull_request(self, vqip, tag = 'default'):
        volume = vqip['volume']
        #Apply pipe capacity
        excess_in = self.get_excess(direction = 'pull', vqip = vqip)['volume']
        not_pulled = max(volume - excess_in, 0)
        volume -= not_pulled
        
        for pol in constants.ADDITIVE_POLLUTANTS:
            if pol in vqip.keys():
                vqip[pol] *= volume / vqip['volume']
            
        vqip['volume'] = volume
        
        #Make pull
        vqip = self.in_port.pull_set(vqip)
        
        #Update mass balance
        self.flow_in += vqip['volume']
        self.flow_out = self.flow_in
        
        self.vqip_in = self.sum_vqip(self.vqip_in, vqip)
        self.vqip_out = self.vqip_in
        
        return vqip
    
    def send_push_check(self, vqip = None, tag = 'default'):
        return self.get_excess(direction = 'push', vqip = vqip, tag = tag)

    
    def send_pull_check(self, vqip = None, tag = 'default'):
        return self.get_excess(direction = 'pull', vqip = vqip, tag = tag)
    
    def get_excess(self, direction, vqip = None, tag = 'default'):
        #Get excess in direction (push/pull)
        
        #Pipe capacity
        pipe_excess = self.capacity - self.flow_in
        
        #Node capacity
        if direction == 'push':
            node_excess = self.out_port.push_check(vqip, tag)
        elif direction == 'pull':
            node_excess = self.in_port.pull_check(vqip, tag)
        excess = min(pipe_excess, node_excess['volume'])

        #TODO : returning this as a vqip seems dodgy.. at least for pushes
        return self.v_change_vqip(node_excess, excess)
    
    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0

    def reinit(self):
        self.end_timestep()

class QueueArc(Arc):
    def __init__(self, **kwargs):
        self.number_of_timesteps = 0
        self.queue = []
        super().__init__(**kwargs)
        
        self.queue_storage = self.empty_vqip()
        self.queue_storage_ = self.empty_vqip()
        
        self.mass_balance_ds.append(lambda : self.queue_arc_ds())
        
    def queue_arc_ds(self):
        self.queue_storage = self.queue_arc_sum()
        return self.extract_vqip(self.queue_storage, self.queue_storage_)
        
    def queue_arc_sum(self):
        queue_storage = self.empty_vqip()
        for request in self.queue:
            queue_storage = self.sum_vqip(queue_storage, request['vqip'])
        return queue_storage
    
    def send_pull_request(self, vqip, tag = 'default', time = 0):
        volume = vqip['volume']
        #Apply pipe capacity
        excess_in = self.get_excess(direction = 'pull', vqip = vqip)['volume']
        not_pulled = max(volume - excess_in, 0)
        volume -= not_pulled
        vqip = self.v_change_vqip(vqip,volume)
        
        #Make pull
        vqip = self.in_port.pull_set(vqip)
        
        #Update to queue request
        request = {'time' : time + self.number_of_timesteps,
                   'vqip' : vqip}
        
        #vqtip enters arc as a request
        self.enter_queue(request, direction = 'pull')
        
        #Update request queue and return pulls from queue
        reply = self.update_queue(direction = 'pull')
        return reply
        
    def send_push_request(self, vqip_, tag = 'default', force = False, time = 0):
        #TODO force doesn't appear to do anything here
        vqip = self.copy_vqip(vqip_)
        
        if vqip['volume'] < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        
        #Apply pipe capacity
        if force:
            not_pushed = self.empty_vqip()
        else:
            excess_in = self.get_excess(direction = 'push', vqip = vqip, tag = tag)
            not_pushed = self.v_change_vqip(vqip, 
                                            max(vqip['volume'] - excess_in['volume'], 0))
        
        
        vqip = self.extract_vqip(vqip, not_pushed)
        
        #Update to queue request
        request = {'time' : time + self.number_of_timesteps,
                   'vqip' : vqip}
        
        #vqtip enters arc as a request
        self.enter_queue(request, direction = 'push', tag = tag)
        
        #Update request queue
        backflow = self.update_queue(direction = 'push')
        not_pushed = self.sum_vqip(not_pushed, backflow)
        
        if backflow['volume'] > vqip_['volume']:
            print('more backflow than vqip...')
        
        self.vqip_in = self.extract_vqip(self.vqip_in, backflow)
        
        return not_pushed
    
    def enter_arc(self, request, direction, tag):
        request['average_flow'] =  request['vqip']['volume'] / (request['time'] + 1)
        request['direction'] = direction
        request['tag'] = tag

        self.flow_in += request['average_flow']
        self.vqip_in = self.sum_vqip(self.vqip_in, request['vqip'])
        
        return request
        
    def enter_queue(self, request, direction = None, tag = 'default'):
        #Update inflows and format request
        request = self.enter_arc(request, direction, tag)

        #Enter queue
        self.queue.append(request)
        
    def update_queue(self, direction = None):
        done_requests = []
        
        total_removed = self.empty_vqip()
        total_backflow = self.empty_vqip()
        #Iterate over requests
        for request in self.queue:
            if request['direction'] == direction:
                vqip = request['vqip']
                
                if vqip['volume'] < constants.FLOAT_ACCURACY:
                    #Add to queue for removal
                    done_requests.append(request)
                elif request['time'] == 0:
                    
                    if direction == 'push':
                        #Attempt to push request
                        reply = self.out_port.push_set(vqip, request['tag'])
                        removed = vqip['volume'] - reply['volume']
                        
                    elif direction == 'pull':
                        #Water has already been pulled, so assume all received
                        removed = vqip['volume']
                    
                    else:
                        print('No direction')
                        
                    #Update outflows
                    self.flow_out += (request['average_flow'] * removed / vqip['volume'])
                    vqip_ = self.v_change_vqip(vqip, removed)
                    total_removed = self.sum_vqip(total_removed, vqip_)

                    #Assume that any water that cannot arrive at destination this timestep is backflow
                    rejected = self.v_change_vqip(vqip, vqip['volume'] - removed)
                    total_backflow = self.sum_vqip(rejected, total_backflow)
                    
                    done_requests.append(request)
                
                    
                    
        self.vqip_out = self.sum_vqip(self.vqip_out, total_removed)                    
        
        #Remove done requests
        for request in done_requests:
            self.queue.remove(request)
            
        # return total_removed
        if direction == 'pull':
            return total_removed
        elif direction == 'push':
            return total_backflow
        else:
            print('No direction')
            
    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        
        self.queue_storage_ = self.copy_vqip(self.queue_storage)
        self.queue_storage = self.empty_vqip()
        
        for request in self.queue:
            request['time'] = max(request['time'] - 1, 0)

    def reinit(self):
        self.end_timestep()
        self.queue = []
        
class AltQueueArc(QueueArc):
    def __init__(self, **kwargs):
        self.queue_arc_sum = self.alt_queue_arc_sum
                
        super().__init__(**kwargs)
        self.queue = {0 : self.empty_vqip(), 1 : self.empty_vqip()}
        self.max_travel = 1
        
        
        
    def alt_queue_arc_sum(self):
        queue_storage = self.empty_vqip()
        for request in self.queue.values():
            queue_storage = self.sum_vqip(queue_storage, request)
        return queue_storage
    
    def enter_queue(self, request, direction = None, tag = 'default'):
        #NOTE- has no tags
        
        #Update inflows and format request
        request = self.enter_arc(request, direction, tag)
        
        #Sum into queue
        if request['time'] in self.queue.keys():
            self.queue[request['time']]  = self.sum_vqip(self.queue[request['time']], request['vqip'])
        else:
            self.queue[request['time']] = request['vqip']
            self.max_travel = max(self.max_travel, request['time'])
        

        
    def update_queue(self, direction = None):
        #NOTE - has no direction
   
        total_removed = self.copy_vqip(self.queue[0])
        
        #Push 0 travel time water
        backflow = self.out_port.push_set(self.queue[0])
        self.queue[0] = self.v_change_vqip(self.queue[0], backflow['volume'])
        total_removed = self.v_change_vqip(total_removed, total_removed['volume'] - backflow['volume'])

        self.flow_out += total_removed['volume']
        self.vqip_out = self.sum_vqip(self.vqip_out, total_removed)
        
        return backflow

    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        self.queue_storage_ = self.copy_vqip(self.queue_storage)
        self.queue_storage = self.empty_vqip()

        queue_ = self.queue.copy()
        keys = self.queue.keys()
        for i in range(self.max_travel):
            if (i + 1) in keys:
                self.queue[i] = queue_[i+1]
                self.queue[i+1] = self.empty_vqip()

        self.queue[0] = self.sum_vqip(queue_[0], queue_[1])
        
    def reinit(self):
        self.end_timestep()
        self.queue = {0 : self.empty_vqip(), 1 : self.empty_vqip()}

class DecayArc(QueueArc, DecayObj):
    def __init__(self, **kwargs):
        self.decays = {}
        
        super().__init__(**kwargs)

        self.mass_balance_out.append(lambda : self.total_decayed)
        
    def enter_queue(self, request, direction = None, tag = 'default'):
        #Update inflows and format
        request = self.enter_arc(request, direction, tag)
        
        #Decay on entry
        request['vqip'] = self.make_decay(request['vqip'])
        
        #Append to queue
        self.queue.append(request)
        
        

    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.total_decayed = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        
        self.queue_storage_ = self.copy_vqip(self.queue_storage)
        self.queue_storage = self.empty_vqip()
        
        
        for request in self.queue:
            request['vqip'] = self.make_decay(request['vqip'])
            request['time'] = max(request['time'] - 1, 0)


class DecayArcAlt(AltQueueArc, DecayObj):
    def __init__(self, **kwargs):
        self.decays = {}
        
        super().__init__(**kwargs)
        self.end_timestep = self._end_timestep

        self.mass_balance_out.append(lambda : self.total_decayed)
        
    def enter_queue(self, request, direction = None, tag = 'default'):
        #TODO- has no tags
        
        #Update inflows and format
        request = self.enter_arc(request, direction, tag)
        
        #Decay on entry
        request['vqip'] = self.make_decay(request['vqip'])
        
        #Sum into queue
        if request['time'] in self.queue.keys():
            self.queue[request['time']]  = self.sum_vqip(self.queue[request['time']], request['vqip'])
        else:
            self.queue[request['time']]  = request['vqip']
            self.max_travel = max(self.max_travel, request['time'])
        
        
        

    def _end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.total_decayed = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        
        self.queue_storage_ = self.copy_vqip(self.queue_storage)
        self.queue_storage = self.empty_vqip()

        queue_ = self.queue.copy()
        keys = self.queue.keys()
        for i in range(self.max_travel):
            if (i + 1) in keys:
                self.queue[i] = self.make_decay(queue_[i+1])
                self.queue[i+1] = self.empty_vqip()

        self.queue[0] = self.sum_vqip(queue_[0], queue_[1])
    
class SewerArc(Arc):
    pass

class WeirArc(SewerArc):
    pass

