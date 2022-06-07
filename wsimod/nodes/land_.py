# -*- coding: utf-8 -*-
"""
Created on Fri May 20 08:58:58 2022

@author: Barney
"""
from wsimod.nodes.nodes import Node, Tank, DecayTank, QueueTank, ResidenceTank
from wsimod.nodes.nutrient_pool import NutrientPool
from wsimod.core import constants
from math import exp, log, log10, sin
from bisect import bisect_left
import sys

class Land_(Node):
    def __init__(self, **kwargs):
        self.subsurface_residence_time = 2
        self.percolation_residence_time = 10
        self.surface_residence_time = 1
        
        super().__init__(**kwargs)
        
        surfaces_ = kwargs['surfaces'].copy()
        surfaces = []
        for surface in surfaces_:
            surface['parent'] = self
            surfaces.append(getattr(sys.modules[__name__], surface['type'])(**surface))
            self.mass_balance_ds.append(surfaces[-1].ds)
        
        #Can also do as timearea if this seems dodge (that is how it is done in IHACRES)
        #TODO should these be decayresidencetanks?
        
        
        self.subsurface_runoff = ResidenceTank(residence_time = self.subsurface_residence_time, 
                                               capacity = constants.UNBOUNDED_CAPACITY)
        self.percolation = ResidenceTank(residence_time = self.percolation_residence_time,
                                         capacity = constants.UNBOUNDED_CAPACITY)
        self.surface_runoff = ResidenceTank(residence_time = self.surface_residence_time,
                                            capacity = constants.UNBOUNDED_CAPACITY)
        
        
        self.surfaces = surfaces
        
        self.running_inflow_mb = self.empty_vqip()
        self.running_outflow_mb = self.empty_vqip()
        
        self.mass_balance_in.append(lambda : self.running_inflow_mb)
        self.mass_balance_out.append(lambda : self.running_outflow_mb)
        self.mass_balance_ds.append(self.surface_runoff.ds)
        self.mass_balance_ds.append(self.subsurface_runoff.ds)
        self.mass_balance_ds.append(self.percolation.ds)
        
    def run(self):  
        for surface in self.surfaces:
            surface.run()
            
        #Apply residence time to percolation
        percolation = self.percolation.pull_outflow()
        
        #Distribute percolation
        reply = self.push_distributed(percolation, of_type = ['Groundwater'])
        
        if reply['volume'] > 0:
            #Update percolation 'tank'
            _ = self.percolation.push_storage(reply, force = True)
        
        #Apply residence time to subsurface/surface runoff
        surface_runoff = self.surface_runoff.pull_outflow()
        subsurface_runoff = self.subsurface_runoff.pull_outflow()
        
        #Total runoff
        total_runoff = self.sum_vqip(surface_runoff, subsurface_runoff)
        if total_runoff['volume'] > 0:
            reply = self.push_distributed(total_runoff, of_type = ['River','Node'])
            
            #Redistribute total_runoff not sent
            if reply['volume'] > 0:
                reply_surface = self.v_change_vqip(reply, reply['volume'] * surface_runoff['volume'] / total_runoff['volume'])
                reply_subsurface = self.v_change_vqip(reply, reply['volume'] * subsurface_runoff['volume'] / total_runoff['volume'])
                
                #Update surface/subsurface runoff 'tanks'
                if reply_surface['volume'] > 0:
                    self.surface_runoff.push_storage(reply_surface, force = True)
                if reply_subsurface['volume'] > 0:
                    self.subsurface_runoff.push_storage(reply_subsurface, force = True)
        
    def get_data_input(self, var):
        return self.data_input_dict[(var, self.t)]
    
    def end_timestep(self):
        self.running_inflow_mb = self.empty_vqip()
        self.running_outflow_mb = self.empty_vqip()
        for tanks in self.surfaces + [self.surface_runoff, self.subsurface_runoff, self.percolation]:
            tanks.end_timestep()
            
        
        
