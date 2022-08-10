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

class Land(Node):
    def __init__(self, **kwargs):
        self.subsurface_residence_time = 2
        self.percolation_residence_time = 10
        self.surface_residence_time = 1
        
        
        self.irrigation_functions = [lambda : None]
        
        super().__init__(**kwargs)
        
        surfaces_ = kwargs['surfaces'].copy()
        surfaces = []
        for surface in surfaces_:
            surface['parent'] = self
            surfaces.append(getattr(sys.modules[__name__], surface['type'])(**surface))
            self.mass_balance_ds.append(surfaces[-1].ds)
            if isinstance(surfaces[-1], IrrigationSurface):
                self.irrigation_functions.append(surfaces[-1].irrigate)
            
            if isinstance(surfaces[-1], GardenSurface):
                self.push_check_handler[('Demand','Garden')] = surfaces[-1].calculate_irrigation_demand
                self.push_set_handler[('Demand','Garden')] = surfaces[-1].receive_irrigation_demand
        
        #Update handlers
        self.push_set_handler['default'] = self.push_set_deny
        self.push_check_handler['default'] = self.push_check_deny
        self.push_set_handler['Sewer'] = self.push_set_sewer
        
        
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
    
    def apply_irrigation(self):
        for f in self.irrigation_functions:
            f()
            
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
    
    def push_set_sewer(self, vqip):
        impervious_surfaces = []
        #TODO could move to be a parameter..
        #TODO currently just push to the first impervious surface... not sure if people will be having multiple impervious surfaces
        for surface in self.surfaces:
            if isinstance(surface.__class__, ImperviousSurface):
                vqip = self.surface.push_storage(vqip, force = True)
                break
        return vqip
    
    def get_data_input(self, var):
        return self.data_input_dict[(var, self.t)]
    
    def end_timestep(self):
        self.running_inflow_mb = self.empty_vqip()
        self.running_outflow_mb = self.empty_vqip()
        for tanks in self.surfaces + [self.surface_runoff, self.subsurface_runoff, self.percolation]:
            tanks.end_timestep()
            
        
        
class Surface(DecayTank):
    def __init__(self,
                 area = 0,
                 depth = 1,
                 decays = {},
                 parent = None,
                 **kwargs):
        self.depth = depth
        self.decays = area
        
        
        #TODO interception if I hate myself enough?
        capacity = area * depth
        #Parameters
        super().__init__(capacity = capacity,
                         area = area,
                         decays = decays,
                         parent = parent)
        self.__dict__.update(kwargs)
        self.capacity = self.depth * self.area   
        
        self.inflows = [self.atmospheric_deposition,
                        self.precipitation_deposition]
        self.processes = [lambda : (self.empty_vqip(), self.empty_vqip())]
        self.outflows = [lambda : (self.empty_vqip(), self.empty_vqip())]
        
        
    def run(self):
        
        for f in self.inflows + self.processes + self.outflows:
            in_, out_ = f()
            self.parent.running_inflow_mb = self.sum_vqip(self.parent.running_inflow_mb, in_)
            self.parent.running_outflow_mb = self.sum_vqip(self.parent.running_outflow_mb, out_)

        
    def get_data_input(self, var):
        return self.parent.get_data_input(var)
    
    def get_data_input_surface(self, var):
        return self.data_input_dict[(var, self.parent.t)]
    
    def dry_deposition_to_tank(self, vqip):
        _ = self.push_storage(vqip, force = True)
        
    def wet_deposition_to_tank(self, vqip):
        _ = self.push_storage(vqip, force = True)

    def atmospheric_deposition(self):
        #TODO double check units - is weight of N or weight of NHX/noy?
        nhx = self.get_data_input_surface('nhx-dry') * self.area
        noy = self.get_data_input_surface('noy-dry') * self.area
        srp = self.get_data_input_surface('srp-dry') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = noy
        vqip['phosphate'] = srp
        
        self.dry_deposition_to_tank(vqip)
        return (vqip, self.empty_vqip())
        
    def precipitation_deposition(self):
        #TODO double check units - is weight of N or weight of NHX/noy?
        nhx = self.get_data_input_surface('nhx-wet') * self.area
        noy = self.get_data_input_surface('noy-wet') * self.area
        srp = self.get_data_input_surface('srp-wet') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = noy
        vqip['phosphate'] = srp
        
        self.wet_deposition_to_tank(vqip)
        return (vqip, self.empty_vqip())
    
