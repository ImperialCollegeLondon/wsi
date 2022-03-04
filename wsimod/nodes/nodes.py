# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 08:43:32 2021

@author: Barney
"""
from wsimod.nodes import nodes
from wsimod.core import constants, WSIObj
from wsimod.arcs import AltQueueArc, DecayArc
from math import log10
class Node(WSIObj):
    """
    Base class for CWSD nodes.
    
    ...
    """
    def __init__(self,**kwargs):
        """
        Constructs all the necessary attributes for the node object

        Parameters
        ----------
        **kwargs : keyword arguments, optional (default= no attributes)
            Attributes to add to node as key=value pairs.
            
        Example
        -------
        my_node = nodes.Node()
        my_node = nodes.Node(name = 'london_wwtw')
        my_node = nodes.Node({'name' : 'london_wwtw',
                              'treatment_throughput_capacity' : 10})
        """
        #Get node types
        def all_subclasses(cls):
            return set(cls.__subclasses__()).union(
                [s for c in cls.__subclasses__() for s in all_subclasses(c)])
        node_types = [x.__name__ for x in all_subclasses(nodes.Node)] + ['Node']
        
        #Default essential parameters
        self.in_arcs = {}
        self.out_arcs = {}
        
        self.in_arcs_type = {x : {} for x in node_types}
        self.out_arcs_type = {x : {} for x in node_types}
        self.name = None
        self.date = None
        self.pull_set_handler = {'default' : self.pull_distributed}
        self.push_set_handler = {'default' : self.push_distributed}
        self.pull_check_handler = {'default' : self.pull_check_basic}
        self.push_check_handler = {'default' : self.push_check_basic}
        
        #Update args
        super().__init__(**kwargs)
        
        #Mass balance checking
        self.mass_balance_in = [self.total_in]
        self.mass_balance_out = [self.total_out]
        self.mass_balance_ds = [lambda : self.empty_vqip()]
    
    # def replace(self, newnode):
    #     #TODO - doesn't work because the bound methods (e.g., pull_set_handler) get 
    #     #associated with newnode and can't (as far as I can tell) be moved to self
    #
    #     """
    #     Replace node with new node, maintaining any existing references to original node
        
    #     Example
    #     -------
    #     print(my_node.name)
    #     my_node.update(Node(name = 'new_node'))
    #     print(my_node.name)
    #     """
        
        
    #     #You could use the below code to move the arcs_type references to arcs
    #     #that are attached to this node. However, if you were creating a new
    #     #subclass of Node then you would need to include this key in all 
    #     #arcs_type dictionaries in all nodes... which would get complicated
    #     #probably safest to leave the arcs_type keys that are associated with
    #     #this arc the same (for now...) -therefore - needs the same name
        
    #     # for arc in self.in_arcs.values():
    #     #     _ = arc.in_port.out_arcs_type[self.__class__.__name__].pop(arc.name)
    #     #     arc.in_port.out_arcs_type[newnode.__class__.__name__][arc.name] = arc
    #     # for arc in self.out_arcs.values():
    #     #     _ = arc.out_port.in_arcs_type[self.__class__.__name__].pop(arc.name)
    #     #     arc.out_port.in_arcs_type[newnode.__class__.__name__][arc.name] = arc
        
        
    #     #Replace class
    #     self.__class__ = newnode.__class__
        
    #     #Replace object information (keeping some old information such as in_arcs)
    #     for key in ['in_arcs',
    #                 'out_arcs',
    #                 'in_arcs_type',
    #                 'out_arcs_type']:
    #         newnode.__dict__[key] = self.__dict__[key]
    
    #     self.__dict__.clear()
    #     self.__dict__.update(newnode.__dict__)
        
        
    def total_in(self):
        '''
        Sum flow and pollutant concentrations entering a node

        Returns
        -------
        in_ (vqip): Blended vqip of in_arcs
        
        Example
        -------
        node_inflow = my_node.total_in()
        '''
        in_ = self.empty_vqip()
        for arc in self.in_arcs.values():
            in_ = self.blend_vqip(in_, arc.vqip_out)
            
        return in_
    
    def total_out(self):
        '''
        Sum flow and pollutant concentrations leaving a node

        Returns
        -------
        out_ (vqip): Blended vqip of out_arcs
        
        Example
        -------
        node_outflow = my_node.total_out()
        '''
        out_ = self.empty_vqip()
        for arc in self.out_arcs.values():
            out_ = self.blend_vqip(out_, arc.vqip_in)
            
        return out_
    
    def node_mass_balance(self):
        '''
        Checks mass balance for inflows/outflows/storage change in a node

        Returns
        -------
        Note: pollutants in return vqips are take absolute values, 
              not concentrations
        
        in_ (vqip) Blended vqip of in_arcs and other inputs
        out_ (vqip): Blended vqip of out_arcs and other outputs
        ds_ (vqip): Blended vqip of change in node tanks
        
        Example
        -------
        node_in, node_out, node_ds = my_node.node_mass_balance()
        
        Raises
        ------
        Message if mass balance does not close to constants.FLOAT_ACCURACY
        '''
        
        in_ = self.empty_vqip()
        for f in self.mass_balance_in:
            in_ = self.blend_vqip(in_, f())
        in_ = self.concentration_to_total(in_)
        
        out_ = self.empty_vqip()
        for f in self.mass_balance_out:
            out_ = self.blend_vqip(out_, f())
        out_ = self.concentration_to_total(out_)
            
        ds_ = self.empty_vqip()
        for f in self.mass_balance_ds:
            ds_f = f()
            for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                ds_[v] += ds_f[v]
        
        for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
            
            largest = max(in_[v], out_[v], ds_[v])

            if largest > constants.FLOAT_ACCURACY:
                magnitude = 10**int(log10(largest))
                in_10 = in_[v] / magnitude
                out_10 = out_[v] / magnitude
                ds_10 = ds_[v] / magnitude
            else:
                in_10 = in_[v]
                ds_10 = ds_[v]
                out_10 = out_[v]
            
            if abs(in_10 - ds_10 - out_10) > constants.FLOAT_ACCURACY:
                print("mass balance error for " + v)
        return in_, ds_, out_
        
            
    
    def pull_set(self, vqip, tag = 'default'):
        """
        Receives pull set requests from arcs and passes request 
        to query handler

        Parameters
        ----------
        vqip (vqip): the vqip request (by default, only the 'volume' 
                                       key is used)
        tag : optional message to direct query_handler which pull 
              function to call

        Returns
        -------
        reply from query_handler (vqip received)
        
        Example
        -------
        water_received = my_node.pull_set({'volume' : 10})
        """
        return self.query_handler(self.pull_set_handler, vqip, tag)
    
    def push_set(self, vqip, tag = 'default'):
        """
        Receives push set requests from arcs and passes request 
        to query handler

        Parameters
        ----------
        vqip (vqip): the vqip request 
        tag : optional message to direct query_handler which push 
              function to call

        Returns
        -------
        reply from query_handler (vqip not received)
        
        Example
        -------
        water_not_pushed = my_node.push_set(wastewater_vqip)
        """
        return self.query_handler(self.push_set_handler, vqip, tag)
    
    def pull_check(self, vqip = None, tag = 'default'):
        """
        Receives pull check requests from arcs and passes request 
        to query handler

        Parameters
        ----------
        vqip (vqip): the vqip request (by default, only the 'volume' 
                                       key is used)
        tag : optional message to direct query_handler which pull 
              function to call

        Returns
        -------
        reply from query_handler (vqip available)
        
        Example
        -------
        water_available = my_node.pull_check({'volume' : 10})
        """
        return self.query_handler(self.pull_check_handler, vqip, tag)
    
    def push_check(self, vqip = None, tag = 'default'):
        """
        Receives push check requests from arcs and passes request 
        to query handler

        Parameters
        ----------
        vqip (vqip): the vqip request
        tag : optional message to direct query_handler which push 
              function to call

        Returns
        -------
        reply from query_handler (vqip available)
        
        Example
        -------
        available_push_capacity = my_node.push_check(wastewater_vqip)
        """
        return self.query_handler(self.push_check_handler, vqip, tag)
    
    def get_direction_arcs(self, direction, of_type = None):
        """
        Identify arcs of all attached nodes in a given direction

        Parameters
        ----------
        direction (str) : can be either 'pull' or 'push' to send checks to 
                          receiving or contributing nodes
        of_type (str) : optional, can be specified to send checks only to 
                        nodes of a given type (must currently be a subclass in
                                               nodes.py)

        Returns
        -------
        f (str) : Either 'send_pull_check' or 'send_push_check' depending on 
                  direction
        arcs (list) : List of arc objects
        
        Raises
        ------
        Message if no direction is specified
        
        Example
        -------
        arcs_to_push_to = my_node.get_direction_arcs('push')
        arcs_to_pull_from = my_node.get_direction_arcs('pull')
        arcs_from_reservoirs = my_node.get_direction_arcs('pull',
                                                          of_type = 'Reservoir')
        """
        if of_type is None:
            if direction == "pull":
                arcs = list(self.in_arcs.values())
                f = 'send_pull_check'
            elif direction == "push":
                arcs = list(self.out_arcs.values())
                f = 'send_push_check'
            else:
                print('No direction')
        
        else:
            
            if type(of_type) is str:
                of_type = [of_type]
            
            #Assign arcs/function based on parameters
            arcs = []
            if direction == 'pull':
                for type_ in of_type:
                    arcs += list(self.in_arcs_type[type_].values())
                f = 'send_pull_check'
            elif direction == 'push':
                for type_ in of_type:
                    arcs += list(self.out_arcs_type[type_].values())
                f = 'send_push_check'
            else:
                print('No direction')
                
        return f, arcs
    
    def get_connected(self, direction = 'pull', of_type = None, tag = 'default'):
        """
        Send push/pull checks to all attached arcs in a given direction

        Parameters
        ----------
        direction (str) : The type of check to send to all attached nodes.
                          Can be 'push' or 'pull'. The default is 'pull'.
        of_type (str) : optional, can be specified to send checks only to 
                        nodes of a given type (must currently be a subclass in
                                               nodes.py)
        tag (str) : optional message to direct query_handler which function to call

        Returns
        -------
        connected (dict) : 
            Dictionary containing keys:
             'avail' (float) - total available volume for push/pull
             'priority' (float) - total (availability * preference) 
                                  of attached arcs
             'allocation' (dict) - contains all attached arcs in specified
                            direction and respective (availability * preference)
                            
        Example
        -------
        vqip_available_to_pull = my_node.get_direction_arcs()
        vqip_available_to_push = my_node.get_direction_arcs('push')
        avail_reservoir_vqip = my_node.get_direction_arcs('pull',
                                                          of_type = 'Reservoir')
        avail_sewer_push_to_sewers = my_node.get_direction_arcs('push',
                                                                of_type = 'Sewer',
                                                                tag = 'Sewer')
        """
        
        #Perform push/pull checks in direction to nodes of_type
        
        #Return connected dict, containing total_avail, and priorities 
        #of arcs depending on preference
        
        #Initialise connected dict
        connected = {'avail' : 0,
                     'priority' : 0,
                     'allocation' : {}}
        
        f, arcs = self.get_direction_arcs(direction, of_type)
        
        #Iterate over arcs, updating connected dict
        for arc in arcs:
            avail = getattr(arc, f)(tag = tag)['volume']
            connected['avail'] += avail
            preference = arc.preference
            connected['priority'] += avail * preference
            connected['allocation'][arc.name] = avail * preference
                
        return connected
    
    def query_handler(self, handler, ip, tag):
        """
        Sends all push/pull requests using the handler (i.e., ensures the 
        correct function is used that lines up with 'tag')

        Parameters
        ----------
        handler (dict) : contains all push/pull requests for various tags
        ip (vqip) : the vqip request
        tag (str) : describes what type of push/pull request should be called

        Returns
        -------
        reply from push/pull request
        
        Raises
        ------
        Message if no functions are defined for tag
        
        Example
        ------
        See push_set/push_check/pull_set/pull_check
        """
        try: 
            return handler[tag](ip)
        except:
            if tag not in handler.keys():
                print('No functions defined for ' + tag)
                return handler[tag](ip)
            else:
                print('Some other error')
                return handler[tag](ip)
    
    def pull_distributed(self, vqip, of_type = None, tag = 'default'):
        
        #Pull in proportion from connected by priority
        
        #Initialise pulled, deficit, connected, iter_
        pulled = self.empty_vqip()
        deficit = vqip['volume']
        connected = self.get_connected(direction = 'pull', of_type = of_type, tag = tag)
        iter_ = 0
        
        #Iterate over sending nodes until deficit met
        while (((deficit > constants.FLOAT_ACCURACY) &
                (connected['avail'] > constants.FLOAT_ACCURACY)) &
                (iter_ < constants.MAXITER)):
            
            #Pull from connected
            for key, allocation in connected['allocation'].items():
                received = self.in_arcs[key].send_pull_request({'volume' : deficit *
                                                                   allocation / 
                                                                   connected['priority']},
                                                               tag = tag)
                pulled = self.blend_vqip(pulled, received)
            
            #Update deficit, connected and iter_
            deficit = vqip['volume'] - pulled['volume']
            connected = self.get_connected(direction = 'pull', of_type = of_type, tag = tag)
            iter_ += 1
        
        if iter_ == constants.MAXITER:
            print('Maxiter reached')
        return pulled
    
    def push_distributed(self, vqip, of_type = None, tag = 'default'):
        
        if len(self.out_arcs) == 1:
            #If only one out_arc, just send the water down that
            if of_type == None:
                not_pushed_ = next(iter(self.out_arcs.values())).send_push_request(vqip, tag = tag)
            elif any([x in of_type for x, y in self.out_arcs_type.items() if len(y) > 0]):
                not_pushed_ = next(iter(self.out_arcs.values())).send_push_request(vqip, tag = tag)
            else:
                #No viable out arcs
                not_pushed_ = vqip
        else:
            #Push in proportion to connected by priority
            #Initialise pushed, deficit, connected, iter_
            not_pushed = vqip['volume']
            not_pushed_ = self.copy_vqip(vqip)
            connected = self.get_connected(direction = 'push', 
                                           of_type = of_type, 
                                           tag = tag)
            iter_ = 0
            
            #Iterate over receiving nodes until sent
            while ((not_pushed > constants.FLOAT_ACCURACY) & 
                  (connected['avail'] > constants.FLOAT_ACCURACY) &
                  (iter_ < constants.MAXITER)):
    
                #Push to connected
                amount_to_push = min(connected['avail'], not_pushed)
                
                for key, allocation in connected['allocation'].items():
                    
                    to_send = amount_to_push * allocation / connected['priority']
                    to_send = self.v_change_vqip(vqip, to_send)
                    reply = self.out_arcs[key].send_push_request(to_send, tag = tag)
                    not_pushed_['volume'] -= (to_send['volume'] - reply['volume'])
                
                not_pushed = not_pushed_['volume']
                connected = self.get_connected(direction = 'push', 
                                               of_type = of_type, 
                                               tag = tag)
                iter_ += 1
                
            if iter_ == constants.MAXITER:
                print('Maxiter reached')
                
        return not_pushed_
        
    def check_basic(self, direction, vqip = None, of_type = None, tag = 'default'):
        f, arcs = self.get_direction_arcs(direction, of_type)
        
        #Iterate over arcs, updating connected dict
        avail = self.empty_vqip()
        for arc in arcs:
            avail = self.blend_vqip(avail, getattr(arc, f)(tag = tag))
            
        if vqip is not None:
            avail['volume'] = min(avail['volume'], vqip['volume'])
            
        return avail
    
    def pull_check_basic(self, vqip = None, of_type = None, tag = 'default'):
        #TODO not sure whether these should have of_type... maybe not tag either?
        return self.check_basic('pull', vqip, of_type, tag)
    
    def push_check_basic(self, vqip = None, of_type = None, tag = 'default'):
        return self.check_basic('push', vqip, of_type, tag)
    
    def pull_set_deny(self, vqip):
        #Returns no available water to pull
        print('Attempted pull set from deny')
        return self.empty_vqip()
    
    def pull_check_deny(self, vqip = None):
        #Returns no available water to pull
        print('Attempted pull check from deny')
        return self.empty_vqip()

    def push_set_deny(self, vqip):
        #Returns push denied
        print('Attempted push set to deny')
        return self.empty_vqip()
    
    def push_check_deny(self, vqip = None):
        #Returns no water available to push
        print('Attempted push check to deny')
        return self.empty_vqip()
    
    def end_timestep(self):
        pass
    
    def reinit(self):
        pass