class Surface(DecayTank):
    def __init__(self, **kwargs):
        self.depth = 0
        self.decays = {} #generic decay parameters
        
        
        #TODO interception if I hate myself enough?
        
        #Parameters
        super().__init__(**kwargs)        
        
        self.capacity = self.depth * self.area   
        
        self.inflows = [self.atmospheric_deposition,
                        self.precipitation_deposition]
        self.processes = [lambda : None]
        self.outflows = [lambda : None]
        
    def run(self):
        
        for f in self.inflows:
            in_, out_ = f()
            self.parent.running_inflow_mb = self.sum_vqip(self.parent.running_inflow_mb, in_)
            self.parent.running_outflow_mb = self.sum_vqip(self.parent.running_outflow_mb, out_)
        
        for f in self.processes + self.outflows:
            f()
            
        
    def get_data_input(self, var):
        return self.parent.get_data_input(var)
    
    def dry_deposition_to_tank(self, vqip):
        _ = self.push_storage(vqip, force = True)
        
    def wet_deposition_to_tank(self, vqip):
        _ = self.push_storage(vqip, force = True)

    def atmospheric_deposition(self):
        #TODO double check units - is weight of N or weight of NHX/NOX?
        nhx = self.get_data_input('nhx-dry') * self.area
        nox = self.get_data_input('nox-dry') * self.area
        srp = self.get_data_input('srp-dry') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = nox
        vqip['phosphate'] = srp
        
        self.dry_deposition_to_tank(vqip)
        return (vqip, self.empty_vqip())
        
    def precipitation_deposition(self):
        #TODO double check units - is weight of N or weight of NHX/NOX?
        nhx = self.get_data_input('nhx-wet') * self.area
        nox = self.get_data_input('nox-wet') * self.area
        srp = self.get_data_input('srp-wet') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = nox
        vqip['phosphate'] = srp
        
        self.wet_deposition_to_tank(vqip)
        return (vqip, self.empty_vqip())
    
class ImperviousSurface(Surface):
    def __init__(self, **kwargs):
        self.pore_depth = 0 #Need a way to say 'depth means pore depth'
        kwargs['depth'] = kwargs['pore_depth'] # TODO Need better way to handle this
        
        #Default parameters 
        self.et0_to_e = 0.1 #Total evaporation (ignoring transpiration)
        self.deposition_dict = {x : 0.001 for x in constants.POLLUTANTS} #kg/m2/dt
        
        
        super().__init__(**kwargs)
        
        self.inflows.append(self.urban_deposition)
        self.inflows.append(self.precipitation_evaporation)
        
        self.outflows.append(self.push_to_sewers)
    
    def urban_deposition(self):
        pollution = self.copy_vqip(self.pollutant_dict)
        pollution['volume'] = 0
        _ = self.push_storage(pollution, force = True)
        
        return (pollution, self.empty_vqip())
    
    def precipitation_evaporation(self):
        precipitation_depth = self.get_data_input('precipitation')
        evaporation_depth = self.get_data_input('et0') * self.et0_to_e
        
        if precipitation_depth < evaporation_depth:
            net_precipitation = 0
            evaporation_from_pores = evaporation_depth - precipitation_depth
            evaporation_from_pores *= self.area
            evaporation_from_pores = self.evaporate(evaporation_from_pores)
            total_evaporation = evaporation_from_pores + precipitation_depth * self.area
        else:
            net_precipitation = precipitation_depth - evaporation_depth
            net_precipitation *= self.area
            net_precipitation = self.v_change_vqip(self.empty_vqip(), net_precipitation)
            _ = self.push_storage(net_precipitation, force = True)
            total_evaporation = evaporation_depth * self.area
        
        total_evaporation = self.v_change_vqip(self.empty_vqip(), total_evaporation)
        total_precipitation = self.v_change_vqip(self.empty_vqip(), precipitation_depth * self.area)
        
        return (total_precipitation, total_evaporation)
        
    
    def push_to_sewers(self):
        surface_runoff = self.pull_ponded()
        reply = self.parent.push_distributed(surface_runoff, of_type = ['Sewer'])
        _ = self.push_storage(reply, force = True)
        #TODO in cwsd_partition this is done with timearea
    
