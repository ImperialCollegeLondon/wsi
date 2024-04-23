# -*- coding: utf-8 -*-
"""
Created on Sun Dec 24 10:09:12 2023

@author: leyan
"""

from wsimod.nodes.storage import Storage
from wsimod.core import constants
from math import exp

class River_h(Storage):
    #TODO non-day timestep
    def __init__(self, 
                        depth = 2,
                        length = 200,
                        width = 20,
                        velocity = 0.2 * constants.M_S_TO_M_DT,
                        damp = 0.1,
                        mrf = 0,
                        denpar_w = 0.0015,
                        muptNpar = 0.001,
                        muptPpar = 0.0001,
                        **kwargs):
        """Node that contains extensive in-river biochemical processes

        Args:
            depth (float, optional): River tank depth. Defaults to 2.
            length (float, optional): River tank length. Defaults to 200.
            width (float, optional): River tank width. Defaults to 20.
            velocity (float, optional): River velocity (if someone wants to calculate 
                this on the fly that would also work). Defaults to 0.2*constants.M_S_TO_M_DT.
            damp (float, optional): Flow delay and attentuation parameter. Defaults 
                to 0.1.
            mrf (float, optional): Minimum required flow in river (volume per timestep), 
                can limit pulls made to the river. Defaults to 0.
        
        Functions intended to call in orchestration:
            distribute
            
        Key assumptions:
             - River is conceptualised as a water tank that receives flows from various 
                sources (e.g., runoffs from urban and rural land, baseflow from groundwater), 
                interacts with water infrastructure (e.g., abstraction for irrigation and 
                domestic supply, sewage and treated effluent discharge), and discharges 
                flows downstream. It has length and width as shape parameters, average 
                velocity to indicate flow speed and capacity to indicate the maximum storage limit.
             - Flows from different sources into rivers will fully mix. River tank is assumed to
                have delay and attenuation effects when generate outflows. These effects are 
                simulated based on the average velocity.
             - In-river biochemical processes are simulated as sources/sinks of nutrients
                in the river tank, including
                - denitrification (for nitrogen)
                - phytoplankton absorption/release (for nitrogen and phosphorus)
                - macrophyte uptake (for nitrogen and phosphorus)
                These processes are affected by river temperature.

        Input data and parameter requirements:
             - depth, length, width
                _Units_: m
             - velocity
                _Units_: m/day
             - damping coefficient
                _Units_: -
             - minimum required flow
                _Units_: m3/day
        """
        #Set parameters
        self.depth = depth # [m]
        self.length = length # [m]
        self.width = width # [m]
        self.velocity = velocity # [m/dt]
        self.damp = damp # [>=0] flow delay and attenuation
        self.mrf = mrf
        self.denpar_w = denpar_w  # [kg/m2/day] reference denitrification rate in water course
        self.muptNpar = muptNpar  # [kg/m2/day] nitrogen macrophyte uptake rate
        self.muptPpar = muptPpar # [kg/m2/day] phosphorus macrophyte uptake rate
        area = length * width # [m2]
        
        capacity = constants.UNBOUNDED_CAPACITY #TODO might be depth * area if flood indunation is going to be simulated
        
        #Required in cases where 'area' conflicts with length*width
        kwargs['area'] = area
        #Required in cases where 'capacity' conflicts with depth*area
        kwargs['capacity'] = capacity
        
        super().__init__(**kwargs)
        
        
        
        #TODO check units
        #TODO Will a user want to change any of these?
        #Wide variety of river parameters (from HYPE)
        self.uptake_PNratio = 1/7.2 # [-] P:N during crop uptake
        self.bulk_density = 1300 # [kg/m3] soil density
        # self.denpar_w = 0.0015#0.001, # [kg/m2/day] reference denitrification rate in water course
        self.T_wdays = 5 # [days] weighting constant for river temperature calculation (similar to moving average period)
        self.halfsatINwater = 1.5 * constants.MG_L_TO_KG_M3 # [kg/m3] half saturation parameter for denitrification in river
        self.T_10_days = [] # [degree C] average water temperature of 10 days
        self.T_20_days = [] # [degree C] average water temperature of 20 days
        self.TP_365_days = [] # [degree C] average water temperature of 20 days
        self.hsatTP = 0.05 * constants.MG_L_TO_KG_M3  # [kg/m3] 
        self.limpppar = 0.1 * constants.MG_L_TO_KG_M3  # [kg/m3]
        self.prodNpar = 0.001 # [kg N/m3/day] nitrogen production/mineralisation rate
        self.prodPpar = 0.0001 # [kg N/m3/day] phosphorus production/mineralisation rate
        # self.muptNpar = 0.001 # [kg/m2/day] nitrogen macrophyte uptake rate
        # self.muptPpar = 0.0001#0.01, # [kg/m2/day] phosphorus macrophyte uptake rate
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
        
        self.din_components = ['ammonia','nitrate'] 
        # TODO need a cleaner way to do this depending on whether e.g., nitrite is included
        
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
        self.push_set_handler['default'] = self.push_set_river
        self.push_check_handler['default'] = self.push_check_accept
        self.push_check_handler[('Groundwater_h', 'datum')] = self.push_check_datum
        self.push_check_handler[('Groundwater_h', 'length')] = self.push_check_length
        self.push_check_handler[('Groundwater_h', 'width')] = self.push_check_width
        self.pull_check_handler['default'] = self.pull_check_river
        self.pull_set_handler['default'] = self.pull_set_river

        #TODO - RiparianBuffer
        self.pull_check_handler[('RiparianBuffer', 'volume')] = self.pull_check_fp
        
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

    def pull_check_river(self, vqip = None):
        """Check amount of water that can be pulled from river tank and upstream

        Args:
            vqip (dict, optional): Maximum water required (only 'volume' is used) 

        Returns:
            avail (dict): A VQIP amount that can be pulled
        """
        
        #Get storage
        avail = self.tank.get_avail()
        
        #Check incoming
        upstream = self.get_connected(direction = 'pull', of_type =['River_h','Node'])
        avail['volume'] += upstream['avail']
        
        #convert mrf from volume/timestep to discrete value
        mrf = self.mrf / self.get_riverrc()

        #Apply mrf
        avail_vol = max(avail['volume'] - mrf, 0)
        if vqip is None:
            avail = self.v_change_vqip(avail, avail_vol)
        else:
            avail = self.v_change_vqip(avail, min(avail_vol,vqip['volume']))
        
        return avail

    def pull_set_river(self, vqip):
        """Pull from river tank and upstream, acknowledging MRF with pull_check

        Args:
            vqip (dict): A VQIP amount to pull (only volume key used)

        Returns:
            (dict): A VQIP amount that was pulled
        """
        #Calculate available pull
        avail = self.pull_check_river(vqip)
        
        #Take first from tank
        pulled = self.tank.pull_storage(avail)
        
        #Take remaining from upstream
        to_pull = {'volume' : avail['volume'] - pulled['volume']}
        pulled_ = self.pull_distributed(to_pull, of_type = ['River_h', 'Node'])
        
        reply = self.sum_vqip(pulled, pulled_)
        
        return reply
        

    def push_set_river(self, vqip):
        """Push to river tank, currently forced.

        Args:
            vqip (dict): A VQIP amount to push

        Returns:
            (dict): A VQIP amount that was not successfully received
        """
        _ = self.tank.push_storage(vqip, force = True)
        return self.empty_vqip()
        
    def update_depth(self):
        """Recalculate depth
        """
        self.current_depth = self.tank.storage['volume'] / self.area
    
    def get_din_pool(self):
        """Get total dissolved inorganic nitrogen from tank storage

        Returns:
            (float): total din
        """
        return sum([self.tank.storage[x] for x in self.din_components]) #TODO + self.tank.storage['nitrite'] but nitrite might not be modelled... need some ways to address this
    
    def biochemical_processes(self):
        """Runs all biochemical processes and updates pollutant amounts

        Returns:
            in_ (dict): A VQIP amount that represents total gain in pollutant amounts
            out_ (dict): A VQIP amount that represents total loss in pollutant amounts
        """
        #TODO make more modular
        self.update_depth()

        self.tank.storage['temperature'] = (1 - 1 / self.T_wdays) * self.tank.storage['temperature'] + (1 / self.T_wdays) * self.get_data_input('temperature')
        
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
        """Get river outflow coefficient (i.e., how much water leaves the tank in this 
        timestep)

        Returns:
            riverrc (float): outflow coeffficient
        """
        #Calculate travel time
        total_time = self.length / self.velocity
        #Apply damp
        kt = self.damp * total_time # [day]
        if kt != 0 :
            riverrc = 1 - kt + kt * exp(-1 / kt) # [-]
        else:
            riverrc = 1
        return riverrc
    
    def calculate_discharge(self):
        if 'nitrate' in constants.POLLUTANTS:
            #TODO clumsy
            #Run biochemical processes
            in_, out_ = self.biochemical_processes()
            #Mass balance
            self.bio_in = in_
            self.bio_out = out_
            
    def distribute(self):
        """Run biochemical processes, track mass balance, and distribute water
        """
        # self.calculate_discharge()
        #Get outflow
        outflow = self.tank.pull_storage({'volume' : self.tank.storage['volume'] * self.get_riverrc()})
        #Distribute outflow
        reply = self.push_distributed(outflow, of_type = ['River_h','Node','Waste'])
        _ = self.tank.push_storage(reply, force = True)
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('river cant push: {0}'.format(reply['volume']) + ' at '+self.name)
        ## river-groundwater exchange
        # query river elevation
        # list of arcs that connect with gw bodies
        _, arcs = self.get_direction_arcs(direction='push', of_type=['Groundwater_h'])
        # if there is only one arc to gw_h
        if len(arcs) == 1:
            arc = arcs[0]
            h = arc.send_push_check(tag=('River_h', 'head'))['volume'] # [m asl]
            c_riverbed = arc.send_push_check(tag=('River_h', 'c_riverbed'))['volume'] # [m]
            # calculate riverbed hydraulic conductance
            C_riverbed = c_riverbed * self.length * self.width # [m2/day]
            # calculate river-gw flux
            flux = C_riverbed * (self.datum - h) # [m3/day]
            if flux > 0:
                to_send = self.tank.pull_storage({'volume' : flux}) # vqip afterwards
                retained = self.push_distributed(to_send, of_type = ['Groundwater_h'])
                _ = self.tank.push_storage(retained, force = True)
                if retained['volume'] > constants.FLOAT_ACCURACY:
                    print('River to groundwater: river return flow unable to push into groundwater at '+self.name)
            # else: wait gw to discharge back
        # TODO may need consider when one river connects to multiple gws
        elif len(arcs) > 1:
            print('WARNING: '+self.name+' connects with more than one gw - cannot model this at this stage and please re-setup the model')
             
            
    def pull_check_fp(self, vqip = None):
        #TODO Pull checking for riparian buffer, needs updating
        # update river depth
        self.update_depth()
        return self.current_depth, self.area, self.width, self.river_tank.storage
    
    def push_check_datum(self, vqip = None):
        # TODO should revise arc.get_excess to consider information transfer not in vqip?
        """Return a pseudo vqip whose volume is self.datum
        """
        datum = self.empty_vqip()
        datum['volume'] = self.datum
        
        return datum
    
    def push_check_length(self, vqip = None):
        # TODO should revise arc.get_excess to consider information transfer not in vqip?
        """Return a pseudo vqip whose volume is self.length
        """
        length = self.empty_vqip()
        length['volume'] = self.length
        
        return length
    
    def push_check_width(self, vqip = None):
        # TODO should revise arc.get_excess to consider information transfer not in vqip?
        """Return a pseudo vqip whose volume is self.width
        """
        width = self.empty_vqip()
        width['volume'] = self.width
        
        return width
    
    def end_timestep_(self):
        """Update state variables
        """
        self.tank.end_timestep()
        self.bio_in = self.empty_vqip()
        self.bio_out = self.empty_vqip()
