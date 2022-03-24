# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 09:25:09 2021

@author: leyan
"""


from wsimod.nodes.nodes import Node
from wsimod.nodes.nodes import Tank
from wsimod.core import constants
import numpy as np
from copy import deepcopy
import math
def vqip_ml_to_m3(vqip):
    # for key in constants.ADDITIVE_POLLUTANTS:
    #     vqip[key] *= constants.MG_L_TO_KG_M3
    vqip['volume'] *= constants.ML_TO_M3
    return vqip
class River(Node):
    def __init__(self, **kwargs):
        # parameters requiring input
        self.width = 0 # [m]
        self.length = 0 # [m]
        self.damp = 0.1 # [>=0] flow delay and attenuation
        
        super().__init__(**kwargs)
        # Default parameters
        self.capacity = constants.UNBOUNDED_CAPACITY # [Ml]
        self.river_area = self.width * self.length # TODO [m2]
        self.river_datum = 0 # [m]
        self.velocity = 0.2 # [m/s]
        
        
        self.uptake_PNratio = 1/7.2 # [-] P:N during crop uptake
        self.bulk_density = 1300 # [kg/m3] soil density
        self.denpar_w = 0.0015#0.001, # [kg/m2/day] reference denitrification rate in water course
        self.T_wdays = 20 # [days] weighting constant for river temperature calculation (similar to moving average period)
        self.halfsatINwater = 1.5 # [mg/l] half saturation parameter for denitrification in river
        self.T_10_days = [] # [degree C] average water temperature of 10 days
        self.T_20_days = [] # [degree C] average water temperature of 20 days
        self.TP_365_days = [] # [degree C] average water temperature of 20 days
        self.hsatTP = 0.05 # [mg/l] 
        self.limpppar = 0.1 # [mg/l]
        self.prodNpar = 0.001 # [kg N/m3/day] nitrogen production/mineralisation rate
        self.prodPpar = 0.0001 # [kg N/m3/day] phosphorus production/mineralisation rate
        self.muptNpar = 0.001 # [kg/m2/day] nitrogen macrophyte uptake rate
        self.muptPpar = 0.0001#0.01, # [kg/m2/day] phosphorus macrophyte uptake rate
        self.qbank_365_days = [1000, 1000] # [Ml/day] store outflow in the previous year
        self.qbank = 1000 # [Ml/day] bankfull flow = second largest outflow in the previous year
        self.qbankcorrpar = 0.001 # [-] correction coefficient for qbank flow
        self.sedexppar = 1 # [-]
        self.EPC0 = 0.05 # [mg/l]
        self.kd_s = 0#6 * 1e-6, # [mg/l]
        self.kadsdes_s = 2#0.9, # [-]
        self.Dsed = 0.2 # [m]
        
        # Initialise paramters
        self.depth = 0 # [m]
        self.river_temperature = 0 # [degree C]
        self.river_denitrification = 0 # [kg/day]
        self.macrophyte_uptake_N = 0 # [kg/day]
        self.macrophyte_uptake_P = 0 # [kg/day]
        self.sediment_particulate_phosphorus_pool = 60000 # [kg]
        self.sediment_pool = 1000000 # [kg]
        self.benthos_source_sink = 0 # [kg/day]
        self.t_res = 0 # [day]
        self.outflow = self.empty_vqip() # [Ml]
        
        #Create tank
        self.river_tank = Tank(capacity = self.capacity,
                            area = self.river_area,
                            datum = self.river_datum
                            )
        
        #Update handlers
        self.push_set_handler['default'] = self.push_set_rw
        self.pull_set_handler['default'] = self.pull_set_rw
        self.push_check_handler['default'] = self.push_check_rw
        self.pull_check_handler['default'] = self.pull_check_rw
        self.pull_check_handler[('RiparianBuffer', 'volume')] = self.pull_check_fp
        
        #Mass balance
        self.mass_balance_ds.append(self.rw_tank_ds_)
        self.mass_balance_out.append(self.mass_balance_loss_processes)
        
    def rw_tank_ds_(self):
        ds = self.river_tank.ds() 
        # for key in constants.ADDITIVE_POLLUTANTS:
        #     ds[key] *= constants.MG_L_TO_KG_M3
        ds['volume'] *= constants.ML_TO_M3
        return ds
    def mass_balance_loss_processes(self):
        vq = self.empty_vqip()
        vq['DIN'] = self.river_denitrification + self.macrophyte_uptake_N + self.minprodN
        vq['DON'] = -self.minprodN
        vq['SRP'] = self.macrophyte_uptake_P + self.minprodP
        vq['PP'] = -self.minprodP
        vq['volume'] = constants.FLOAT_ACCURACY / 100
        vq = self.total_to_concentration(vq)
        return vq
    
    def get_hydroclimatic(self, mean_temperature):
        #!!! read reference ET
        self.mean_temperature = mean_temperature # [degree C] require input
    
    def biochemical_processes(self):
        # manning's equation - assume wide rectangulaer channel (hydraulic radius ~ depth)
        #self.manning_coefficient = 0.035
        #self.river_slope = 0.0005
        #self.depth = (self.outflow['volume'] / constants.M3_S_TO_ML_D * self.manning_coefficient / ((self.river_slope ** 0.5) * self.width)) ** (3/5) # [m]
        self.depth = self.river_tank.storage['volume'] * constants.ML_TO_M3 / self.river_area # [m] 
        
        # water temperature
        self.river_temperature = (1 - 1/self.T_wdays) * self.river_temperature + 1/self.T_wdays * self.mean_temperature
        # denitrification - for dissolved inorganic nitrogen only - i.e. [0]
        # calculate temperature_dependence_factor
        tempfcn = 2 ** ((self.river_temperature - 20) / 10)
        if self.river_temperature < 5 :
            tempfcn *= (self.river_temperature / 5)
        if self.river_temperature < 0 :
            tempfcn = 0
        # calculate half_saturation_concentration_factor
        confcn = self.river_tank.storage['DIN'] / (self.river_tank.storage['DIN'] + self.halfsatINwater)
        denitri_water = self.denpar_w * self.river_area * tempfcn * confcn # [kg/day]
        river_DIN_pool = self.river_tank.storage['DIN'] * self.river_tank.storage['volume'] # [kg/day]
        self.river_denitrification = min(denitri_water, 0.5 * river_DIN_pool) # [kg/day] max 50% kan be denitrified
        self.river_tank.storage['DIN'] = (river_DIN_pool - self.river_denitrification) / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY) # [mg/l]
        # production & mineralisation
        # initiate in-river pools
        river_DIN_pool = self.river_tank.storage['DIN'] * self.river_tank.storage['volume'] # [kg/day]
        river_DON_pool = self.river_tank.storage['DON'] * self.river_tank.storage['volume'] # [kg/day]
        river_SRP_pool = self.river_tank.storage['SRP'] * self.river_tank.storage['volume'] # [kg/day]
        river_PP_pool = self.river_tank.storage['PP'] * self.river_tank.storage['volume'] # [kg/day]
        river_SS_pool = self.river_tank.storage['SS'] * self.river_tank.storage['volume'] # [kg/day]
        # calculate T_10_days & T_20_days & temperature dependence factor
        self.T_10_days.append(self.river_temperature)
        if len(self.T_10_days) > 10 :
            del(self.T_10_days[0])
        self.T_20_days.append(self.river_temperature)
        if len(self.T_20_days) > 20 :
            del(self.T_20_days[0])
        T_10 = np.array(self.T_10_days).mean()
        T_20 = np.array(self.T_20_days).mean()
        
        if self.river_temperature > 0 :
            tempfcn1 = self.river_temperature / 20
            tempfcn2 = (T_10 - T_20) / 5
            tempfcn = tempfcn1 * tempfcn2 # use the same tempfcn in denitrification as denitrification has already been calculated and won't be calculated again
            # TP concentration function
            self.TP_365_days.append(self.river_tank.storage['SRP'] + self.river_tank.storage['PP'])
            if len(self.TP_365_days) > 365 :
                del(self.TP_365_days[0])
            TP_365 = np.array(self.TP_365_days).mean()
            TPfcn = 0
            if (TP_365 - self.limpppar + self.hsatTP) > 0:
                TPfcn = (TP_365 - self.limpppar) / (TP_365 - self.limpppar + self.hsatTP)
            # minprodN
            self.minprodN = self.prodNpar * TPfcn * tempfcn * self.river_area * self.depth # [kg N/day]
            if self.minprodN > 0 : # production
                self.minprodN = min(0.5 * river_DIN_pool, self.minprodN) # only half pool can be used for production
            else: # mineralisation
                self.minprodN = max(-0.5 * river_DON_pool, self.minprodN)
            river_DIN_pool -= self.minprodN
            river_DON_pool += self.minprodN
            # minprodP
            self.minprodP = self.prodPpar * TPfcn * tempfcn * self.river_area * self.depth * self.uptake_PNratio # [kg N/day]
            if self.minprodP > 0 : # production
                self.minprodP = min(0.5 * river_SRP_pool, self.minprodP) # only half pool can be used for production
            else: # mineralisation
                self.minprodP = max(-0.5 * river_PP_pool, self.minprodP)
            river_SRP_pool -= self.minprodP
            river_PP_pool += self.minprodP
        
            # macrophyte uptake
            # temperature dependence factor
            tempfcn1 = (max(0, self.river_temperature) / 20) ** 0.3
            tempfcn2 = (self.river_temperature - T_20) / 5
            tempfcn = max(0, tempfcn1 * tempfcn2)
            
            macrouptN = self.muptNpar * tempfcn * self.river_area # [kg/day]
            self.macrophyte_uptake_N = min(0.5 * river_DIN_pool, macrouptN)
            river_DIN_pool -= self.macrophyte_uptake_N
            
            macrouptP = self.muptPpar * tempfcn * max(0, TPfcn) * self.river_area # [kg/day]
            self.macrophyte_uptake_P = min(0.5 * river_SRP_pool, macrouptP)
            river_SRP_pool -= self.macrophyte_uptake_P
            
            self.river_tank.storage['DIN'] = river_DIN_pool / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY/100)
            self.river_tank.storage['SRP'] = river_SRP_pool / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY/100)
            self.river_tank.storage['DON'] = river_DON_pool / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY/100)
            
        #
        # source/sink for benthos sediment P
        # Calculate new pool and concentration, depends on the equilibrium concentration
        ad_P_equi_conc = self.EPC0
        conc_wat = self.river_tank.storage['SRP']
        if abs(ad_P_equi_conc - conc_wat) > 1e-6 :
            #adsdes = self.kd_s * (conc_wat - ad_P_equi_conc) * (1 - math.exp(-self.kadsdes_s)) # kinetic adsorption/desorption
            adsdes = self.kd_s * (abs(conc_wat - ad_P_equi_conc)) ** self.kadsdes_s * (conc_wat - ad_P_equi_conc)/abs(conc_wat - ad_P_equi_conc)
            #t_res = self.length / (self.outflow * 1e6 / 1e3 / depth / self.width) # [day]
            t_res = 1
            self.t_res = t_res
            help_ = adsdes * self.bulk_density * self.Dsed * self.river_area * t_res # [kg] + = adsorption; - = desorption
            if help_ > 0:
                help_ = min(0.5 * river_SRP_pool, help_)
            else:
                help_ = -min(0.5 * self.sediment_particulate_phosphorus_pool, abs(help_))
            
            self.sediment_particulate_phosphorus_pool += help_
            river_SRP_pool -= help_
            self.benthos_source_sink = -help_  # [kg] + = source to water; - = sink to water
        
        self.river_tank.storage['SRP'] = river_SRP_pool / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY)
        
        # sedimentation-resuspension
        # bankfull flow
        # if self.day == 1 :
        #     self.qbank = self.qbank_365_days[-2]
        #     self.qbank_365_days = []
        # self.qbank_365_days.append(self.outflow) # [Ml/day]
        # if self.day >= 365 :
        #     self.qbank_365_days.sort()
            
        # qbankcorr = self.qbankcorrpar * self.qbank
        # help_ = 0
        # if qbankcorr > self.outflow :
        #     help_ += ((qbankcorr - self.outflow) / qbankcorr) ** self.sedexppar   # sedimentation at low flow
        # if self.outflow > 0 :
        #     help_ -=  (self.outflow / qbankcorr) ** self.sedexppar # resuspension at all flows
        # sedresp = max(-1, min(1, help_)) # [-]
        # if sedresp > 0 : # sedimentation
        #     transfer = sedresp * river_PP_pool # [kg]
        #     river_PP_pool -= transfer
        #     self.sediment_particulate_phosphorus_pool += transfer
        #     transfer = sedresp * river_SS_pool # [kg]
        #     river_SS_pool -= transfer
        #     self.sediment_pool += transfer
        # else: # resuspension
        #     transfer = -sedresp * self.sediment_particulate_phosphorus_pool
        #     self.sediment_particulate_phosphorus_pool -= transfer
        #     river_PP_pool += transfer
        #     transfer = -sedresp * self.sediment_pool
        #     self.sediment_pool -= transfer
        #     river_SS_pool += transfer
        
        self.river_tank.storage['SS'] = river_SS_pool / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY) # [mg/l]
        self.river_tank.storage['PP'] = river_PP_pool / max(self.river_tank.storage['volume'], constants.FLOAT_ACCURACY) # [mg/l]
    def get_flow_downstream(self):
        self.biochemical_processes()
        total_time = self.length / (self.velocity * constants.D_TO_S) # [day]
        kt = self.damp * total_time # [day]
        if kt != 0 :
            riverrc = 1 - kt + kt * math.exp(-1 / kt) # [-]
        else:
            riverrc = 1
        self.outflow = deepcopy(self.river_tank.storage)
        self.outflow['volume'] = self.river_tank.storage['volume'] * riverrc # [Ml/d]
        self.river_tank.storage['volume'] -= self.outflow['volume'] # TODO can use pull_storage()
        if self.river_tank.storage['volume'] < 0 :
            print('river storage is < 0')
        
        self.outflow['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(self.outflow.keys()) - set(['volume']):
            self.outflow[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        reply = self.push_distributed(self.outflow,
                                      of_type = ['River', 'Waste'])
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('River couldnt push')
    
    def pull_check_fp(self, vqip = None):
        # update river depth
        self.depth = self.river_tank.storage['volume'] * constants.ML_TO_M3 / self.river_area # [m] 
        return self.depth, self.river_area, self.width, self.river_tank.storage
    
    def pull_set_rw(self, vqip):
        vqip = self.copy_vqip(vqip)
        vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(vqip.keys()) - set(['volume']):
            vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.river_tank.pull_storage(vqip)
        reply = self.copy_vqip(reply)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        return reply
    
    def pull_check_rw(self, vqip = None):
        if vqip is not None:
            vqip = self.copy_vqip(vqip)
            vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
            for i in set(vqip.keys()) - set(['volume']):
                vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.river_tank.get_avail(vqip)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        return reply
    
    
    def push_set_rw(self, vqip):
        vqip = self.copy_vqip(vqip)
        vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(vqip.keys()) - set(['volume']):
            vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        reply = self.river_tank.push_storage(vqip)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        return reply
    
    def push_check_rw(self, vqip = None):
        if vqip is not None:
            vqip = self.copy_vqip(vqip)
            vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
            for i in set(vqip.keys()) - set(['volume']):
                vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
            
        reply = self.river_tank.get_excess(vqip)
        reply['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(reply.keys()) - set(['volume']):
            reply[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        return reply
    
    def end_timestep(self):
        self.river_tank.end_timestep()