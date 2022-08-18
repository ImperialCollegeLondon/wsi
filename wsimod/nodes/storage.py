# -*- coding: utf-8 -*-
"""
Created on Mon Nov 15 14:20:36 2021

@author: bdobson
Converted to totals on 2022-05-03

"""
from wsimod.nodes.nodes import Node, Tank, QueueTank, DecayTank, DecayQueueTank
from wsimod.core import constants
from math import exp
class Storage(Node):
    #Basically a node wrapper for a tank

    def __init__(self, 
                        name,
                        capacity = 0,
                        area = 0,
                        datum =0,
                        decays = None,
                        initial_storage = 0,
                        ):
        
        self.initial_storage = initial_storage
        self.capacity = capacity
        self.area = area
        self.datum = datum
        self.decays = decays
        super().__init__(name)
        
        #Create tank
        if 'initial_storage' not in dir(self):
            self.initial_storage = self.empty_vqip()
        
        if self.decays is None:
            self.tank = Tank(capacity = self.capacity,
                                area = self.area,
                                datum = self.datum,
                                initial_storage = self.initial_storage,
                                )
        else:
            self.tank = DecayTank(capacity = self.capacity,
                                area = self.area,
                                datum = self.datum,
                                initial_storage = self.initial_storage,
                                decays = self.decays,
                                parent = self,
                                )
        #Update handlers
        self.push_set_handler['default'] = self.push_set_storage
        self.push_check_handler['default'] = self.tank.get_excess
        self.pull_set_handler['default'] = lambda vol : self.tank.pull_storage(vol)
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
    def __init__(self, 
                        residence_time = 200,
                        infiltration_threshold = 1,
                        infiltration_pct = 0,
                        data_input_dict = {},
                        **kwargs):
        self.residence_time = residence_time
        self.infiltration_threshold = infiltration_threshold # %/100 of capacity that node must be exceeding to generate infiltration
        self.infiltration_pct = infiltration_pct # %/100 of storage above threshold that is SQRTed and infiltrated
        self.data_input_dict = data_input_dict
        super().__init__(**kwargs)
        
    def distribute(self):
        avail = self.tank.get_avail()['volume'] / self.residence_time
        to_send = self.tank.pull_storage({'volume' : avail})
        retained = self.push_distributed(to_send, of_type = ['Node', 'River'])
        if retained['volume'] > constants.FLOAT_ACCURACY:
            print('Storage unable to push')
    
    def infiltrate(self):
        avail = self.tank.get_avail()['volume']
        avail = max(avail - self.tank.capacity * self.tank.infiltration_threshold, 0)
        avail = (avail * self.infiltration_pct) ** 0.5
        
        to_send = self.tank.pull_storage({'volume' : avail})
        retained = self.push_distributed(to_send, of_type = 'Sewer')

        if retained['volume'] > constants.FLOAT_ACCURACY:
            _ = self.tank.push_storage(retained, force = True)
    