class ImperviousSurface(Surface):
    def __init__(self, **kwargs):
        self.pore_depth = 0 #Need a way to say 'depth means pore depth'
        kwargs['depth'] = kwargs['pore_depth'] # TODO Need better way to handle this
        
        #Default parameters 
        self.et0_to_e = 0.1 #Total evaporation (ignoring transpiration)
        self.pollutant_load = {x : 0.001 for x in constants.POLLUTANTS} #kg/m2/dt
        
        
        super().__init__(**kwargs)
        
        self.inflows.append(self.urban_deposition)
        self.inflows.append(self.precipitation_evaporation)
        
        self.outflows.append(self.push_to_sewers)
    
    def urban_deposition(self):
        pollution = self.copy_vqip(self.pollutant_load)
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
            net_precipitation['temperature'] = self.get_data_input('temperature')
            
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
        
        #Return empty mass balance because outflows are handled by parent
        return (self.empty_vqip(), self.empty_vqip())
    
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
        
        super().__init__(**kwargs)
        
        #Initiliase flows
        self.infiltration_excess = self.empty_vqip()
        self.subsurface_flow = self.empty_vqip()
        self.percolation = self.empty_vqip()
        self.tank_recharge = self.empty_vqip()
        self.evaporation = self.empty_vqip()
        self.precipitation = self.empty_vqip()
        
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
        temperature = self.get_data_input('temperature')
        
        #Apply infiltration
        infiltrated_precipitation = min(precipitation_depth, self.infiltration_capacity)
        #Seems like evap should be here but it shouldn't because it comes out if total_water_passing..<0
        infiltration_excess = max(precipitation_depth - infiltrated_precipitation, 0) 
        
        #Formulate in terms of (m) moisture deficit
        current_moisture_deficit_depth = self.get_cmd()
        
        #IHACRES equations
        evaporation = evaporation_depth * min(1, exp(2 * (1 - current_moisture_deficit_depth / self.wilting_point)))
        outflow = infiltrated_precipitation  * (1 - min(1, (current_moisture_deficit_depth / self.field_capacity) ** self.ihacres_p))
        
        #Can't evaporate more than available moisture
        evaporation = min(evaporation, precipitation_depth + self.get_smc())
        
        #Convert to volumes
        percolation = outflow * self.percolation_coefficient * self.area
        subsurface_flow = outflow * self.subsurface_coefficient * self.area
        tank_recharge = (infiltrated_precipitation - evaporation - outflow) * self.area
        infiltration_excess *= self.area
        evaporation *= self.area
        precipitation = precipitation_depth * self.area
        
        #Mix in tank to calculate pollutant concentrations
        total_water_passing_through_soil_tank = tank_recharge + subsurface_flow + percolation
        
        if total_water_passing_through_soil_tank > 0:
            total_water_passing_through_soil_tank = self.v_change_vqip(self.empty_vqip(), total_water_passing_through_soil_tank)
            total_water_passing_through_soil_tank['temperature'] = temperature
            _ = self.push_storage(total_water_passing_through_soil_tank, force = True)
            subsurface_flow = self.pull_storage({'volume': subsurface_flow})
            percolation = self.pull_storage({'volume':percolation})
        else:
            evap = self.evaporate(-total_water_passing_through_soil_tank)
            subsurface_flow = self.empty_vqip()
            percolation = self.empty_vqip()
            
            if abs(evap + infiltrated_precipitation * self.area - evaporation) > constants.FLOAT_ACCURACY:
                print('inaccurate evaporation calculation')
        
        #Convert to VQIPs
        infiltration_excess = self.v_change_vqip(self.empty_vqip(), infiltration_excess)
        infiltration_excess['temperature'] = temperature
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
        
        return (self.empty_vqip(), self.empty_vqip())
        
    
    def calculate_soil_temperature(self):
        auto = self.storage['temperature'] * self.soil_temp_w_prev
        air = self.get_data_input('temperature') * self.soil_temp_w_air
        self.storage['temperature'] = auto + air + self.soil_temp_cons
        
        return (self.empty_vqip(), self.empty_vqip())
    
    # def decay(self):
    #     pass
    
    