class Tank(WSIObj):
    #A standard storage with capacity
    def __init__(self,**kwargs):
        
        self.capacity = 0
        self.area = 1
        self.datum = 10
        self.decays = None
        #Vol. of water in a tank that is unavailable to evaporation. Must be >0
        #Otherwise, evaporation will remove pollutants if it drops a tank to 0.
        self.unavailable_to_evap = 0.000001
        
        super().__init__(**kwargs)
        
        if self.decays:
            self.end_timestep = self.end_timestep_decay
        
        #TODO enable stores to be initialised not empty
        if 'initial_storage' in dir(self):
            self.storage = self.copy_vqip(self.initial_storage)
            self.storage_ = self.copy_vqip(self.initial_storage)
        else:
            self.storage = self.empty_vqip()
            self.storage_ = self.empty_vqip()
    
    def ds(self):
        return self.ds_vqip(self.storage, self.storage_)
        
    
    def pull_ponded(self):
        ponded = max(self.storage['volume'] - self.capacity, 0)
        ponded = self.pull_storage(self.v_change_vqip(self.storage, ponded) )
        return ponded
    
    def get_avail(self, vqip = None):
        reply = self.copy_vqip(self.storage)
        if vqip is None:
            return reply
        else:
            reply['volume'] = min(reply['volume'], vqip['volume'])
            return reply
    
    def get_excess(self, vqip = None):
        vol = max(self.capacity - self.storage['volume'], 0)
        if vqip is not None:
            vol = min(vqip['volume'], vol)
        return self.v_change_vqip(self.storage, vol)
    
    def push_storage(self, vqip, force = False):
        #Push to Tank
        
        if force:
            #Directly add request to storage
            self.storage = self.blend_vqip(self.storage, vqip)
            return self.empty_vqip()
        
        #Check whether request can be met
        excess = self.get_excess()['volume']
        
        #Adjust accordingly
        reply = max(vqip['volume'] - excess, 0)
        reply = self.v_change_vqip(vqip, reply)
        entered = self.v_change_vqip(vqip, vqip['volume'] - reply['volume'])
        
        #Update storage
        self.storage = self.blend_vqip(self.storage, entered)
            
        return reply
    
    def pull_storage(self, vqip):
        #Pull from Tank
        
        #Adjust based on available volume
        reply = min(vqip['volume'], self.storage['volume'])
        if (self.storage['volume'] - reply) < self.unavailable_to_evap:
            reply = max(reply - self.unavailable_to_evap, 0)
        
        #Extract from storage
        self.storage['volume'] -= reply
        
        #Update reply to vqip
        reply = self.v_change_vqip(self.storage, reply)
        
        return reply
        

    def get_head(self, datum = None, non_head_storage = 0):
        #Area-volume calc
        
        #If datum not provided use object datum
        if not datum:
            datum = self.datum
        
        #Calculate head generating storage
        head_storage = max(self.storage['volume'] - non_head_storage, 0)
        
        #Perform head calculation
        head = head_storage / self.area + datum
        
        return head
    
    def evaporate(self, evap):
        avail = max(self.get_avail()['volume'] - self.unavailable_to_evap, 0)
        evap = min(evap, avail)
        self.storage = self.v_distill_vqip(self.storage, evap)
        return evap
    
    def push_total(self, vqip):
        
        #Push vqip to storage where pollutants are given as a total rather than concentration
        storage = self.concentration_to_total(self.storage)
        self.storage = self.total_to_concentration(self.sum_vqip(storage, vqip))
        
        return self.empty_vqip()
    
    def end_timestep(self):
        self.storage_ = self.copy_vqip(self.storage)
        
    def end_timestep_decay(self):
        temperature = self.parent.data_input_dict[('temperature', self.parent.t)]
        #TODO: this decay is not in mass balance
        self.storage, _ = self.generic_temperature_decay(self.storage, self.decays, temperature)
        self.storage_ = self.copy_vqip(self.storage)
        
    def reinit(self):
        self.storage = self.empty_vqip()
        self.storage_ = self.empty_vqip()
    
