# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 08:43:32 2021

@author: Barney
"""

from wsimod.core import constants, WSIObj
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

        
    def send_push_request(self, vqip, tag = 'default', force = False):
        
        vqip = self.copy_vqip(vqip)
        
        if vqip['volume'] < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        
        #Apply pipe capacity
        if force:
            not_pushed = self.empty_vqip()
        else:
            excess_in = self.get_excess(direction = 'push', vqip = vqip, tag = tag)
            not_pushed = self.v_change_vqip(vqip, 
                                            max(vqip['volume'] - excess_in['volume'], 0))
        
        
        #Don't attempt to send volume that exceeds capacity
        vqip['volume'] -= not_pushed['volume']
        
        #Set push
        reply = self.out_port.push_set(vqip, tag)
        
        #Update total amount successfully sent
        vqip['volume'] -= reply['volume']
        
        #Combine non-sent water
        reply = self.blend_vqip(reply, not_pushed)
        
        #Update mass balance
        self.flow_in += vqip['volume']
        self.flow_out = self.flow_in
        
        self.vqip_in = self.blend_vqip(self.vqip_in, vqip)
        self.vqip_out = self.vqip_in
        
        return reply
    
    def send_pull_request(self, vqip, tag = 'default'):
        volume = vqip['volume']
        #Apply pipe capacity
        excess_in = self.get_excess(direction = 'pull', vqip = vqip)['volume']
        not_pulled = max(volume - excess_in, 0)
        volume -= not_pulled
        vqip['volume'] = volume
        
        #Make pull
        vqip = self.in_port.pull_set(vqip)
        
        #Update mass balance
        self.flow_in += vqip['volume']
        self.flow_out = self.flow_in
        
        self.vqip_in = self.blend_vqip(self.vqip_in, vqip)
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
        
    def send_pull_request(self, vqip, tag = 'default'):
        volume = vqip['volume']
        #Apply pipe capacity
        excess_in = self.get_excess(direction = 'pull', vqip = vqip)['volume']
        not_pulled = max(volume - excess_in, 0)
        volume -= not_pulled
        vqip['volume'] = volume
        #Make pull
        vqip = self.in_port.pull_set(vqip)
        
        #Update to vqtip
        vqtip = self.t_insert_vqip(vqip, self.number_of_timesteps)
        
        #vqtip enters arc as a request
        self.enter_queue(vqtip, direction = 'pull')
        
        #Update request queue and return pulls from queue
        reply = self.update_queue(direction = 'pull')
        return reply
        
    def send_push_request(self, vqip, tag = 'default', force = False):
        
        vqip = self.copy_vqip(vqip)
        
        if vqip['volume'] < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        
        #Apply pipe capacity
        if force:
            not_pushed = self.empty_vqip()
        else:
            excess_in = self.get_excess(direction = 'push', vqip = vqip, tag = tag)
            not_pushed = self.v_change_vqip(vqip, 
                                            max(vqip['volume'] - excess_in['volume'], 0))
        
            
        vqip['volume'] -= not_pushed['volume']
        
        #Create vqtip
        if 'time' in vqip.keys():
            vqtip = vqip
        else:
            vqtip = self.t_insert_vqip(vqip, 0)
        vqtip['time'] += self.number_of_timesteps
        
        #vqtip enters arc as a request
        self.enter_queue(vqtip, direction = 'push', tag = tag)
        
        #Update request queue
        _ = self.update_queue(direction = 'push')
        
        return not_pushed
    
    def enter_queue(self, vqtip, direction = None, tag = 'default'):
        #Form as request and append to queue
        request = {'vqtip' : vqtip,
                   'average_flow' : vqtip['volume'] / (vqtip['time'] + 1),
                   'direction' : direction,
                   'tag' : tag}
        
        self.queue.append(request)
        
        #Update inflows
        self.flow_in += request['average_flow']
        self.vqip_in = self.blend_vqip(self.vqip_in, vqtip)
        
    def update_queue(self, direction = None):
        
        done_requests = []
        
        total_removed = self.empty_vqip()
        #Iterate over requests
        for request in self.queue:
            if request['direction'] == direction:
                vqtip = request['vqtip']
                if vqtip['volume'] < constants.FLOAT_ACCURACY:
                    #Add to queue for removal
                    done_requests.append(request)
                    
                elif vqtip['time'] == 0:
                    vqip = self.t_remove_vqtip(vqtip)
                    if direction == 'push':
                        #Attempt to push request
                        reply = self.out_port.push_set(vqip, request['tag'])
                        removed = vqip['volume'] - reply['volume']
                        
                    elif direction == 'pull':
                        #Water has already been pulled, so assume all received
                        removed = vqtip['volume']
                    
                    else:
                        print('No direction')
                        
                    #Update outflows
                    self.flow_out += (request['average_flow'] * removed / vqip['volume'])
                    vqip_ = self.v_change_vqip(vqip, removed)
                    total_removed = self.blend_vqip(total_removed, vqip_)
                    
                    
                    #Update request
                    request['vqtip']['volume'] -= removed
                    
        self.vqip_out = self.blend_vqip(self.vqip_out, total_removed)                    
        
        #Remove done requests
        for request in done_requests:
            self.queue.remove(request)
        
        return total_removed
    
    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        # self.update_queue(direction = 'pull') # TODO Is this needed? - probably
        # self.update_queue(direction = 'push') # TODO Is this needed? - probably
        for request in self.queue:
            request['vqtip']['time'] = max(request['vqtip']['time'] - 1, 0)
    
    def reinit(self):
        self.end_timestep()
        self.queue = []
        
class AltQueueArc(QueueArc):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.queue = {0 : self.empty_vqip(), 1 : self.empty_vqip()}
        self.max_travel = 1
        
    def enter_queue(self, vqtip, direction = None, tag = 'default'):
        #NOTE- has no tags
        
        #Form as request and append to queue
        if vqtip['time'] in self.queue.keys():
            self.queue[vqtip['time']]  = self.blend_vqip(self.queue[vqtip['time']], vqtip)
        else:
            self.queue[vqtip['time']]  = vqtip
            self.max_travel = max(self.max_travel, vqtip['time'])
        
        #Update inflows
        self.flow_in += vqtip['volume'] / (vqtip['time'] + 1)
        self.vqip_in = self.blend_vqip(self.vqip_in, vqtip)
        
    def update_queue(self, direction = None):
        #NOTE - has no direction

        total_removed = self.copy_vqip(self.queue[0])

        #Push 0 travel time water
        reply = self.out_port.push_set(self.queue[0])
        self.queue[0]['volume'] = reply['volume']
        total_removed['volume'] -= reply['volume']

        self.flow_out += total_removed['volume']
        self.vqip_out = self.blend_vqip(self.vqip_out, total_removed)
        
        return total_removed

    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        # self.update_queue()
        queue_ = self.queue.copy()
        keys = self.queue.keys()
        for i in range(self.max_travel):
            if (i + 1) in keys:
                self.queue[i] = queue_[i+1]
                self.queue[i+1] = self.empty_vqip()

        self.queue[0] = self.blend_vqip(queue_[0], queue_[1])
    
    def reinit(self):
        self.end_timestep()
        self.queue = {0 : self.empty_vqip(), 1 : self.empty_vqip()}

class DecayArc(QueueArc):
    def __init__(self, **kwargs):
        self.decays = {}
        super().__init__(**kwargs)
        if 'parent' in dir(self):
            self.data_input_object = self.parent
        elif 'in_port' in dir(self):
            self.data_input_object = self.in_port
        else:
            print('warning: decay arc cannot access temperature data')
            
    def enter_queue(self, vqtip, direction = None, tag = 'default'):
        temperature = self.data_input_object.data_input_dict[('temperature', self.data_input_object.t)]
        vqtip_, diff = self.generic_temperature_decay(vqtip, self.decays, temperature)
        
        #TODO: mass balance isn't tracked within in arc, so vqtip_ is the decayed value sent onwards, but is less than the actual vqip_in
        
        #diff contains total gain(+)/loss(-) of pollutants due to decay
        #ignored for now because mass balance within arcs isn't tracked
        
        #Form as request and append to queue
        request = {'vqtip' : vqtip_,
                   'average_flow' : vqtip_['volume'] / (vqtip_['time'] + 1),
                   'direction' : direction,
                   'tag' : tag}
        
        self.queue.append(request)
        
        #Update inflows
        self.flow_in += request['average_flow']
        self.vqip_in = self.blend_vqip(self.vqip_in, vqtip)

    def end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        # self.update_queue(direction = 'pull') # TODO Is this needed? - probably
        # self.update_queue(direction = 'push') # TODO Is this needed? - probably
        for request in self.queue:
            temperature = self.data_input_object.data_input_dict[('temperature', self.data_input_object.t)]
            request['vqtip'], diff = self.generic_temperature_decay(request['vqtip'], self.decays, temperature)
            request['vqtip']['time'] = max(request['vqtip']['time'] - 1, 0)

class DecayArcAlt(AltQueueArc):
    def __init__(self, **kwargs):
        self.decays = {}
        super().__init__(**kwargs)
        self.end_timestep = self._end_timestep
        if 'parent' in dir(self):
            self.data_input_object = self.parent
        elif 'in_port' in dir(self):
            self.data_input_object = self.in_port
        else:
            print('warning: decay arc cannot access temperature data')
            
    def enter_queue(self, vqtip, direction = None, tag = 'default'):
        #NOTE- has no tags
        
        temperature = self.data_input_object.data_input_dict[('temperature', self.data_input_object.t)]
        vqtip, diff = self.generic_temperature_decay(vqtip, self.decays, temperature)
        #Form as request and append to queue
        if vqtip['time'] in self.queue.keys():
            self.queue[vqtip['time']]  = self.blend_vqip(self.queue[vqtip['time']], vqtip)
        else:
            self.queue[vqtip['time']]  = vqtip
            self.max_travel = max(self.max_travel, vqtip['time'])
        
        #Update inflows
        self.flow_in += vqtip['volume'] / (vqtip['time'] + 1)
        self.vqip_in = self.blend_vqip(self.vqip_in, vqtip)


    def _end_timestep(self):
        self.vqip_in = self.empty_vqip()
        self.vqip_out = self.empty_vqip()
        self.flow_in = 0
        self.flow_out = 0
        # self.update_queue()
        queue_ = self.queue.copy()
        keys = self.queue.keys()
        for i in range(self.max_travel):
            if (i + 1) in keys:
                temperature = self.data_input_object.data_input_dict[('temperature', self.data_input_object.t)]
                vqip, diff = self.generic_temperature_decay(queue_[i+1], self.decays, temperature)
                self.queue[i] = vqip
                self.queue[i+1] = self.empty_vqip()

        self.queue[0] = self.blend_vqip(queue_[0], queue_[1])
    
class SewerArc(Arc):
    pass

class WeirArc(SewerArc):
    pass