class GrowingSurface(PerviousSurface):
    def __init__(self, **kwargs):
        #TODO Automatic check that nitrate, ammonia, solids, phosphorus, phosphate are in POLLUTANTS
        
        #Crop factors (set when creating object)
        self.ET_depletion_factor = 0 #To do with water availability, p from FAOSTAT
        self.rooting_depth = 0 #maximum depth that plants can absorb, Zr from FAOSTAT
        kwargs['depth'] = kwargs['rooting_depth']
        
        #Nutrient pool parameters
        self.nutrient_parameters = {'fraction_dry_n_to_dissolved_inorganic' : 0.9,
                                    'degrhpar' : {'N' : 7 * 1e-5, 
                                                  'P' : 7 * 1e-6}, # [1/day] dimension = N & P
                                    'dishpar' : {'N' : 7 * 1e-5, 
                                                 'P' : 7 * 1e-6}, # [1/day] dimension = N & P
                                    'minfpar' : {'N' : 0.00013, 
                                                 'P' : 0.000003}, # [1/day] dimension = N & P
                                    'disfpar' : {'N' : 0.000003, 
                                                 'P' : 0.0000001}, # [1/day] dimension = N & P
                                    'immobdpar' : {'N' : 0.0056, 
                                                   'P' : 0.2866}, # [1/day] dimension = N & P
                                    'fraction_manure_to_dissolved_inorganic_nutrients' : {'N' : 0.5, 
                                                                                          'P' : 0.1}, # [-] dimension = N & P
                                    'fraction_residue_to_fast_nutrients' : {'N' : 0.1, 
                                                                            'P' : 0.1} # [-] dimension = N & P
        }        
        #Crop parameters
        self.crop_cover_max = 0.9 # [-] 0~1
        self.ground_cover_max = 0.3 # [-]
        self.crop_factor_stages = [0,0,0,0,0,0] #coefficient to do with ET, associated with stages
        self.crop_factor_stage_dates = [0, 50, 200, 300, 301, 365] #dates when crops are planted/growing/harvested
        
        #Soil moisture dependence parameters
        self.satact = 0.6 # [-] for calculating soil_moisture_dependence_factor
        self.thetaupp = 0.12 # [-] for calculating soil_moisture_dependence_factor
        self.thetalow = 0.08 # [-] for calculating soil_moisture_dependence_factor
        self.thetapow = 1 # [-] for calculating soil_moisture_dependence_factorself.satact = 0.6 # [-] for calculating soil_moisture_dependence_factor
    
        #Crop uptake parameters
        self.uptake1 = 15 # [g/m2/y] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake2 = 1 # [-] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake3 = 0.02 # [1/day] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake_PNratio = 1/7.2 # [-] P:N during crop uptake
        
        #Erosion parameters
        self.erodibility = 0.0025 # [g * d / (J * mm)]
        self.sreroexp = 1.2 # [-] surface runoff erosion exponent
        self.cohesion = 1 # [kPa]
        self.slope = 5 # [-] every 100
        self.srfilt = 0.95 # [-] ratio of eroded sediment left in surface runoff after filtration
        self.macrofilt = 0.1 # [-] ratio of eroded sediment left in subsurface flow after filtration
        
        #Denitrification parameters
        self.limpar = 0.7 # [-] above which denitrification begins
        self.exppar = 2.5 # [-] exponential parameter for soil_moisture_dependence_factor_exp calculation
        self.hsatINs = 1 # [mg/l] for calculation of half-saturation concentration dependence factor
        self.denpar = 0.015 # [-] denitrification rate coefficient
        
        #Adsorption parameters
        self.adosorption_nr_limit = 0.00001
        self.adsorption_nr_maxiter = 20
        self.kfr = 153.7 # [1/kg] freundlich adsorption isoterm
        self.nfr = 1/2.6 # [-] freundlich exponential coefficient
        self.kadsdes = 0.03 # [1/day] adsorption/desorption coefficient
        
        
        #Other soil parameters
        self.bulk_density = 1300 # [kg/m3]
        
        super().__init__(**kwargs)
        
        #If decays are defined for any modelled pollutants then remove that behaviour
        for pollutant in ['nitrate','ammonia','org-phosphorus','phosphate']:
            self.decays.pop(pollutant, None)
        
        
        #Infer basic sow/harvest calendar        
        self.harvest_sow_calendar = [0, self.sowing_day, self.harvest_day, self.harvest_day + 1, 365]
        self.ground_cover_stages = [0,0,self.ground_cover_max,0,0]
        self.crop_cover_stages = [0,0,self.crop_cover_max,0,0]
        
        #This is just based on googling when is autumn...
        if self.sowing_day > 265:
            self.autumn_sow = True
        else:
            self.autumn_sow = False
        
        #State variables
        self.days_after_sow = None
        self.crop_cover = 0
        self.ground_cover = 0
        self.crop_factor = 0
        self.et0_coefficient = 1
        #Calculate parameters based on capacity/wp
        self.total_available_water = (self.field_capacity - self.wilting_point) / self.area
        if self.total_available_water < 0:
            print('warning: TAW < 0...')
        self.readily_available_water = self.total_available_water * self.ET_depletion_factor
        
        self.nutrient_pool = NutrientPool(**self.nutrient_parameters)
        
        self.inflows.insert(0, self.calc_crop_cover)
        self.inflows.append(self.fertiliser)
        self.inflows.append(self.manure)
        self.inflows.append(self.residue)
        
        self.processes.append(self.calc_temperature_dependence_factor)
        self.processes.append(self.calc_soil_moisture_dependence_factor)
        self.processes.append(self.soil_pool_transformation)
        self.processes.append(self.calc_crop_uptake)
        
        #TODO possibly move these into nutrient pool
        self.processes.append(self.erosion)
        self.processes.append(self.denitrification)
        self.processes.append(self.adsorption)
    
    def pull_storage(self, vqip):
        #Pull from Tank by volume (taking pollutants in proportion)
        
        if self.storage['volume'] == 0:
            return self.empty_vqip()
        
        #Adjust based on available volume
        reply = min(vqip['volume'], self.storage['volume'])
        
        #Update reply to vqip (get concentration for non-nutrients)
        reply = self.v_change_vqip(self.storage, reply)
        
        #Update nutrient pool and get concentration for nutrients
        prop = reply['volume'] / self.storage['volume']
        nutrients = self.nutrient_pool.extract_dissolved(prop)
        
        #For now assume organic and inorganic N go to the same place to maintain mass balance
        #TODO Also ignores ammonia -> nitrate transformation within soil - it would be easy enough to use a generic decay for this
        reply['nitrate'] = nutrients['inorganic']['N'] * self.storage['nitrate'] / (self.storage['nitrate'] + self.storage['ammonia'])
        reply['ammonia'] = nutrients['inorganic']['N'] * self.storage['ammonia'] / (self.storage['nitrate'] + self.storage['ammonia'])
        reply['phosphate'] = nutrients['inorganic']['P']
        reply['org-phosphorus'] = nutrients['organic']['P']
        reply['org-nitrogen'] = nutrients['organic']['N']
        
        #Extract from storage
        self.storage = self.extract_vqip(self.storage, reply)
        
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
        #Calculate crop calendar and cover and adjust ET parameters

        doy = self.parent.t.dayofyear
        
        if self.parent.t.is_leap_year:
            if doy > 59:
                doy -= 1
            
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
        
        #Calculate relevant parameters
        self.crop_factor = self.quick_interp(doy, self.crop_factor_stage_dates, self.crop_factor_stages)
        if self.days_after_sow:
            #Move outside of this if, if you want nonzero crop/ground cover outside of season
            self.crop_cover = self.quick_interp(doy, self.harvest_sow_calendar, self.crop_cover_stages)
            self.ground_cover = self.quick_interp(doy, self.harvest_sow_calendar, self.ground_cover_stages)
        
        root_zone_depletion = self.get_cmd()
        if root_zone_depletion < self.readily_available_water :
            crop_water_stress_coefficient = 1
        else:
            crop_water_stress_coefficient = max(0, (self.total_available_water - root_zone_depletion) /\
                                                ((1 - self.ET_depletion_factor) * self.total_available_water))
        
        self.et0_coefficient = crop_water_stress_coefficient * self.crop_factor
        
        return (self.empty_vqip(), self.empty_vqip())
    
    
    
    def fertiliser(self):
        #TODO tidy up fertiliser/manure/residue/deposition once preprocessing is sorted
        #Distribute between surfaces
        nhx = self.get_data_input_surface('nhx-fertiliser') * self.area
        noy = self.get_data_input_surface('noy-fertiliser') * self.area
        srp = self.get_data_input_surface('srp-fertiliser') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = noy
        vqip['phosphate'] = srp
        
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_fertiliser(deposition)
        self.push_storage(vqip, force = True)
    
        return (vqip, self.empty_vqip())
    
    def manure(self):
        nhx = self.get_data_input_surface('nhx-manure') * self.area
        noy = self.get_data_input_surface('noy-manure') * self.area
        srp = self.get_data_input_surface('srp-manure') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = noy
        vqip['phosphate'] = srp
        
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_manure(deposition)
        self.push_storage(vqip, force = True)
    
        return (vqip, self.empty_vqip())
    
    def residue(self):
        nhx = self.get_data_input_surface('nhx-residue') * self.area
        noy = self.get_data_input_surface('noy-residue') * self.area
        srp = self.get_data_input_surface('srp-residue') * self.area
        
        vqip = self.empty_vqip()
        vqip['ammonia'] = nhx * self.nutrient_pool.fraction_residue_to_fast['N']
        vqip['nitrate'] = noy * self.nutrient_pool.fraction_residue_to_fast['N']
        vqip['org-nitrogen'] = (nhx + noy) * self.nutrient_pool.fraction_residue_to_humus['N']
        vqip['phosphate'] = srp * self.nutrient_pool.fraction_residue_to_fast['P']
        vqip['org-phosphorus'] = srp * self.nutrient_pool.fraction_residue_to_humus['P']
        
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_residue(deposition)
        self.push_storage(vqip, force = True)
    
        return (vqip, self.empty_vqip())
    
    def soil_pool_transformation(self):
        in_ = self.empty_vqip()
        out_ = self.empty_vqip()
        
        nitrate_proportion = self.storage['nitrate'] / (self.storage['nitrate'] + self.storage['ammonia'])
        
        increase_in_inorganic = self.nutrient_pool.soil_pool_transformation()
        if increase_in_inorganic['N'] > 0:
            in_['nitrate'] = increase_in_inorganic['N'] * nitrate_proportion
            in_['ammonia'] = increase_in_inorganic['N'] * (1 - nitrate_proportion)
            out_['org-nitrogen'] = increase_in_inorganic['N']
        else:
            out_['nitrate'] = -increase_in_inorganic['N'] * nitrate_proportion
            out_['ammonia'] = -increase_in_inorganic['N'] * (1 - nitrate_proportion)
            in_['org-nitrogen'] = -increase_in_inorganic['N']
        
        if increase_in_inorganic['P'] > 0:
            in_['phosphate'] = increase_in_inorganic['P']
            out_['org-phosphorus'] = increase_in_inorganic['P']
        else:
            out_['phosphate'] = increase_in_inorganic['P']
            in_['org-phosphorus'] = increase_in_inorganic['P']
        
        _ = self.push_storage(in_, force = True)
        
        out2_ = self.pull_pollutants(out_)
        if not self.compare_vqip(out_, out2_):
            print('nutrient pool not tracking soil tank')
        
        return (in_, out_)
    
    def calc_temperature_dependence_factor(self):
        #TODO parameterise/find sources for data (HYPE)
        if self.storage['temperature'] > 5:
            temperature_dependence_factor = 2 ** ((self.storage['temperature'] - 20) / 10)
        elif self.storage['temperature'] > 0:
            temperature_dependence_factor = self.storage['temperature'] / 5
        else:
            temperature_dependence_factor = 0
        self.nutrient_pool.temperature_dependence_factor = temperature_dependence_factor
        return (self.empty_vqip(), self.empty_vqip())
        
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
        return (self.empty_vqip(), self.empty_vqip())
    
    def calc_crop_uptake(self):
        #Initialise
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
            out_ = self.empty_vqip()
            
            # Assuming plants eat N and P as nitrate and phosphate
            out_['nitrate'] = crop_uptake['N'] 
            out_['phosphate'] = crop_uptake['P'] 
            
            out2_ = self.pull_pollutants(out_)
            if not self.compare_vqip(out_, out2_):
                print('nutrient pool not tracking soil tank')
                    
            return (self.empty_vqip(), out_)
        else:
            return (self.empty_vqip(), self.empty_vqip())
        
    def erosion(self):
        #TODO source parameters (HYPE)
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
            return (self.empty_vqip(), self.empty_vqip())
        
        #Eroding flow > 0
        #
        erodableP = self.nutrient_pool.get_erodable_P() / self.area * constants.KG_M2_TO_KG_KM2
        erodedP = erodedsed * (erodableP / (self.rooting_depth * constants.M_TO_KM) / (self.bulk_density * constants.KG_M3_TO_KG_KM3)) * enrichment # [kg/km2]
        
        #Convert top kg
        erodedP *= (self.area * constants.M2_TO_KM2) # [kg]
        erodedsed *= (self.area * constants.M2_TO_KM2) # [kg]
        
        
        surface_erodedP = self.srfilt * self.infiltration_excess['volume'] / total_flows * erodedP # [kg]
        surface_erodedsed = self.srfilt * self.infiltration_excess['volume'] / total_flows * erodedsed # [kg]
        
        subsurface_erodedP = self.macrofilt * self.subsurface_flow['volume'] / total_flows * erodedP # [kg]
        subsurface_erodedsed = self.macrofilt * self.subsurface_flow['volume'] / total_flows * erodedsed # [kg]
        
        percolation_erodedP = self.macrofilt * self.percolation['volume'] / total_flows * erodedP # [kg]
        percolation_erodedsed = self.macrofilt * self.percolation['volume'] / total_flows * erodedsed # [kg]
        
        
        in_ = self.empty_vqip()
        
        
        eff_erodedP = percolation_erodedP + surface_erodedP + subsurface_erodedP # [kg]
        if eff_erodedP > 0:
            org_removed, inorg_removed = self.nutrient_pool.erode_P(eff_erodedP)
            total_removed = inorg_removed + org_removed 
            
            if abs(total_removed - eff_erodedP) > constants.FLOAT_ACCURACY:
                print('weird nutrients')
                
            self.infiltration_excess['org-phosphorus'] += (surface_erodedP * org_removed / eff_erodedP)
            self.subsurface_flow['org-phosphorus'] += (subsurface_erodedP * org_removed / eff_erodedP)
            self.percolation['org-phosphorus'] += (percolation_erodedP * org_removed / eff_erodedP)
            
            #TODO Leon reckons this should all go to org-phosphorus - but little pain to update mass balance
            self.infiltration_excess['phosphate'] += (surface_erodedP * inorg_removed / eff_erodedP)
            self.subsurface_flow['phosphate'] += (subsurface_erodedP * inorg_removed / eff_erodedP)
            self.percolation['phosphate'] += (percolation_erodedP * inorg_removed / eff_erodedP)
            
            removed = self.empty_vqip()
            removed['org-phosphorus'] = org_removed
            removed['phosphate'] = inorg_removed
            removed_ = self.pull_pollutants(removed)
            
            if not self.compare_vqip(removed, removed_):
                print('nutrient pool not tracking soil tank')
            
        else:
            inorg_to_org_P = 0
            
        self.infiltration_excess['solids'] += surface_erodedsed
        self.subsurface_flow['solids'] += subsurface_erodedsed
        self.percolation['solids'] += percolation_erodedsed

        
        in_['solids'] = surface_erodedsed + subsurface_erodedsed + percolation_erodedsed
            
        return (in_, self.empty_vqip())
    
    def denitrification(self):
        soil_moisture_content = self.get_smc()
        if soil_moisture_content > self.field_capacity:
            denitrifying_soil_moisture_dependence = 1
        elif soil_moisture_content / self.field_capacity > self.limpar:
            denitrifying_soil_moisture_dependence = (((soil_moisture_content / self.field_capacity) - self.limpar) / (1 - self.limpar)) ** self.exppar
        else:
            denitrifying_soil_moisture_dependence = 0
            return (self.empty_vqip(), self.empty_vqip())
        
        #TODO should this be moved to NutrientPool
        din_conc = self.nutrient_pool.dissolved_inorganic_pool.storage['N'] / self.storage['volume'] # [kg/m3]
        din_conc *= constants.KG_M3_TO_MG_L
        half_saturation_concentration_dependence_factor = din_conc / (din_conc + self.hsatINs)
        
        denitrified_N = self.nutrient_pool.dissolved_inorganic_pool.storage['N'] *\
                            half_saturation_concentration_dependence_factor *\
                                denitrifying_soil_moisture_dependence *\
                                    self.nutrient_pool.temperature_dependence_factor *\
                                        self.denpar
        denitrified_request = self.nutrient_pool.get_empty_nutrient()
        denitrified_request['N'] = denitrified_N
        denitrified_N = self.nutrient_pool.dissolved_inorganic_pool.extract(denitrified_request)
        
        
        #Leon reckons this should leave the model (though I think technically some small amount goes to nitrite)
        out_ = self.empty_vqip()
        out_['nitrate'] = denitrified_N['N'] 
        
        out2_ = self.pull_pollutants(out_)
        if not self.compare_vqip(out_, out2_):
            print('nutrient pool not tracking soil tank')

        return (self.empty_vqip(), out_)
    
    def adsorption(self):
        #TODO should be in nutrient pool?
        limit = self.adosorption_nr_limit
        ad_de_P_pool = self.nutrient_pool.adsorbed_inorganic_pool.storage['P'] + self.nutrient_pool.dissolved_inorganic_pool.storage['P'] # [kg]
        ad_de_P_pool /= (self.area * constants.M2_TO_KM2) # [kg/km2]
        if ad_de_P_pool == 0:
            return (self.empty_vqip(), self.empty_vqip())
        
        soil_moisture_content = self.get_smc() * constants.M_TO_MM # [mm] (not sure why HYPE has this in mm but whatever)
        conc_sol = self.nutrient_pool.adsorbed_inorganic_pool.storage['P'] * constants.KG_TO_MG / (self.bulk_density * self.rooting_depth * self.area)# [mg P/kg soil]
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
            while (abs(fxn) > limit and j < self.adsorption_nr_maxiter) : # iteration to calculate equilibrium concentations
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
            request = self.nutrient_pool.get_empty_nutrient()
            
            #TODO not sure about this if statement, surely it would be triggered every time
            adsdes = (ad_P_equi_conc - conc_sol) * (1 - exp(-self.kadsdes)) # kinetic adsorption/desorption
            request['P'] = adsdes * self.bulk_density * self.rooting_depth * (self.area * constants.M2_TO_KM2) # [kg]
            if request['P'] > 0:
                adsorbed = self.nutrient_pool.dissolved_inorganic_pool.extract(request)
                if (adsorbed['P'] - request['P']) > constants.FLOAT_ACCURACY:
                    print('Warning: freundlich flow adjusted, was larger than pool')
                self.nutrient_pool.adsorbed_inorganic_pool.receive(adsorbed)
            else:
                request['P'] = -request['P']
                desorbed = self.nutrient_pool.adsorbed_inorganic_pool.extract(request)
                if (desorbed['P'] - request['P']) > constants.FLOAT_ACCURACY:
                    print('Warning: freundlich flow adjusted, was larger than pool')
                self.nutrient_pool.dissolved_inorganic_pool.receive(adsorbed)
        
        return (self.empty_vqip(), self.empty_vqip())
    
    def dry_deposition_to_tank(self, vqip):
        #Distribute between surfaces
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_dry_deposition(deposition)
        self.push_storage(vqip, force = True)
        
    def wet_deposition_to_tank(self, vqip):
        deposition = self.nutrient_pool.get_empty_nutrient()
        deposition['N'] = vqip['nitrate'] + vqip['ammonia']
        deposition['P'] = vqip['phosphate']
        self.nutrient_pool.allocate_wet_deposition(deposition)
        self.push_storage(vqip, force = True)
        
        
