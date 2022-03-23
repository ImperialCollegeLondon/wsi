# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 09:28:59 2021

@author: leyan
"""


from wsimod.nodes.nodes import Node
from wsimod.nodes.nodes import Tank
from wsimod.core import constants
from copy import deepcopy

class Groundwater(Node):
    def __init__(self, **kwargs):
        
        self.capacity = constants.UNBOUNDED_CAPACITY
        self.area = 1e9
        self.datum = 10
        
        self.residence_time = 500 # !!! [days]
        
        super().__init__(**kwargs)
        
        self.baseflow = self.empty_vqip()
        #Create tank
        self.gw_tank = Tank(capacity = self.capacity,
                            area = self.area,
                            datum = self.datum,
                            initial_storage = 0.1 * 1e4,
                            )
        
        
        #Update handlers
        self.push_set_handler['default'] = self.push_set_gw
        self.pull_set_handler['default'] = self.pull_set_gw
        self.push_check_handler['default'] = self.push_check_gw
        self.pull_check_handler['default'] = self.pull_check_gw
        
        #Mass balance
        self.mass_balance_ds.append(lambda : self.gw_tank_ds_() )
    
    def return_river_flow(self):
        self.baseflow = deepcopy(self.gw_tank.storage) # vqip
        self.baseflow['volume'] = self.gw_tank.storage['volume'] / self.residence_time # TODO should be [Ml/d]
        self.gw_tank.storage['volume'] -= self.baseflow['volume'] # TODO can use pull_storage()
        if self.gw_tank.storage['volume'] < 0 :
            print('groundwater storage is < 0')
        
        self.baseflow['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(self.baseflow.keys()) - set(['volume']):
            self.baseflow[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        reply = self.push_distributed(self.baseflow,
                                      of_type = ['River'])
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('Groundwater couldnt push')
    
    def pull_set_gw(self, vqip):
        vqip = self.copy_vqip(vqip)
        vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(vqip.keys()) - set(['volume']):
            vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.gw_tank.pull_storage(vqip)
        reply = self.copy_vqip(reply)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        return reply    
    
    def gw_tank_ds_(self):
        ds = self.gw_tank.ds() 
        for key in constants.ADDITIVE_POLLUTANTS:
            ds[key] *= constants.MG_L_TO_KG_M3
        ds['volume'] *= constants.ML_TO_M3
        return ds
        
    def push_set_gw(self, vqip):
        vqip = self.copy_vqip(vqip)
        vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(vqip.keys()) - set(['volume']):
            vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.gw_tank.push_storage(vqip)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]    
        return reply            
    
    def pull_check_gw(self, vqip = None):
        if vqip is not None:
            vqip = self.copy_vqip(vqip)
            vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
            for i in set(vqip.keys()) - set(['volume']):
                vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.gw_tank.get_avail(vqip)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        return reply
    

    def push_check_gw(self, vqip = None):
        if vqip is not None:
            vqip = self.copy_vqip(vqip)
            vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
            for i in set(vqip.keys()) - set(['volume']):
                vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.gw_tank.get_excess(vqip)
        reply['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        return reply
    
    def end_timestep(self):
        self.gw_tank.end_timestep()