class PerviousSurface(Surface):
    def __init__(self, **kwargs):
        self.field_capacity = 0 #depth of water when water level is above this, recharge/percolation are generated
        self.wilting_point = 0 #Depth of tank when added to field capacity, water below this level is available for plants+evaporation but not drainage
        self.infiltration_capacity = 0 #depth of precipitation that can enter tank per timestep
        self.percolation_coefficient = 0 #proportion of water above field capacity that can goes to percolation
        self.et0_coefficient = 0.5 #proportion of et0 that goes to evapotranspiration
        self.ihacres_p = 0.5
        
        
        
        #TODO what should these params be?
        self.soil_temp_w_prev = 0.3 #previous timestep weighting
        self.soil_temp_w_air = 0.3 #air temperature weighting
        self.soil_temp_cons = 3 #deep soil temperature * weighting
        
        #IHACRES is a deficit not a tank, so doesn't really have a capacity in this way... and if it did.. it probably wouldn't be the sum of these
        kwargs['depth'] = kwargs['field_capacity'] + kwargs['wilting_point'] # TODO Need better way to handle this
        
        #Initiliase flows
        self.infiltration_excess = self.empty_vqip()
        self.subsurface_flow = self.empty_vqip()
        self.percolation = self.empty_vqip()
        self.tank_recharge = self.empty_vqip()
        self.evaporation = self.empty_vqip()
        self.precipitation = self.empty_vqip()
        
        
        super().__init__(**kwargs)
        
        self.subsurface_coefficient = 1 - self.percolation_coefficient #proportion of water above field capacity that can goes to subsurface flow
        
        self.inflows.append(self.ihacres) #work out runoff
        
        self.processes.append(self.calculate_soil_temperature) # Calculate soil temp + dependence factor
        # self.processes.append(self.decay) #apply generic decay (currently handled by decaytank at end of timestep)
        #TODO decaytank uses air temperature not soil temperature... probably need to just give it the decay function
        
        self.outflows.append(self.route)
    def get_cmd(self):
        #Depth of moisture deficit
        return self.get_excess()['volume'] / self.area
    
    def get_smc(self):
        #Depth of soil moisture
        return self.storage['volume'] / self.area
    
    def ihacres(self):
        #TODO saturation excess
        
        #Read data
        precipitation_depth = self.get_data_input('precipitation')
        evaporation_depth = self.get_data_input('et0') * self.et0_coefficient
        
        #Apply infiltration
        infiltrated_precipitation = min(precipitation_depth, self.infiltration_capacity)
        infiltration_excess = max(precipitation_depth - evaporation_depth - infiltrated_precipitation, 0)
        
        #Formulate in terms of (m) moisture deficit
        current_moisture_deficit_depth = self.get_cmd()
        
        #IHACRES equations
        evaporation = evaporation_depth * min(1, exp(2 * (1 - current_moisture_deficit_depth / self.wilting_point)))
        outflow = infiltrated_precipitation  * (1 - min(1, (current_moisture_deficit_depth / self.field_capacity) ** self.ihacres_p))
        
        #Convert to volumes
        percolation = outflow * self.percolation_coefficient * self.area
        subsurface_flow = outflow * self.subsurface_coefficient * self.area
        tank_recharge = (infiltrated_precipitation - evaporation - outflow) * self.area
        infiltration_excess *= self.area
        evaporation *= self.area
        precipitation = precipitation_depth * self.area
        
        #Mix in tank to calculate pollutant concentrations
        total_water_passing_through_soil_tank = tank_recharge + subsurface_flow + percolation
        total_water_passing_through_soil_tank = self.v_change_vqip(self.empty_vqip(), total_water_passing_through_soil_tank)
        _ = self.push_storage(total_water_passing_through_soil_tank, force = True)
        subsurface_flow = self.pull_storage({'volume': subsurface_flow})
        percolation = self.pull_storage({'volume':percolation})
        
        #Convert to VQIPs
        infiltration_excess = self.v_change_vqip(self.empty_vqip(), infiltration_excess)
        precipitation = self.v_change_vqip(self.empty_vqip(), precipitation)
        evaporation = self.v_change_vqip(self.empty_vqip(), evaporation)
        
        #Track flows
        self.infiltration_excess = infiltration_excess
        self.subsurface_flow = subsurface_flow
        self.percolation = percolation
        self.tank_recharge = tank_recharge
        self.evaporation = evaporation
        self.precipitation = precipitation
        
        #Mass balance
        in_ = precipitation
        out_ = evaporation
        
        return (in_, out_)
    
    def route(self):
        #Send water 
        self.parent.surface_runoff.push_storage(self.infiltration_excess, force = True)
        self.parent.subsurface_runoff.push_storage(self.subsurface_flow, force = True)
        self.parent.percolation.push_storage(self.percolation, force = True)
        
    
    def calculate_soil_temperature(self):
        auto = self.storage['temperature'] * self.soil_temp_w_prev
        air = self.get_data_input('temperature') * self.soil_temp_w_air
        self.storage['temperature'] = auto + air + self.soil_temp_cons
    
    # def decay(self):
    #     pass
    
    

