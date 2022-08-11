# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
Converted to totals on 2022-05-03

"""
from wsimod.nodes.nodes import Node, Tank
from wsimod.core import constants

class WTW(Node):
    def __init__(self,
                        name,
                        treatment_throughput_capacity = 10,
                        process_multiplier = {},
                        liquor_multiplier = {},
                        percent_solids = 0.0002):
        #Default parameters
        self.treatment_throughput_capacity = treatment_throughput_capacity
        if len(process_multiplier) > 0:
            self.process_multiplier = process_multiplier
        else:
            self.process_multiplier = {x : 0.2 for x in constants.ADDITIVE_POLLUTANTS}
        if len(liquor_multiplier) > 0:
            self.liquor_multiplier = liquor_multiplier
        else:
            self.liquor_multiplier = {x : 0.7 for x in constants.ADDITIVE_POLLUTANTS}
            self.liquor_multiplier['volume'] = 0.03
        
        self.percent_solids = percent_solids
        
        #Update args
        super().__init__(name)
        
        self.process_multiplier['volume'] = 1 - self.percent_solids - self.liquor_multiplier['volume']
        
        #Update handlers        
        self.push_set_handler['default'] = self.push_set_deny
        self.push_set_handler['default'] = self.push_check_deny
        
        #Initialise parameters
        self.current_input = self.empty_vqip()
        self.treated = self.empty_vqip()
        self.liquor = self.empty_vqip()
        self.solids = self.empty_vqip()
        
    def get_excess_throughput(self):
        return max(self.treatment_throughput_capacity -\
                   self.current_input['volume'], 
                   0)
    
    def treat_current_input(self):
        #Treat current input
        influent = self.copy_vqip(self.current_input)
        
        #Calculate effluent, liquor and solids
        discharge_holder = self.empty_vqip()
        for key in constants.ADDITIVE_POLLUTANTS + ['volume']:
            discharge_holder[key] = influent[key] * self.process_multiplier[key]
            self.liquor[key] = influent[key] * self.liquor_multiplier[key]
            
        self.solids['volume'] = influent['volume'] * self.percent_solids
        
        for key in constants.ADDITIVE_POLLUTANTS:
            self.solids[key] = (influent[key] - discharge_holder[key] - self.liquor[key])
        
        #Blend with any existing discharge
        self.treated = self.sum_vqip(self.treated, discharge_holder)

    
    def end_timestep(self):
        self.current_input = self.empty_vqip()
        self.treated = self.empty_vqip()
        
class WWTW(WTW):
    def __init__(self,
                        name,
                        treatment_throughput_capacity = 10,
                        process_multiplier = {},
                        liquor_multiplier = {},
                        percent_solids = 0.0002,
                        stormwater_storage_capacity = 10,
                        stormwater_storage_area = 1,
                        stormwater_storage_elevation = 10):
        self.tank_parameters = {}
        self.stormwater_storage_capacity = stormwater_storage_capacity
        self.stormwater_storage_area = stormwater_storage_area
        self.stormwater_storage_elevation = stormwater_storage_elevation

        #Update args
        super().__init__(name,
                                treatment_throughput_capacity = treatment_throughput_capacity,
                                process_multiplier = process_multiplier,
                                liquor_multiplier = liquor_multiplier,
                                percent_solids = percent_solids)
        
        self.end_timestep = self.end_timestep_
        
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_reuse
        self.pull_check_handler['default'] = self.pull_check_reuse
        self.push_set_handler['Sewer'] = self.push_set_sewer
        self.push_check_handler['Sewer'] = self.push_check_sewer
        
        #Create tanks
        self.stormwater_tank = Tank(capacity = self.stormwater_storage_capacity,
                                    area = self.stormwater_storage_area,
                                    datum = self.stormwater_storage_elevation)
        
        #Initialise states 
        self.liquor_ = self.empty_vqip()
        self.previous_input = self.empty_vqip()
        self.current_input = self.empty_vqip()
        
        #Mass balance
        self.mass_balance_out.append(lambda : self.solids) # Assume these go to landfill
        self.mass_balance_ds.append(lambda : self.stormwater_tank.ds())
        self.mass_balance_ds.append(lambda : self.ds_vqip(self.liquor,
                                                          self.liquor_)) #Change in liquor
    def calculate_discharge(self):
        #Run WWTW model
        
        #Try to clear stormwater
        excess = self.get_excess_throughput()
        if (self.stormwater_tank.get_avail()['volume'] > constants.FLOAT_ACCURACY) & \
           (excess > constants.FLOAT_ACCURACY):
            to_pull = min(excess,self.stormwater_tank.get_avail()['volume'])
            to_pull = self.v_change_vqip(self.stormwater_tank.storage, to_pull)
            cleared_stormwater = self.stormwater_tank.pull_storage(to_pull)
            self.current_input = self.sum_vqip(self.current_input, 
                                               cleared_stormwater)
        
        #Run processes
        self.current_input = self.sum_vqip(self.current_input,
                                           self.liquor)
        self.treat_current_input()
    
    def make_discharge(self):
        reply = self.push_distributed(self.treated)
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
        vqip_ = self.copy_vqip(vqip)
        #Check if can directly be treated
        sent_direct = self.get_excess_throughput()
        
        sent_direct = min(sent_direct, vqip['volume'])
        
        sent_direct = self.v_change_vqip(vqip, sent_direct)
        
        self.current_input = self.sum_vqip(self.current_input,
                                           sent_direct)
        
        if sent_direct['volume'] == vqip['volume']:
            #If all added to input, no problem
            return self.empty_vqip()
        
        #Next try temporary storage
        vqip = self.v_change_vqip(vqip, 
                                  vqip['volume'] - sent_direct['volume'])
        
        vqip = self.stormwater_tank.push_storage(vqip)
        
        if vqip['volume'] < constants.FLOAT_ACCURACY:
            return self.empty_vqip()
        else:
            #TODO what to do here ???
            return vqip
    
    def pull_set_reuse(self, vqip):
        #Respond to request of water for reuse/MRF
        reply_vol = min(vqip['volume'], 
                        self.treated['volume'])
        reply = self.v_change_vqip(self.treated, reply_vol)
        self.treated = self.v_change_vqip(self.treated, self.treated['volume'] - reply_vol)
        return reply

    def pull_check_reuse(self, vqip = None):
        #Respond to request of water for reuse/MRF
        return self.copy_vqip(self.previous_input)
    
    def end_timestep_(self):
        self.liquor_ = self.copy_vqip(self.liquor)
        self.previous_input = self.copy_vqip(self.current_input)
        self.current_input = self.empty_vqip()
        self.treated = self.empty_vqip()
        self.stormwater_tank.end_timestep()
        
class FWTW(WTW):
    def __init__(self,
                        name,
                        treatment_throughput_capacity = 10,
                        process_multiplier = {},
                        liquor_multiplier = {},
                        percent_solids = 0.0002,
                        service_reservoir_storage_capacity = 10,
                        service_reservoir_storage_area = 1,
                        service_reservoir_storage_elevation = 10,
                        service_reservoir_initial_storage = 0,
                        data_input_dict = {}):
        #Default parameters
        self.service_reservoir_storage_capacity = service_reservoir_storage_capacity
        self.service_reservoir_storage_area = service_reservoir_storage_area
        self.service_reservoir_storage_elevation = service_reservoir_storage_elevation
        self.service_reservoir_initial_storage = service_reservoir_initial_storage
        self.data_input_dict = data_input_dict
        
        #Update args
        super().__init__(name,
                                treatment_throughput_capacity = treatment_throughput_capacity,
                                process_multiplier = process_multiplier,
                                liquor_multiplier = liquor_multiplier,
                                percent_solids = percent_solids)
        self.end_timestep = self.end_timestep_
                
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_fwtw
        self.pull_check_handler['default'] = self.pull_check_fwtw
        
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_check_deny
        
        #Initialise parameters
        self.total_deficit = self.empty_vqip()
        self.total_pulled = self.empty_vqip()
        self.previous_pulled = self.empty_vqip()
        
        #Create tanks
        self.service_reservoir_tank = Tank(capacity = self.service_reservoir_storage_capacity,
                                    area = self.service_reservoir_storage_area,
                                    datum = self.service_reservoir_storage_elevation,
                                    initial_storage = self.service_reservoir_initial_storage)
        # self.service_reservoir_tank.storage['volume'] = self.service_reservoir_inital_storage
        # self.service_reservoir_tank.storage_['volume'] = self.service_reservoir_inital_storage
        
        #Mass balance
        self.mass_balance_in.append(lambda : self.total_deficit)
        self.mass_balance_ds.append(lambda : self.service_reservoir_tank.ds())
    
    def treat_water(self):
        #Run WWTW model
        target_throughput = self.service_reservoir_tank.get_excess()
        
        target_throughput = min(target_throughput['volume'], self.treatment_throughput_capacity)
        
        throughput = self.pull_distributed({'volume' : target_throughput})
        
        deficit = max(self.previous_pulled['volume'] - throughput['volume'], 0)
        deficit = self.v_change_vqip(self.previous_pulled, deficit)
        
        self.current_input = self.sum_vqip(throughput, deficit)
        
        self.total_deficit = self.sum_vqip(self.total_deficit, deficit)
        
        if self.total_deficit['volume'] > constants.FLOAT_ACCURACY:
            # print('deficit')
            pass
        
        self.treat_current_input()
        
        #Discharge liquor and solids to sewers
        push_back = self.sum_vqip(self.liquor, self.solids)
        rejected = self.push_distributed(push_back, of_type = 'Sewer')
        
        if rejected['volume'] > constants.FLOAT_ACCURACY:
            print('nowhere for sludge to go - mass balance error incoming')
        
        #Send water to service reservoirs
        excess = self.service_reservoir_tank.push_storage(self.treated)
        
        if excess['volume'] > 0:
            print("excess treated water")
    
    def pull_check_fwtw(self, vqip = None):
        return self.service_reservoir_tank.get_avail(vqip)
    
    def pull_set_fwtw(self, vqip):
        pulled = self.service_reservoir_tank.pull_storage(vqip)
        self.total_pulled = self.sum_vqip(self.total_pulled, pulled)
        return pulled
    
    def end_timestep_(self):
        self.service_reservoir_tank.end_timestep()
        self.total_deficit = self.empty_vqip()
        self.previous_pulled = self.copy_vqip(self.total_pulled)
        self.total_pulled = self.empty_vqip()
        self.treated = self.empty_vqip()
        
    def reinit(self):
        self.service_reservoir_tank.reinit()