class QueueGroundwater(Storage):
    #TODO - no infiltration as yet
    def __init__(self,
                        timearea = {0 : 1},
                        data_input_dict = {},
                        **kwargs):
        self.timearea = timearea
        self.data_input_dict = data_input_dict
        super().__init__(**kwargs)
        self.__class__.__name__ = 'Groundwater'
        self.push_set_handler['default'] = self.push_set_timearea
        self.pull_set_handler['default'] = self.pull_set_active
        self.pull_check_handler['default'] = self.pull_check_active
        if self.decays is None:
            #TODO... renaming storage to capacity here is confusing
            self.tank = QueueTank(capacity = self.capacity,
                                             area = self.area,
                                             datum = self.datum,
                                             initial_storage = self.initial_storage,
                                             )
        else:
            self.tank = DecayQueueTank(capacity = self.capacity,
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

class River(Storage):
    #TODO non-day timestep
    def __init__(self, 
                        depth = 2,
                        length = 200,
                        width = 20,
                        velocity = 0.2 * constants.M_S_TO_M_DT,
                        damp = 0.1,
                        **kwargs):
        self.depth = depth # [m]
        self.length = length # [m]
        self.width = width # [m]
        self.velocity = velocity # [m/dt]
        self.damp = damp # [>=0] flow delay and attenuation
        
        area = length * width # [m2]
        capacity = depth * area
        
        super().__init__(capacity = capacity,
                                area = area,
                                **kwargs)
        
        
        
        #TODO check units
        self.uptake_PNratio = 1/7.2 # [-] P:N during crop uptake
        self.bulk_density = 1300 # [kg/m3] soil density
        self.denpar_w = 0.0015#0.001, # [kg/m2/day] reference denitrification rate in water course
        self.T_wdays = 20 # [days] weighting constant for river temperature calculation (similar to moving average period)
        self.halfsatINwater = 1.5 * constants.MG_L_TO_KG_M3 # [kg/m3] half saturation parameter for denitrification in river
        self.T_10_days = [] # [degree C] average water temperature of 10 days
        self.T_20_days = [] # [degree C] average water temperature of 20 days
        self.TP_365_days = [] # [degree C] average water temperature of 20 days
        self.hsatTP = 0.05 * constants.MG_L_TO_KG_M3  # [kg/m3] 
        self.limpppar = 0.1 * constants.MG_L_TO_KG_M3  # [kg/m3]
        self.prodNpar = 0.001 # [kg N/m3/day] nitrogen production/mineralisation rate
        self.prodPpar = 0.0001 # [kg N/m3/day] phosphorus production/mineralisation rate
        self.muptNpar = 0.001 # [kg/m2/day] nitrogen macrophyte uptake rate
        self.muptPpar = 0.0001#0.01, # [kg/m2/day] phosphorus macrophyte uptake rate
        self.qbank_365_days = [1e6, 1e6] # [m3/day] store outflow in the previous year
        self.qbank = 1e6 # [m3/day] bankfull flow = second largest outflow in the previous year
        self.qbankcorrpar = 0.001 # [-] correction coefficient for qbank flow
        self.sedexppar = 1 # [-]
        self.EPC0 = 0.05 * constants.MG_L_TO_KG_M3 # [mg/l]
        self.kd_s = 0 * constants.MG_L_TO_KG_M3 #6 * 1e-6, # [kg/m3]
        self.kadsdes_s = 2#0.9, # [-]
        self.Dsed = 0.2 # [m]
        
        self.max_temp_lag = 20
        self.lagged_temperatures = []
        
        self.max_phosphorus_lag = 365
        self.lagged_total_phosphorus = []
        
        self.din_components = ['ammonia','nitrate'] # TODO need a cleaner way to do this depending on whether e.g., nitrite is included
        
        # Initialise paramters
        self.current_depth = 0 # [m]
        # self.river_temperature = 0 # [degree C]
        # self.river_denitrification = 0 # [kg/day]
        # self.macrophyte_uptake_N = 0 # [kg/day]
        # self.macrophyte_uptake_P = 0 # [kg/day]
        # self.sediment_particulate_phosphorus_pool = 60000 # [kg]
        # self.sediment_pool = 1000000 # [kg]
        # self.benthos_source_sink = 0 # [kg/day]
        # self.t_res = 0 # [day]
        # self.outflow = self.empty_vqip()
        
        #Update end_teimstep
        self.end_timestep = self.end_timestep_
        
        #Update handlers
        self.pull_check_handler[('RiparianBuffer', 'volume')] = self.pull_check_fp
        self.push_set_handler['default'] = self.push_set_river
        self.push_check_handler['default'] = lambda x : self.push_check_basic(x, of_type = ['Node', 'River', 'Waste'])
        
        #Update mass balance
        self.bio_in = self.empty_vqip()
        self.bio_out = self.empty_vqip()
        
        self.mass_balance_in.append(lambda : self.bio_in)
        self.mass_balance_out.append(lambda : self.bio_out)
    
    
    #TODO something like this might be needed if you want sewers backing up from river height... would need to incorporate expected river outflow
    # def get_dt_excess(self, vqip = None):
    #     reply = self.empty_vqip()
    #     reply['volume'] = self.tank.get_excess()['volume'] + self.tank.get_avail()['volume'] * self.get_riverrc()
    #     if vqip is not None:
    #         reply['volume'] = min(vqip['volume'], reply['volume'])
    #     return reply
    
    # def push_set_river(self, vqip):
    #     vqip_ = vqip.copy()
    #     vqip_ = self.v_change_vqip(vqip_, min(vqip_['volume'], self.get_dt_excess()['volume']))
    #     _ = self.tank.push_storage(vqip_, force=True)
    #     return self.extract_vqip(vqip, vqip_)
    
    def push_set_river(self, vqip):
        _ = self.tank.push_storage(vqip, force = True)
        return self.empty_vqip()
        
    def update_depth(self):
        self.current_depth = self.tank.storage['volume'] / self.area
    
    def get_din_pool(self):
        return sum([self.tank.storage[x] for x in self.din_components]) #TODO + self.tank.storage['nitrite'] but nitrite might not be modelled... need some ways to address this
    
    def biochemical_processes(self):
        #TODO make more modular
        self.update_depth()
        #HYPE has a temperature equation that tends the tank storage to the mean... I'd sooner rely on decay or similar
        
        #Update lagged temperatures
        if len(self.lagged_temperatures) > self.max_temp_lag:
            del self.lagged_temperatures[0]
        self.lagged_temperatures.append(self.tank.storage['temperature'])
        
        #Update lagged total phosphorus
        if len(self.lagged_total_phosphorus) > self.max_phosphorus_lag:
            del self.lagged_total_phosphorus[0]
        total_phosphorus = self.tank.storage['phosphate'] + self.tank.storage['org-phosphorus']
        self.lagged_total_phosphorus.append(total_phosphorus)
        
        #Check if any water
        if self.tank.storage['volume'] < constants.FLOAT_ACCURACY:
            #Assume these only do something when there is water
            return (self.empty_vqip(), self.empty_vqip())
        
        if self.tank.storage['temperature'] <= 0 :
            #Seems that these things are only active when above freezing
            return (self.empty_vqip(), self.empty_vqip())
        
        #Denitrification
        tempfcn = 2 ** ((self.tank.storage['temperature'] - 20) / 10)
        if self.tank.storage['temperature'] < 5 :
            tempfcn *= (self.tank.storage['temperature'] / 5)
        
        din = self.get_din_pool()
        din_concentration = din / self.tank.storage['volume']
        confcn = din_concentration / (din_concentration + self.halfsatINwater) # [kg/m3]
        denitri_water = self.denpar_w * self.area * tempfcn * confcn # [kg/day] #TODO convert to per DT
        
        river_denitrification = min(denitri_water, 0.5 * din) # [kg/day] max 50% kan be denitrified
        din_ = (din - river_denitrification) # [kg]
        
        #Update mass balance
        in_ = self.empty_vqip()
        out_ = self.empty_vqip()
        if din > 0:
            for pol in self.din_components:
                #denitrification
                loss = (din - din_) / din * self.tank.storage[pol]
                out_[pol] += loss
                self.tank.storage[pol] -= loss
        
        din = self.get_din_pool()
        
        #Calculate moving averages 
        #TODO generalise
        temp_10_day = sum(self.lagged_temperatures[-10:]) / 10
        temp_20_day = sum(self.lagged_temperatures[-20:]) / 20
        total_phos_365_day = sum(self.lagged_total_phosphorus) / self.max_phosphorus_lag
        
        #Calculate coefficients
        tempfcn = (self.tank.storage['temperature']) / 20 * (temp_10_day - temp_20_day) / 5
        if (total_phos_365_day - self.limpppar + self.hsatTP) > 0:
            totalphosfcn = (total_phos_365_day - self.limpppar) / (total_phos_365_day - self.limpppar + self.hsatTP)
        else:
            totalphosfcn = 0
        
        #Mineralisation/production
        #TODO this feels like it could be much tidier
        minprodN = self.prodNpar * totalphosfcn * tempfcn * self.area * self.current_depth # [kg N/day]
        minprodP = self.prodPpar * totalphosfcn * tempfcn * self.area * self.current_depth * self.uptake_PNratio # [kg N/day]
        if minprodN > 0 : 
            #production (inorg -> org)
            minprodN = min(0.5 * din, minprodN) # only half pool can be used for production
            minprodP = min(0.5 * self.tank.storage['phosphate'], minprodP) # only half pool can be used for production
            
            #Update mass balance
            out_['phosphate'] = minprodP
            self.tank.storage['phosphate'] -= minprodP
            in_['org-phosphorus'] = minprodP
            self.tank.storage['org-phosphorus'] += minprodP
            if din > 0:
                for pol in self.din_components:
                    loss = minprodN * self.tank.storage[pol] / din
                    out_[pol] += loss
                    self.tank.storage[pol] -= loss
            
            in_['org-nitrogen'] = minprodN
            self.tank.storage['org-nitrogen'] += minprodN
            
        else:  
            #mineralisation (org -> inorg)
            minprodN = min(0.5 * self.tank.storage['org-nitrogen'], -minprodN)
            minprodP = min(0.5 * self.tank.storage['org-phosphorus'], -minprodP)
            
            #Update mass balance
            in_['phosphate'] = minprodP
            self.tank.storage['phosphate'] += minprodP
            out_['org-phosphorus'] = minprodP
            self.tank.storage['org-phosphorus'] -= minprodP
            if din > 0:
                for pol in self.din_components:
                    gain = minprodN * self.tank.storage[pol] / din
                    in_[pol] += gain
                    self.tank.storage[pol] += gain
            
            out_['org-nitrogen'] = minprodN
            self.tank.storage['org-nitrogen'] -= minprodN
            
        din = self.get_din_pool()
        
        # macrophyte uptake
        # temperature dependence factor
        tempfcn1 = (max(0, self.tank.storage['temperature']) / 20) ** 0.3
        tempfcn2 = (self.tank.storage['temperature'] - temp_20_day) / 5
        tempfcn = max(0, tempfcn1 * tempfcn2)
    
        macrouptN = self.muptNpar * tempfcn * self.area # [kg/day]
        macrophyte_uptake_N = min(0.5 * din, macrouptN)
        if din > 0:
            for pol in self.din_components:
                loss = macrophyte_uptake_N * self.tank.storage[pol] / din
                out_[pol] += loss
                self.tank.storage[pol] -= loss
       
        macrouptP = self.muptPpar * tempfcn * max(0, totalphosfcn) * self.area # [kg/day]
        macrophyte_uptake_P = min(0.5 * self.tank.storage['phosphate'], macrouptP) 
        out_['phosphate'] += macrophyte_uptake_P
        self.tank.storage['phosphate'] -= macrophyte_uptake_P
        
        #TODO
        #source/sink for benthos sediment P
        #suspension/resuspension
        return in_, out_
    
    def get_riverrc(self):
        total_time = self.length / self.velocity
        kt = self.damp * total_time # [day]
        if kt != 0 :
            riverrc = 1 - kt + kt * exp(-1 / kt) # [-]
        else:
            riverrc = 1
        return riverrc
    
    def distribute(self):
        if 'nitrate' in constants.POLLUTANTS:
            in_, out_ = self.biochemical_processes()
            self.bio_in = in_
            self.bio_out = out_
        
        
        outflow = self.tank.pull_storage({'volume' : self.tank.storage['volume'] * self.get_riverrc()})
        reply = self.push_distributed(outflow, of_type = ['River','Node','Waste'])
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('river cant push')
        
    def pull_check_fp(self, vqip = None):
        # update river depth
        self.update_depth()
        return self.current_depth, self.area, self.width, self.river_tank.storage
    
    def end_timestep_(self):
        self.tank.end_timestep()
        self.bio_in = self.empty_vqip()
        self.bio_out = self.empty_vqip()
    
class Abstraction(Storage):
    """
    With a river - abstractions must be placed at abstraction points
    They must have accumulated all upstream flows that are available for abstraction before being abstracted from
    Once abstracted from, they can then distribute
    """
    #TODO use this or subclass abstraction?
    def __init__(self, 
                        mrf =0,
                        **kwargs):
        super().__init__(**kwargs)
        self.mrf = mrf
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
    def __init__(self, environmental_flow = 0, **kwargs):

        #Parameters
        self.environmental_flow = environmental_flow
        super().__init__(**kwargs)
        
        #State variables
        self.total_environmental_satisfied = 0

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