class IrrigationSurface(GrowingSurface):
    def __init__(self, **kwargs):
        self.irrigation_coefficient = 0.1 #proportion area irrigated * proportion of demand met
        
        super().__init__(**kwargs)
        
        # self.inflows.append(self.irrigation)
                
    def irrigate(self):
        if self.days_after_sow:
            irrigation_demand = max(self.evaporation['volume'] - self.precipitation['volume'], 0) * self.irrigation_coefficient
            if irrigation_demand > constants.FLOAT_ACCURACY:
                root_zone_depletion = self.get_cmd()
                if root_zone_depletion <= constants.FLOAT_ACCURACY:
                    #TODO this isn't in FAO... but seems sensible
                    irrigation_demand = 0
                    
                supplied = self.parent.pull_distributed({'volume' : irrigation_demand}, 
                                                         of_type = ['River',
                                                                    'Node',
                                                                    'Groundwater',
                                                                    'Reservoir'
                                                                    ])
                
                #update tank
                _ = self.push_storage(supplied, force = True)
                
                #update nutrient pools
                organic = {'N' : supplied['org-nitrogen'], 
                           'P' : supplied['org-phosphorus']}
                inorganic = {'N' : supplied['ammonia'] + supplied['nitrate'], 
                             'P' : supplied['phosphate']}
                self.nutrient_pool.allocate_organic_irrigation(organic)
                self.nutrient_pool.allocate_inorganic_irrigation(inorganic)


class GardenSurface(GrowingSurface):
    #TODO - probably a simplier version of this is useful, building just on pervioussurface
    def __init__(self, **kwargs):  
        super().__init__(**kwargs)
        
        
    def calculate_irrigation_demand(self,ignore_vqip):
        irrigation_demand = max(self.evaporation['volume'] - self.precipitation['volume'], 0)
        
        root_zone_depletion = self.get_cmd()
        if root_zone_depletion <= constants.FLOAT_ACCURACY:
            #TODO this isn't in FAO... but seems sensible
            irrigation_demand = 0
        
        reply = self.empty_vqip()
        reply['volume'] = irrigation_demand
        return reply
    def receive_irrigation_demand(self, vqip):
        #update tank
        return self.push_storage(vqip, force = True)
            