class CropSurface(PerviousSurface):
    def __init__(self, **kwargs):
        #TODO Check that nitrate, ammonia, solids, phosphorus, phosphate are in POLLUTANTS
        
        self.ET_depletion_factor = 0 #To do with water availability, p from FAOSTAT
        self.rooting_depth = 0 #maximum depth that plants can absorb, Zr from FAOSTAT
        kwargs['depth'] = kwargs['rooting_depth']
        
        self.fraction_dry_deposition_to_DIN = 0.9 #TODO may or may not be handled in preprocessing
        self.nutrient_parameters = {}
        
        #Parameters (TODO source and check units)
        self.satact = 0.6
        
        self.tawfract_p = 0.5 # Fraction of TAW that a crop can extract from the root zone without suffering water stress
        
        self.thetaupp = 0.12 # [-] for calculating soil_moisture_dependence_factor
        self.thetalow = 0.08 # [-] for calculating soil_moisture_dependence_factor
        self.thetapow = 1 # [-] for calculating soil_moisture_dependence_factor
        
        self.uptake1 = 15 # [g/m2/y] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake2 = 1 # [-] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake3 = 0.02 # [1/day] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake_PNratio = 1/7.2 # [-] P:N during crop uptake
        
        self.erodibility = 0.0025 # [g * d / (J * mm)]
        self.sreroexp = 1.2 # [-] surface runoff erosion exponent
        self.cohesion = 1 # [kPa]
        self.slope = 5 # [-] every 100
        self.srfilt = 0.95 # [-] ratio of eroded sediment left in surface runoff after filtration
        self.macrofilt = 0.1 # [-] ratio of eroded sediment left in subsurface flow after filtration
        
        self.limpar = 0.7 # [-] above which denitrification begins
        self.exppar = 2.5 # [-] exponential parameter for soil_moisture_dependence_factor_exp calculation
        self.hsatINs = 1 # [mg/l] for calculation of half-saturation concentration dependence factor
        self.denpar = 0.015 # [-] denitrification rate coefficient
        
        self.adosorption_nr_limit = 0.00001
        
        #TODO check units (WIMS is based on mg/l of N)
        self.nh3_no3_ratio = 1/10 # [-] NH3:NO3 ratio for soil water abstractions of N in nutrient pool (averaged from WIMS)
        
        self.crop_factor_stages = [0,0,0,0,0,0] #coefficient to do with ET, associated with stages
        self.crop_factor_stage_dates = [0, 50, 200, 300, 301, 365] #dates when crops are planted/growing/harvested
        
        self.crop_cover_max = 0.9 # [-] 0~1
        self.ground_cover_max = 0.3 # [-]
        
        super().__init__(**kwargs)
        
        #Infer basic sow/harvest calendar
        #TODO It might be easier to infer everything - but could be risky if people want to change calendars on the fly
        self.harvest_day = self.crop_factor_stage_dates[-3]
        self.sow_day = self.crop_factor_stage_dates[1]
        self.harvest_sow_calendar = [0, self.sow_day, self.harvest_day, self.harvest_day + 1, 365]
        self.ground_cover_stages = [0,0,self.ground_cover_max,0,0]
        self.crop_cover_stages = [0,0,self.crop_cover_max,0,0]
        
        #State variables
        self.days_after_sow = None
        self.crop_cover = 0
        self.ground_cover = 0
        self.crop_factor = 0
        
        self.total_available_water = self.field_capacity - self.wilting_point
        if self.total_available_water < 0:
            print('warning: TAW < 0...')
        
        self.nutrient_pool = NutrientPool(**self.nutrient_parameters)
        self.fraction_dry_deposition_to_fast = 1 - self.fraction_dry_deposition_to_DIN
        self.inflows.insert(0, self.calc_crop_cover)
        self.inflows.append(self.fertiliser)
        self.inflows.append(self.manure)
        
        self.processes.append(self.calc_temperature_dependence_factor)
        self.processes.append(self.calc_soil_moisture_dependence_factor)
        self.processes.append(self.nutrient_pool.soil_pool_transformation)
        self.processes.append(self.calc_crop_uptake)
        
        #TODO possibly move these into nutrient pool
        self.processes.append(self.erosion)
        self.processes.append(self.denitrification)
        self.processes.append(self.adsorption)
    
    
    
    def pull_storage(self, vqip):
        #Pull from Tank
        
        if self.storage['volume'] == 0:
            #TODO people may want to pull pollutants and no volume from storage..
            return self.empty_vqip()
        
        #Adjust based on available volume
        reply = min(vqip['volume'], self.storage['volume'])
        
        
        # Edit BD 2022-05-03 - should be no longer needed after change to total-based
        # if (self.storage['volume'] - reply) < self.unavailable_to_evap:
        #     reply = max(reply - self.unavailable_to_evap, 0)
        
        #Update reply to vqip (get concentration for non-nutrients)
        reply = self.v_change_vqip(self.storage, reply)
        
        #Update nutrient pool and get concentration for nutrients
        prop = reply['volume'] / self.storage['volume']
        nutrients = self.nutrient_pool.extract_dissolved(prop)
        
        #Extract from storage
        self.storage = self.extract_vqip(self.storage, reply)
        
        #For now assume organic and inorganic N go to the same place to maintain mass balance
        total_N = nutrients['inorganic']['N'] + nutrients['organic']['N']
        reply['nitrate'] = total_N * (1 - self.nh3_no3_ratio)
        reply['ammonia'] = total_N * self.nh3_no3_ratio
        reply['phosphate'] = nutrients['inorganic']['P']
        reply['phosphorus'] = nutrients['organic']['P']
        
        return reply
    
    def quick_interp(self, x, xp, yp):
        #Restrained version of np.interp
        x_ind = bisect_left(xp, x)
        x_left = xp[x_ind - 1]
        x_right = xp[x_ind]
        dif = x - x_left
        y_left = yp[x_ind - 1]
        y_right = yp[x_ind]
        y = y_left + (y_right - y_left) * dif / (x_right - x_left)
        return y
    
    def calc_crop_cover(self):
        #Calculate crop calendar and cover
        #TODO leap year? Or cba?
        doy = self.t.dayofyear
        
        if self.days_after_sow is None:
            if self.parent.t.dayofyear == self.sowing_day:
                self.days_after_sow = 0
        else:
            if self.parent.t.dayofyear == self.harvest_day:
                self.days_after_sow = None
                self.crop_factor = self.crop_factor_stages[0]
                self.crop_cover = 0
                self.ground_cover = 0
            else:
                self.days_after_sow += 1
        self.crop_factor = self.quick_interp(doy, self.crop_stage_dates, self.crop_factor_stages)
        if self.days_after_sow:
            #Move outside of this if, if you want nonzero crop/ground cover outside of season
            self.crop_cover = self.quick_interp(doy, self.harvest_sow_calendar, self.crop_cover_stages)
            self.ground_cover = self.quick_interp(doy, self.harvest_sow_calendar, self.ground_cover_stages)
                
    def fertiliser(self):
        pass
    
    def manure(self):
        pass
    
    def calc_temperature_dependence_factor(self):
        #TODO parameterise/find sources for data (HYPE)
        if self.storage['temperature'] > 5:
            temperature_dependence_factor = 2 ** ((self.storage['temperature'] - 20) / 10)
        elif self.storage['temperature'] > 0:
            temperature_dependence_factor = self.storage['temperature'] / 5
        else:
            temperature_dependence_factor = 0
        self.nutrient_pool.temperature_dependence_factor = temperature_dependence_factor
    
    def calc_soil_moisture_dependence_factor(self):        
        #TODO parameterise/find sources for data (HYPE)
        current_soil_moisture = self.get_smc()
        if current_soil_moisture  >= self.field_capacity: 
            self.nutrient_pool.soil_moisture_dependence_factor = self.satact
        elif current_soil_moisture <= self.wilting_point: 
            self.nutrient_pool.soil_moisture_dependence_factor = 0
        else:
            fc_diff = self.field_capacity - current_soil_moisture
            fc_comp = (fc_diff / (self.thetaupp * self.rooting_depth)) ** self.thetapow
            fc_comp = (1 - self.satact) * fc_comp + self.satact
            wp_diff = current_soil_moisture - self.wilting_point
            wp_comp = (wp_diff / (self.thetalow * self.rooting_depth)) ** self.thetapow
            self.nutrient_pool.soil_moisture_dependence_factor = min(1, wp_comp, fc_comp)

    def calc_crop_uptake(self):
        #TODO insert parameters and convert to kg/m2/dt
        #Initialise N_common_uptake
        N_common_uptake = 0
        P_common_uptake = 0
        
        if self.days_after_sow:
            days_after_sow = self.days_after_sow
            
            if self.autumn_sow:
                temp_func = max(0, min(1, (self.storage['temperature'] - 5) / 20))
                days_after_sow -= 25 #Not sure why this is
            else:
                temp_func = 1
            
            #Calculate uptake
            uptake_par = (self.uptake1 - self.uptake2) * exp(-self.uptake3 * days_after_sow) * temp_func
            if (uptake_par + self.uptake2) > 0 :
                N_common_uptake = self.uptake1 * self.uptake2 * self.uptake3 * uptake_par / ((self.uptake2 + uptake_par) ** 2)
            N_common_uptake *= constants.G_M2_TO_KG_M2
            P_common_uptake = N_common_uptake * self.uptake_PNratio
            uptake = {'P' : P_common_uptake,
                      'N' : N_common_uptake}
            crop_uptake = self.nutrient_pool.dissolved_inorganic_pool.extract(uptake)
            #TODO - I guess these nutrients just leave the model? If so need to mass include in balance
            #LEON CONFIRMED
    
    def erosion(self):
        #TODO source parameters
        precipitation_depth = self.get_data_input('precipitation') * constants.M_TO_MM
        if precipitation_depth > 5:
            rainfall_energy = 8.95 + 8.44 * log10(precipitation_depth * (0.257 + sin(2 * 3.14 * ((self.parent.t.dayofyear - 70) / 365)) * 0.09) * 2)
            rainfall_energy *= precipitation_depth
            mobilised_rain = rainfall_energy * (1 - self.crop_cover) * self.erodibility
        else:
            mobilised_rain = 0
        if self.infiltration_excess['volume'] > 0:
            mobilised_flow = (self.infiltration_excess['volume'] / self.area * constants.M_TO_MM * 365) ** self.sreroexp
            mobilised_flow *= (1 - self.ground_cover) * (1/(0.5 * self.cohesion)) * sin(self.slope / 100) / 365
        else:
            mobilised_flow = 0
        
        total_flows = self.infiltration_excess['volume'] + self.subsurface_flow['volume'] + self.percolation['volume'] #m3/dt + self.tank_recharge['volume'] (guess not needed)
        
        erodingflow = total_flows / self.area * constants.M_TO_MM
        transportfactor = min(1, (erodingflow / 4) ** 1.3)
        erodedsed = 1000 * (mobilised_flow +  mobilised_rain) * transportfactor # [kg/km2]
        #TODO not sure what conversion this HYPE 1000 is referring to
        
        # soil erosion with adsorbed inorganic phosphorus and humus phosphorus (erodedP as P in eroded sediments and effect of enrichment)
        if erodingflow > 4 :
            enrichment = 1.5
        elif erodingflow > 0:
            enrichment = 4 - (4 - 1.5) * erodingflow / 4
        else:
            return
        
        #Eroding flow > 0
        #
        erodableP = self.get_erodable_P() / self.area * constants.KG_M2_TO_KG_KM2
        erodedP = erodedsed * (erodableP / (self.rooting_depth * constants.M_TO_KM) / (self.bulk_density * constants.KG_M3_TO_KG_KM3)) * enrichment # [kg/km2]
        
        #Convert top kg
        erodedP *= (self.area * constants.M2_TO_KM2) # [kg]
        erodedsed *= (self.area * constants.M2_TO_KM2) # [kg]
        
        
        surface_erodedP = self.srfilt * self.infiltration_excess['volume'] / total_flows * erodedP # [kg]
        surface_erodedsed = self.srfilt * self.infiltration_excess['volume'] / total_flows * erodedsed # [kg]
        
        subsurface_erodedP = self.macrofilt * self.subsurface_flow['volume'] / total_flows * erodedP # [kg]
        subsurface_erodedsed = self.macrofilt * self.self.subsurface_flow['volume'] / total_flows * erodedsed # [kg]
        
        percolation_erodedP = self.macrofilt * self.percolation['volume'] / total_flows * erodedP # [kg]
        percolation_erodedsed = self.macrofilt * self.self.percolation['volume'] / total_flows * erodedsed # [kg]
        
        eff_erodedP = percolation_erodedP + surface_erodedP + subsurface_erodedP # [kg]
        
        reply = self.nutrient_pool.erode_P(eff_erodedP)
        ratio_satisfied = reply['P'] / eff_erodedP
        if ratio_satisfied != 1:
            print('weird nutrients')
        
        self.infiltration_excess['phosphorus'] += (surface_erodedP * ratio_satisfied)
        self.infiltration_excess['solids'] += surface_erodedsed
        self.subsurface_flow['phosphorus'] += (subsurface_erodedP * ratio_satisfied)
        self.subsurface_flow['solids'] += subsurface_erodedsed
        self.percolation['phosphorus'] += (percolation_erodedP * ratio_satisfied)
        self.percolation['solids'] += percolation_erodedsed
        
        #TODO mass balance - sediments entering here!
        
    def denitrification(self):
        soil_moisture_content = self.get_smc()
        if soil_moisture_content > self.field_capacity:
            denitrifying_soil_moisture_dependence = 1
        elif soil_moisture_content / self.field_capacity > self.limpar:
            denitrifying_soil_moisture_dependence = (((soil_moisture_content / self.field_capacity) - self.limpar) / (1 - self.limpar)) ** self.exppar
        else:
            denitrifying_soil_moisture_dependence = 0
            return
        
        #TODO should this be moved to NutrientPool
        din_conc = self.nutrient_pool.dissolved_inorganic_pool['N'] / self.storage['volume'] # [kg/m3]
        din_conc *= constants.KG_M3_TO_MG_L
        half_saturation_concentration_dependence_factor = din_conc / (din_conc + self.hsatINs)
        
        denitrified_N = self.nutrient_pool.dissolved_inorganic_pool['N'] *\
                            half_saturation_concentration_dependence_factor *\
                                denitrifying_soil_moisture_dependence *\
                                    self.nutrient_pool.temperature_dependence_factor *\
                                        self.denpar
        denitrified_request = self.nutrient_pool.empty_nutrient()
        denitrified_request['N'] = denitrified_N
        denitrified_N = self.nutrient_pool.dissolved_inorganic_pool.extract(denitrified_request)
        #TODO mass balance - this either leaves the model, goes to nitrite or some mix
        
    def adsorption(self):
        limit = self.adosorption_nr_limit
        ad_de_P_pool = self.nutrient_pool.adsorbed_inorganic_pool['P'] + self.nutrient_pool.dissolved_inorganic_pool['P'] # [kg]
        ad_de_P_pool /= (self.area * constants.M2_TO_KM2) # [kg/km2]
        if ad_de_P_pool == 0:
            return
        
        soil_moisture_content = self.get_smc() * constants.M_TO_MM # [mm] (not sure why HYPE has this in mm but whatever)
        conc_sol = self.nutrient_pool.adsorbed_inorganic_pool['P'] * constants.KG_TO_MG / (self.bulk_density * self.rooting_depth * self.area)# [mg P/kg soil]
        coeff = self.kfr * self.bulk_density * self.rooting_depth # [mm]
        
        # calculate equilibrium concentration
        if conc_sol <= 0 :
            #Not sure how this would happen
            print('Warning: soil partP <=0. Freundlich will give error, take shortcut.')
            xn_1 = ad_de_P_pool / (soil_moisture_content + coeff) # [mg/l]
            ad_P_equi_conc = self.kfr * xn_1   # [mg/ kg]
        else:
            # Newton-Raphson method
            x0 = exp((log(conc_sol) - log(self.kfr)) / self.nfr) # initial guess of equilibrium liquid concentration
            fxn = x0 * soil_moisture_content + coeff * (x0 ** self.nfr) - ad_de_P_pool
            xn = x0
            xn_1 = xn
            j = 0
            while (abs(fxn) > limit and j < 20) : # iteration to calculate equilibrium concentations
                fxn = xn * soil_moisture_content + coeff * (xn ** self.nfr) - ad_de_P_pool
                fprimxn = soil_moisture_content + self.nfr * coeff * (xn ** (self.nfr - 1))
                dx = fxn / fprimxn
                if abs(dx) < (0.000001 * xn):
                    #From HYPE... not sure what it means
                    break
                xn_1 = xn - dx
                if xn_1 <= 0 :
                    xn_1 = 1e-10
                xn = xn_1
                j += 1
            ad_P_equi_conc = self.kfr * (xn_1 ** self.nfr)
            #print(ad_P_equi_conc, conc_sol)
        
        # Calculate new pool and concentration, depends on the equilibrium concentration
        if abs(ad_P_equi_conc - conc_sol) > 1e-6 :
            request = self.nutrient_pool.empty_nutrient()
            
            #TODO not sure about this if statement, surely it would be triggered every time
            adsdes = (ad_P_equi_conc - conc_sol) * (1 - exp(-self.kadsdes)) # kinetic adsorption/desorption
            request['N'] = adsdes * self.bulk_density * self.rooting_depth * (self.area * constants.M2_TO_KM2) # [kg]
            if request['N'] > 0:
                adsorbed = self.nutrient_pool.dissolved_inorganic_pool.extract(request)
                if (adsorbed['N'] - request['N']) > constants.FLOAT_ACCURACY:
                    print('Warning: freundlich flow adjusted, was larger than pool')
                self.nutrient_pool.adsorbed_inorganic_pool.receive(adsorbed)
            else:
                request['N'] = -request['N']
                desorbed = self.nutrient_pool.adsorbed_inorganic_pool.extract(request)
                if (desorbed['N'] - request['N']) > constants.FLOAT_ACCURACY:
                    print('Warning: freundlich flow adjusted, was larger than pool')
                self.nutrient_pool.dissolved_inorganic_pool.receive(adsorbed)
    
    def dry_deposition_to_tank(self, vqip):
        #Distribute between surfaces
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_dry_deposition(deposition)
        
    def wet_deposition_to_tank(self, vqip):
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_wet_deposition(deposition)

    
class IrrigationSurface(CropSurface):
    def __init__(self, **kwargs):
        self.irrigation_cover = 0 #proportion area irrigated
        self.irrigation_efficiency = 0 #proportion of demand met
        
        super().__init__(**kwargs)
        
        self.inflows.append(self.calculate_irrigation)
        self.inflows.append(self.satisfy_irrigation)
        
        self.processes.append(self.crop_uptake)
        
    def calculate_irrigation(self):
        pass
    
    def crop_uptake(self):
        pass
    
    def satisfy_irrigation(self):
        pass

class GardenSurface(IrrigationSurface):
    #TODO - probably a simplier version of this is useful, building just on pervioussurface
    def __init__(self, **kwargs):
        self.satisfy_irrigation = self.pull_from_distribution
        
        super().__init__(**kwargs)
        
    def pull_from_distribution(self):
        pass