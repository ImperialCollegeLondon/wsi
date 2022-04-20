# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
"""
from wsimod.nodes.nodes import Node, Tank
from wsimod.core import constants

class WWTW(Node):
    def __init__(self, **kwargs):
        #Default parameters
        self.stormwater_storage_capacity = 10
        self.stormwater_storage_area = 1
        self.stormwater_storage_elevation = 10
        self.treatment_throughput_capacity = 10
        
        
        self.process_multiplier = {x : 0.2 for x in constants.ADDITIVE_POLLUTANTS}
        self.liquor_multiplier = {x : 5 for x in constants.ADDITIVE_POLLUTANTS}
        self.liquor_multiplier['volume'] = 0.03
        
        self.percent_solids = 0.0002
        
        
        #Update args
        super().__init__(**kwargs)
        
        self.process_multiplier['volume'] = 1 - self.percent_solids - self.liquor_multiplier['volume']
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_reuse
        self.pull_check_handler['default'] = self.pull_check_reuse
        self.push_set_handler['Sewer'] = self.push_set_sewer
        
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['Sewer'] = self.push_check_sewer
        
        #Initialise parameters
        self.current_input = self.empty_vqip()
        self.throughput = self.empty_vqip()
        self.liquor_ = self.empty_vqip()
        self.losses = self.empty_vqip()
        self.discharge = self.empty_vqip()
        self.liquor = self.empty_vqip()
        
        #Create tanks
        self.stormwater_tank = Tank(capacity = self.stormwater_storage_capacity,
                                    area = self.stormwater_storage_area,
                                    datum = self.stormwater_storage_elevation)
        
        #Mass balance
        self.mass_balance_out.append(lambda : self.losses)
        self.mass_balance_ds.append(lambda : self.stormwater_tank.ds())
        self.mass_balance_ds.append(lambda : self.ds_vqip(self.liquor,
                                                          self.liquor_))
        
    def get_excess_throughput(self):
        return max(self.treatment_throughput_capacity -\
                   self.current_input['volume'], 
                   0)
    
    def calculate_discharge(self):
        #Run WWTW model
        
        #Try to clear stormwater
        excess = self.get_excess_throughput()
        if (self.stormwater_tank.get_avail()['volume'] > constants.FLOAT_ACCURACY) & \
           (excess > constants.FLOAT_ACCURACY):
            to_pull = min(excess,self.stormwater_tank.get_avail()['volume'])
            to_pull = self.v_change_vqip(self.stormwater_tank.storage, to_pull)
            cleared_stormwater = self.stormwater_tank.pull_storage(to_pull)
            self.current_input = self.blend_vqip(self.current_input, 
                                                 cleared_stormwater)
        
        #Run processes
        influent = self.blend_vqip(self.current_input,
                                   self.liquor)
        
        #Calculate effluent, liquor and solids
        discharge_holder = self.empty_vqip()
        for key in constants.ADDITIVE_POLLUTANTS + ['volume']:
            discharge_holder[key] = influent[key] * self.process_multiplier[key]
            self.liquor[key] = influent[key] * self.liquor_multiplier[key]
            
        self.losses['volume'] = influent['volume'] * self.percent_solids
        
        for key in constants.ADDITIVE_POLLUTANTS:
            self.losses[key] = (influent[key] * influent['volume'] - \
                                discharge_holder[key] * discharge_holder['volume'] - \
                                self.liquor[key] * self.liquor['volume'])
            self.losses[key] /= self.losses['volume']
        
        #Blend with any existing discharge
        self.discharge = self.blend_vqip(self.discharge, discharge_holder)
    
    
        
    
    def make_discharge(self):
        reply = self.push_distributed(self.discharge)
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('WWTW couldnt push')
    
    def push_check_sewer(self, vqip = None):
        excess_throughput = self.get_excess_throughput()
        excess_tank = self.stormwater_tank.get_excess()
        
        if vqip is None:
            vqip = self.empty_vqip()
        
        return self.v_change_vqip(vqip, excess_tank['volume'] + excess_throughput)
    
    def push_set_sewer(self, vqip):
        #Receive water from sewers
        
        #Check if can directly be treated
        sent_direct = self.get_excess_throughput()
        
        sent_direct = min(sent_direct, vqip['volume'])
        
        sent_direct = self.v_change_vqip(vqip, sent_direct)
        
        self.current_input = self.blend_vqip(self.current_input,
                                             sent_direct)
        
        if sent_direct['volume'] == vqip['volume']:
            #If all added to input, no problem
            return self.empty_vqip()
        
        #Next try temporary storage
        vqip = self.v_change_vqip(vqip, 
                                  vqip['volume'] - sent_direct['volume'])
        
        vqip = self.stormwater_tank.push_storage(vqip)
        
        if vqip['volume'] > constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        
        #TODO what to do here ???
        return vqip
    
    def pull_set_reuse(self, vqip):
        #Respond to request of water for reuse/MRF
        reply_vol = min(vqip['volume'], 
                        self.discharge['volume'])
        reply = self.v_change_vqip(self.discharge, reply_vol)
        self.discharge['volume'] -= reply_vol
        return reply

    def pull_check_reuse(self, vqip = None):
        #Respond to request of water for reuse/MRF
        return self.copy_vqip(self.discharge)
    
    def end_timestep(self):
        self.liquor_ = self.copy_vqip(self.liquor)
        self.current_input = self.empty_vqip()
        self.discharge = self.empty_vqip()
        self.stormwater_tank.end_timestep()

class FWTW(Node):
    def __init__(self, **kwargs):
        #Default parameters
        self.service_reservoir_storage_capacity = 10
        self.service_reservoir_storage_area = 1
        self.service_reservoir_storage_elevation = 10
        self.service_reservoir_inital_storage = 0
        self.treatment_throughput_capacity = 10
        
        
        self.process_multiplier = {x : 0.5 for x in constants.ADDITIVE_POLLUTANTS}
        self.liquor_multiplier = {x : 5 for x in constants.ADDITIVE_POLLUTANTS}
        self.liquor_multiplier['volume'] = 0.01
        
        self.percent_solids = 0.0002
        
        
        #Update args
        super().__init__(**kwargs)
        
        
        self.process_multiplier['volume'] = 1 - self.percent_solids - self.liquor_multiplier['volume']
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_fwtw
        self.pull_check_handler['default'] = self.pull_check_fwtw
        
        self.push_set_handler['default'] = self.push_set_deny
        self.push_set_handler['default'] = self.push_check_deny
        
        #Initialise parameters
        self.solids = self.empty_vqip()
        self.liquor = self.empty_vqip()
        self.total_deficit = self.empty_vqip()
        self.total_pulled = self.empty_vqip()
        self.previous_pulled = self.empty_vqip()
        #Create tanks
        self.service_reservoir_tank = Tank(capacity = self.service_reservoir_storage_capacity,
                                    area = self.service_reservoir_storage_area,
                                    datum = self.service_reservoir_storage_elevation)
        self.service_reservoir_tank.storage['volume'] = self.service_reservoir_inital_storage
        self.service_reservoir_tank.storage_['volume'] = self.service_reservoir_inital_storage
        
        #Mass balance
        self.mass_balance_in.append(lambda : self.total_deficit)
        self.mass_balance_ds.append(lambda : self.service_reservoir_tank.ds())
 
    def get_excess_throughput(self):
        return max(self.treatment_throughput_capacity -\
                   self.current_input['volume'], 
                   0)
    
    def treat_water(self):
        #Run WWTW model
        
        target_throughput = self.service_reservoir_tank.get_excess()
        
        target_throughput = min(target_throughput['volume'], self.treatment_throughput_capacity)
        
        throughput = self.pull_distributed({'volume' : target_throughput})
        
        deficit = max(self.previous_pulled['volume'] - throughput['volume'], 0)
        deficit = self.v_change_vqip(self.previous_pulled, deficit)
        
        
        
        throughput = self.blend_vqip(throughput, deficit)
        
        self.total_deficit = self.blend_vqip(self.total_deficit, deficit)
        
        if self.total_deficit['volume'] > constants.FLOAT_ACCURACY:
            print('deficit')
        
        #Calculate effluent, liquor and solids
        discharge_holder = self.empty_vqip()
        for key in constants.ADDITIVE_POLLUTANTS + ['volume']:
            discharge_holder[key] = throughput[key] * self.process_multiplier[key]
            self.liquor[key] = throughput[key] * self.liquor_multiplier[key]
            
        self.solids['volume'] = throughput['volume'] * self.percent_solids
        
        for key in constants.ADDITIVE_POLLUTANTS:
            self.solids[key] = (throughput[key] * throughput['volume'] - \
                                discharge_holder[key] * discharge_holder['volume'] - \
                                self.liquor[key] * self.liquor['volume'])
            self.solids[key] /= self.solids['volume']
        
        #Discharge liquor and solids to sewers
        push_back = self.blend_vqip(self.liquor, self.solids)
        self.push_distributed(push_back, of_type = 'Sewer')
        
        #Send water to service reservoirs
        excess = self.service_reservoir_tank.push_storage(discharge_holder)
        
        if excess['volume'] > 0:
            print("excess treated water")
    
    def pull_check_fwtw(self, vqip = None):
        return self.service_reservoir_tank.get_avail(vqip)
    
    def pull_set_fwtw(self, vqip):
        pulled = self.service_reservoir_tank.pull_storage(vqip)
        self.total_pulled = self.blend_vqip(self.total_pulled, pulled)
        return pulled
    
    def end_timestep(self):
        self.service_reservoir_tank.end_timestep()
        self.total_deficit = self.empty_vqip()
        self.previous_pulled = self.copy_vqip(self.total_pulled)
        self.total_pulled = self.empty_vqip()
        
    def reinit(self):
        self.service_reservoir_tank.reinit()