class QueueTank(Tank):
    #A storage that can allow delay before parts of it are accessible
    def __init__(self, **kwargs):
        self.number_of_timesteps = 0
        
        super().__init__(**kwargs)
        
        #TODO enable stores to be initialised not empty
        self.active_storage = self.copy_vqip(self.storage)
        
        self.out_arcs = {}
        self.in_arcs = {}
        if self.decays:
            self.internal_arc = DecayArc(in_port = self, 
                                        out_port = self,
                                        number_of_timesteps = self.number_of_timesteps)
        else:
            self.internal_arc = AltQueueArc(in_port = self, 
                                            out_port = self,
                                            number_of_timesteps = self.number_of_timesteps)
    
    def get_avail(self):
        return self.copy_vqip(self.active_storage)
    
    def push_storage(self, vqip, time = None, force = False):
        
        if time is None:
            vqip['time'] = self.number_of_timesteps
        else:
            vqip['time'] = time
        
        #Push to QueueTank
        reply = self.internal_arc.send_push_request(vqip, force)
        self.storage = self.blend_vqip(self.storage,
                                       self.v_change_vqip(vqip, 
                                                          vqip['volume'] - reply['volume']))
        return reply
    
    def pull_storage(self, vqip):
        #Pull from QueueTank
        
        #Adjust based on available volume
        reply = min(vqip['volume'], self.active_storage['volume'])
        
        #Extract from active_storage
        self.active_storage['volume'] -= reply
        
        #Update reply to vqip
        reply = self.v_change_vqip(self.active_storage, reply)
        
        #Extract from storage
        self.storage = self.extract_vqip(self.storage, reply)
        
        return reply
        
    def push_check(self, vqip = None, tag = 'default'):
        #TODO does behaviour for volume = None need to be defined?
        excess = self.get_excess()
        if vqip is not None:
            excess['volume'] = min(vqip['volume'], 
                                   excess['volume'])
        return excess
    
    def push_set(self, vqip, tag = 'default'):
        #Behaves differently from normal push setting
        #Assume sufficient capacity, instead receives
        #vqtips after internal arc. To push to QueueTanks,
        #use push_storage
        
        self.active_storage = self.blend_vqip(self.active_storage, vqip)
        
        return self.empty_vqip()
        
    def end_timestep(self):
        self.internal_arc.end_timestep()
        self.storage_ = self.copy_vqip(self.storage)
    
    def reinit(self):
        self.internal_arc.reinit()
        self.storage = self.empty_vqip()
        self.storage_ = self.empty_vqip()
        self.active_storage = self.empty_vqip()
        