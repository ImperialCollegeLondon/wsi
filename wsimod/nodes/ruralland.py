# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 09:18:58 2021

@author: leyan
"""


from wsimod.nodes.nodes import Node
from wsimod.nodes.nodes import Tank
from wsimod.core import constants

import time
import datetime
import math
import numpy as np
from copy import deepcopy

class RuralLand(Node):
    def __init__(self, **kwargs):
        # parameters required input
        self.no_HRUs = 0 # !!! input
        self.areas = [] # [km2] cannot include 0 !!! input
        self.rooting_depth = [] # [m] (FAO 56 (http://www.fao.org/docrep/X0490E/x0490e0e.htm)) !!! input
        self.crop_factor_stage1_4 = [] # [-] (FAO 56) initial stage, middle stage, end stage !!! input
        self.start_date_stage1_4 = [] # date %m-%d !!! input
        self.fertilisers = [{'N' : None, 'P' : None} for _ in range(self.no_HRUs)] # [kg (N/P)/km2/day] !!! requires input
        self.manure = [{'N' : None, 'P' : None} for _ in range(self.no_HRUs)] # [kg (N/P)/km2/day] !!! requires input
        self.harvest_date = [] # date %m-%d !!! input
        self.ET_depletion_factor = [] # mm !!! input
        self.irrigation_switch = [0 for _ in range(self.no_HRUs)] # [-] Irrigation behaviour coefficient - a switch between fallow period (off) and arable period (on)
        self.impervious_area = 0 # [km2] can be 0 !!! input
        
        self.field_capacity = [0.3 for _ in range(self.no_HRUs)] # [-] (FAO 56)
        self.runoff_coefficient = 0.3 # [-] ratio of net rainfall transformed into surface runoff
        self.recharge_coefficient = 0.7 # [-] ratio of net rainfall transformed into recharge
        self.percolation_coefficient = 0 # [-] ratio of net rainfall transformed into percolation ! these three should be summed as 1
        ## def routing()
        self.runoff_residence_time = 4 # [d]
        self.recharge_residence_time = 25 # [d]
        ## def soil_water()
        self.infiltration_capacity = 40#36, # [mm/day]
        self.interception = [0 for _ in range(self.no_HRUs)] # [0-1] ratio that is intercepted by canopy
        
        
        #Update args
        super().__init__(**kwargs)
        
        #Default parameters determined by input
        
        self.wilting_point = [0.12 for _ in range(self.no_HRUs)] # [-] (FAO 56)
        ## def irrigation_demand()
        self.day = None # [-] (0 - 365 or 366) day number for the date under calculation within the year
        self.fallow_period = [None for _ in range(self.no_HRUs)]
        self.stage_period = [None for _ in range(self.no_HRUs)]
        self.stage_period_pre = [None for _ in range(self.no_HRUs)]
        self.stage_lengths_pre = [None for _ in range(self.no_HRUs)]
        self.stage_lengths = [None for _ in range(self.no_HRUs)] # [-] should have the same format as 'start_date_stage1-4'
        self.stage_label = [None for _ in range(self.no_HRUs)] # [-] indicating which stage the crop is in
        self.crop_factor = [None for _ in range(self.no_HRUs)] # mm
        self.total_available_water = [None for _ in range(self.no_HRUs)] # mm
        self.readily_available_water = [None for _ in range(self.no_HRUs)] # mm
        self.crop_water_stress_coefficient = [None for _ in range(self.no_HRUs)] # [-]
        self.crop_cover = [0 for _ in range(self.no_HRUs)] # [-] 0~1
        self.ground_cover = [0 for _ in range(self.no_HRUs)] # [-] 0~1
        self.crop_cover_max = 0.9 # [-] 0~1
        self.ground_cover_max = 0.3 # [-]
        ## def irrigation_abstraction()
        self.irrigation_percentage_from_surfacewater = 0.29 # [-] 55%
        self.irrigation_percentage_from_groundwater = 0.71 # [-] 45%
        ## def atmospheric_deposition()
        self.fraction_dry_deposition_to_DIN = 0.9 # [-] DIN = dissolved inorganic nitrogen
        self.soil_moisture_content = [247 for _ in range(self.no_HRUs)] # [mm] for the soil layer 
        ## def fertilisers()
        self.fraction_manure_to_dissolved_inorganic_nutrients = {'N' : 0.5, 
                                                                 'P' : 0.1} # [-] dimension = N & P
        self.fraction_residue_to_fast_nutrients = {'N' : 0.1, 
                                                   'P' : 0.1} # [-] dimension = N & P
        ## def soil_pool_transformation()
        self.temperature_dependence_factor = 0 # [-] for calculating soil pool tranformation
        self.soil_moisture_dependence_factor = [None for _ in range(self.no_HRUs)] # [-] for calculating soil pool tranformation
        self.satact = 0.6 # [-] for calculating soil_moisture_dependence_factor
        self.thetaupp = 0.12 # [-] for calculating soil_moisture_dependence_factor
        self.thetalow = 0.08 # [-] for calculating soil_moisture_dependence_factor
        self.thetapow = 1 # [-] for calculating soil_moisture_dependence_factor
        self.degrhpar = {'N' : 7 * 1e-5, 
                         'P' : 7 * 1e-6} # [1/day] dimension = N & P
        self.dishpar = {'N' : 7 * 1e-5, 
                        'P' : 7 * 1e-6} # [1/day] dimension = N & P
        self.minfpar = {'N' : 0.00013, 
                        'P' : 0.000003} # [1/day] dimension = N & P
        self.disfpar = {'N' : 0.000003, 
                        'P' : 0.0000001} # [1/day] dimension = N & P
        self.immobdpar = {'N' : 0.0056, 
                          'P' : 0.2866} # [1/day] dimension = N & P
        ## def potential_crop_uptake()
        self.uptake1 = 15 # [g/m2/y] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake2 = 1 # [-] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.uptake3 = 0.02 # [1/day] shape factor for crop (Dissolved) Inorganic nitrogen uptake
        self.sow_day = [None for _ in range(self.no_HRUs)] # [-] day of sowing date
        self.common_uptake = [{'N' : 0, 'P' : 0} for _ in range(self.no_HRUs)] # [kg/km2/d]
        self.uptake_PNratio = 1/7.2 # [-] P:N during crop uptake
        ## def soil_erosion()
        self.erodibility = 0.0025 # [g * d / (J * mm)]
        self.sreroexp = 1.2 # [-] surface runoff erosion exponent
        self.cohesion = 1 # [kPa]
        self.slope = 5 # [-] every 100
        self.srfilt = 0.95 # [-] ratio of eroded sediment left in surface runoff after filtration
        self.macrofilt = 0.1 # [-] ratio of eroded sediment left in subsurface flow after filtration
        ## def denitrification()
        self.soil_moisture_dependence_factor_exp = [None for _ in range(self.no_HRUs)] # [-] for calculating denitrification
        self.limpar = 0.7 # [-] above which denitrification begins
        self.exppar = 2.5 # [-] exponential parameter for soil_moisture_dependence_factor_exp calculation
        self.half_saturation_concentration_dependence_factor = [None for _ in range(self.no_HRUs)] # [-] for calculating denitrification
        self.hsatINs = 1 # [mg/l] for calculation of half-saturation concentration dependence factor
        self.denpar = 0.015 # [-] denitrification rate coefficient
        ## def adsoprption_desorption_phosphorus()
        self.bulk_density = 1300 # [kg/m3] soil density
        self.kfr = 153.7 # [1/kg] freundlich adsorption isoterm
        self.nfr = 1/2.6 # [-] freundlich exponential coefficient
        self.kadsdes = 0.03 # [1/day] adsorption/desorption coefficient
        #####################
        #Initialise variables
        #####################
        ## def irrigation_demand()
        self.root_zone_depletion = [50 for _ in range(self.no_HRUs)] # [mm]
        self.potential_ET = [None for _ in range(self.no_HRUs)] # [mm]
        self.actual_ET = [0 for _ in range(self.no_HRUs)] # [mm]
        self.irrigation_demand = [None for _ in range(self.no_HRUs)] # [Ml/d]
        self.infiltration = [0 for _ in range(self.no_HRUs)] # [mm] for all agicultural class only
        ## def irrigation_abstraction()
        self.irrigation_supply_from_surfacewater = [0 for _ in range(self.no_HRUs)] # [Ml/d]
        self.irrigation_supply_from_groundwater = [0 for _ in range(self.no_HRUs)] # [Ml/d]
        self.irrigation_supply_from_surfacewater_conc_dissolved_inorganic_nutrients = {'N' : None, 'P' : None} # [mg/l] assume all HRUs share the same irrigation source
        self.irrigation_supply_from_surfacewater_conc_dissolved_organic_nutrients = {'N' : None, 'P' : None} # [mg/l] assume all HRUs share the same irrigation source
        self.irrigation_supply_from_groundwater_conc_dissolved_inorganic_nutrients = {'N' : None, 'P' : None} # [mg/l] assume all HRUs share the same irrigation source
        self.irrigation_supply_from_groundwater_conc_dissolved_organic_nutrients = {'N' : None, 'P' : None} # [mg/l] assume all HRUs share the same irrigation source
        ## def atmospheric_deposition()
        self.precipitation_conc_dissolved_inorganic_nutrients = {'N' : 0.8, 
                                                                 'P' : 0.022} # [mg/l] used to calculate wet deposition
        self.dry_deposition_load = {'N' : 1, 
                                    'P' : 0.316} # [kg/km2/d] - On agri: 1. nitrogen to DIN & fastN; 2. phosphorus to adsorbed P; On urban: all is into dissolved inorganic pools        0.0316
        self.wet_deposition_load = {'N' : 0,
                                    'P' : 0} # [kg/km2] - dimension = N & P
        ## def fertilisers()
        self.residue = [{'N' : 0, 'P' : 0} for _ in range(self.no_HRUs)] # [kg (N/P)/km2/day] TODO may be open for input
        self.fast_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.humus_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.dissolved_inorganic_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.dissolved_organic_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.adsorbed_inorganic_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        ## def potential_crop_uptake()
        self.crop_uptake = [{'N' : 0, 'P' : 0} for _ in range(self.no_HRUs)] # [kg/km2/d]
        ## def soil_water()
        self.percolation = [None for _ in range(self.no_HRUs)] # [mm]
        self.recharge = [None for _ in range(self.no_HRUs)] # [mm]
        self.runoff = [None for _ in range(self.no_HRUs)] # [mm]
        self.runoff_conc_dissolved_inorganic_nutrients = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [mg/l]
        self.runoff_conc_dissolved_organic_nutrients = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [mg/l]
        self.runoff_conc_eroded_phosphorus = [0.1 for _ in range(self.no_HRUs)] # [mg/l] dimension = agricultural class
        self.runoff_conc_sediment = [0.1 for _ in range(self.no_HRUs)] # [mg/l] dimension = agricultural class
        self.recharge_conc_dissolved_inorganic_nutrients = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [mg/l]
        self.recharge_conc_dissolved_organic_nutrients = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [mg/l]
        self.recharge_conc_eroded_phosphorus = [0.1 for _ in range(self.no_HRUs)] # [mg/l] dimension = agricultural class
        self.recharge_conc_sediment = [5 for _ in range(self.no_HRUs)] # [mg/l] dimension = agricultural class
        self.percolation_conc_dissolved_inorganic_nutrients = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [mg/l]
        self.percolation_conc_dissolved_organic_nutrients = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [mg/l]
        self.percolation_conc_eroded_phosphorus = [0 for _ in range(self.no_HRUs)] # [mg/l] dimension = agricultural class
        self.percolation_conc_sediment = [0 for _ in range(self.no_HRUs)] # [mg/l] dimension = agricultural class
        ## def soil_denitrification()
        self.denitrification_rate = [0 for _ in range(self.no_HRUs)] # [kg/km2] dimension = agricultural_class

        
        ## def routing()
        self.runoff_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)] # surface runoff (with constituents) generated for each HRU [mg/l, Ml/d]
                                                                                # dimension = {'pollutants' + 'volume'} * no_HRUs
        self.recharge_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)] # subsurface runoff (with constituents) generated for each HRU [mg/l, Ml/d]
                                                                                # dimension = {'pollutants' + 'volume'} * no_HRUs
        self.percolation_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)] # percolation (with constituents) generated for each HRU [mg/l, Ml/d]
                                                                                # dimension = {'pollutants' + 'volume'} * no_HRUs
        self.runoff_storage = Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9)
        self.recharge_storage = Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9)
        self.recharge_storage.storage['volume'] = 15 * 1e4
        self.soil_water = [Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9) for _ in range(self.no_HRUs)]
        for i in range(self.no_HRUs):
            self.soil_water[i].storage['volume'] = 250
        
        self.runoff_flow = self.empty_vqip() # vqip
        self.recharge_flow = self.empty_vqip() # vqip
        self.recharge_flow['volume'] = 4700 # [Ml/d]
        
        self.precipitation = [0 for _ in range(self.no_HRUs)]
        self.reference_ET = 0
        self.soil_temperature = 0 # [degree C] require input
        self.root_zone_depletion_ = self.copy_vqip(self.root_zone_depletion)
        self.runoff_flow_ = self.empty_vqip()
        self.recharge_flow_ = self.empty_vqip()
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_deny
        self.pull_check_handler['default'] = self.pull_check_deny
        #self.pull_check_handler[('Wetland', 'areas')] = self.pull_check_wetland
        self.push_set_handler['default'] = self.push_set_deny # TODO - potential modelling for floodplain that can accomodate flood
        self.push_check_handler['default'] = self.push_check_deny # TODO - potential modelling for floodplain that can accomodate flood
        
        #Mass balance TODO just water - need to include pollutants balance
        self.precipitation_vqip = [self.empty_vqip() for _ in range(self.no_HRUs)]
        self.infiltration_vqip = [self.empty_vqip() for _ in range(self.no_HRUs)]
        self.actual_ET_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)]
        self.irrigation_supply_from_surfacewater_vqip = self.empty_vqip()
        self.irrigation_supply_from_groundwater_vqip = self.empty_vqip()
        self.total_percolation = self.empty_vqip()
        
        total_precipitation_vqip = dict(self.precipitation_vqip[0])
        total_precipitation_vqip['volume'] = (sum(list(np.array(self.precipitation) * np.array(self.areas))) + self.precipitation[0] / (1 - self.interception[0]) * self.impervious_area) * constants.MM_KM2_TO_ML # [Ml]
        self._mass_balance_in = self.blend_vqip(total_precipitation_vqip, self.irrigation_supply_from_surfacewater_vqip) # [Ml]
        self._mass_balance_in = self.blend_vqip(self._mass_balance_in, self.irrigation_supply_from_groundwater_vqip) # [Ml]

        self._mass_balance_out = self.empty_vqip()
        for i in range(self.no_HRUs):
            self.actual_ET_vqip[i]['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml]
            self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.actual_ET_vqip[i])
        
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.runoff_flow_) # [Ml]
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.recharge_flow_) # [Ml]
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.total_percolation) # [Ml]
        
        self._mass_balance_ds = deepcopy(self.soil_water)
        for i in range(self.no_HRUs):
            self._mass_balance_ds[i].storage['volume'] = self.soil_water[i].storage['volume'] * self.areas[i] * constants.MM_KM2_TO_ML
            self._mass_balance_ds[i].storage_['volume'] = self.soil_water[i].storage_['volume'] * self.areas[i] * constants.MM_KM2_TO_ML
        
        
        self.mass_balance_in = [lambda : self._mass_balance_in]
        self.mass_balance_out = [lambda : self._mass_balance_out]

        self.mass_balance_ds = []
        for i in range(0, self.no_HRUs):
            l = lambda i = i : self._mass_balance_ds[i].ds()
            self.mass_balance_ds.append(l)
        self.mass_balance_ds.append(lambda : self.runoff_storage.ds())
        self.mass_balance_ds.append(lambda : self.recharge_storage.ds()) 
    
    def get_input_variables(self, input_variables):
        #!!! read reference ET
        self.precipitation = [input_variables['precipitation'] * (1 - self.interception[i]) for i in range(self.no_HRUs)]
        self.reference_ET = input_variables['reference_ET']
        self.mean_temperature = input_variables['mean_temperature']
        self.precipitation_conc_dissolved_inorganic_nutrients = input_variables['precipitation_conc_dissolved_inorganic_nutrients']
        self.dry_deposition_load = input_variables['dry_deposition_load']
        # def soil_pool_transformation()
        self.soil_temperature = input_variables['soil_temperature'] # [degree C] require input
        self.fertilisers = input_variables['fertilisers']
        self.manure = input_variables['manure']
    
    def judge_leap_year(self, year):
        # year must be int
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) :
            leap_year = 1
        else:
            leap_year = 0
        return leap_year    
    
    def get_irrigation_demand(self):

        def crop_calendar_days(dates):
            # dates must be in the form [simulation date, stage1-4 date, harvest date]
            if len(dates) == 6 :
                # trasform dates to days
                days = []
                for i in range(0,len(dates)) :
                    if i == 0 :
                        int_date = time.strptime(dates[i], "%Y-%m-%d %H:%M:%S")
                        year = int_date[0]
                        month = int_date[1]
                        day = int_date[2]
                    else:
                        int_date = time.strptime(dates[i], "%m-%d")
                        month = int_date[1]
                        day = int_date[2]
                    monthday = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                    days.append(sum(monthday[:month - 1]) + day)
                    if month > 2 and year % 4 == 0 or year % 400 == 0 and year % 100 != 0:
                        days[i] += 1
                # Judge leap year for generation of stage_period & fallow_period
                leap = self.judge_leap_year(year)
                
                # divide crop stages
                # determine fallow period
                [day, day1, day2, day3, day4, day_harvest] = days
                if day_harvest < day1 :
                    fallow_period = list(range(day_harvest, day1))
                else:
                    fallow_period = list(range(day_harvest, 366 + leap)) + list(range(1, day1))  #[list(range(day_harvest, 366)), list(range(1, day1))]
                # determine periods for 4 crop stages
                calendar_days = [day1, day2, day3, day4, day_harvest]
                stage_period = []
                stage_lengths = []
                for i in range(0, len(calendar_days)-1) :
                    if (calendar_days[i+1] - calendar_days[i]) > 0 :
                        stage_period.append(list(range(calendar_days[i], calendar_days[i+1])))
                    else:
                        stage_period.append(list(range(calendar_days[i], 366 + leap)) + list(range(1, calendar_days[i+1])))
                    stage_lengths.append(len(stage_period[i]))
                
                return day, fallow_period, stage_period, stage_lengths
            else:
                print('Error: input must be a list of dates in the form [simulation date, stage1 date, stage2 date, stage3 date, stage4 date, harvest date]')
        
        #Determine ET_depletion_factor in arable & fallow period
        #!!! format of self.t - must be in timestamp "%Y-%m-%d %H:%M:%S"
        date_str = self.t.strftime("%Y-%m-%d %H:%M:%S")
        date_str_pre = str(self.t.year - 1) + '-01-01 00:00:00' # pseudo date for last year indication
        
        if self.t.month == 1 and self.t.day == 1:
            for i in range(0, self.no_HRUs) :
                dates = [date_str] + self.start_date_stage1_4[i] + [self.harvest_date[i]]
                [self.day, self.fallow_period[i], self.stage_period[i], self.stage_lengths[i]] = crop_calendar_days(dates)  
                self.sow_day[i] = self.stage_period[i][0][0]
                # pseudo date for last year indication
                dates_pre = [date_str_pre] + self.start_date_stage1_4[i] + [self.harvest_date[i]]
                [self.stage_period_pre[i], self.stage_lengths_pre[i]] = crop_calendar_days(dates_pre)[2:4]  
        self.day = self.t.dayofyear        
            
            
        for i in range(0, self.no_HRUs) :            
            # assign ET_depletion_factor and crop_factor based on crop calendar
            if self.day in self.fallow_period[i] :
                self.crop_factor[i] = self.crop_factor_stage1_4[i][0]   # choose bare soil condition & single crop coefficient during fallow period (http://www.fao.org/3/X0490E/x0490e0h.htm)
                self.stage_label[i] = 0 # indicating fallow period
                if self.day == self.fallow_period[i][0] :
                    self.stage_label[i] = 'h' # indicating havest date
                self.crop_cover[i] = 0
                self.ground_cover[i] = 0
            else:
                for j in range(0, len(self.stage_period[i])) :
                    if self.day in self.stage_period[i][j] :
                        if j == 0 : # initial stage or mid-season
                            self.crop_factor[i] = self.crop_factor_stage1_4[i][j]
                            
                            if self.day >= self.stage_period[i][j][0] :
                                self.crop_cover[i] = 0 + (self.day - self.stage_period[i][j][0]) / self.stage_lengths[i][j] * self.crop_cover_max * 0.1
                                self.ground_cover[i] = 0 + (self.day - self.stage_period[i][j][0]) / self.stage_lengths[i][j] * self.ground_cover_max * 0.1
                            else:
                                self.crop_cover[i] = 0 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - self.stage_period_pre[i][j][0]) / self.stage_lengths_pre[i][j] * self.crop_cover_max * 0.1                       
                                self.ground_cover[i] = 0 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - self.stage_period_pre[i][j][0]) / self.stage_lengths_pre[i][j] * self.ground_cover_max * 0.1                       
                        elif j == 1: # development stage or late stage
                            if self.day >= self.stage_period[i][j][0] :
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-1] + (self.day - self.stage_period[i][j][0]) / self.stage_lengths[i][j] * (self.crop_factor_stage1_4[i][j] - self.crop_factor_stage1_4[i][j-1])
                                self.crop_cover[i] = self.crop_cover_max * 0.1 + (self.day - self.stage_period[i][j][0]) / self.stage_lengths[i][j] * (self.crop_cover_max - self.crop_cover_max * 0.1)
                                self.ground_cover[i] = self.ground_cover_max * 0.1 + (self.day - self.stage_period[i][j][0]) / self.stage_lengths[i][j] * (self.ground_cover_max - self.ground_cover_max * 0.1)
                            else:
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-1] + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - self.stage_period_pre[i][j][0]) / self.stage_lengths_pre[i][j] * (self.crop_factor_stage1_4[i][j] - self.crop_factor_stage1_4[i][j-1])                       
                                self.crop_cover[i] = self.crop_cover_max * 0.1 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - self.stage_period_pre[i][j][0]) / self.stage_lengths_pre[i][j] * (self.crop_cover_max - self.crop_cover_max * 0.1)
                                self.ground_cover[i] = self.ground_cover_max * 0.1 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - self.stage_period_pre[i][j][0]) / self.stage_lengths_pre[i][j] * (self.ground_cover_max - self.ground_cover_max * 0.1)                           
                        elif j == 2:
                            self.crop_factor[i] = self.crop_factor_stage1_4[i][j-1]
                            
                            self.crop_cover[i] = self.crop_cover_max
                            self.ground_cover[i] = self.ground_cover_max
                        else: # late stage
                            if self.day >= self.stage_period[i][j][0] :
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-2] + (self.day - self.stage_period[i][j][0]) / self.stage_lengths[i][j] * (self.crop_factor_stage1_4[i][j-1] - self.crop_factor_stage1_4[i][j-2])
                            else:
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-2] + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - self.stage_period_pre[i][j][0]) / self.stage_lengths_pre[i][j] * (self.crop_factor_stage1_4[i][j-1] - self.crop_factor_stage1_4[i][j-2])                       
                        
                            self.crop_cover[i] = self.crop_cover_max
                            self.ground_cover[i] = self.ground_cover_max
                        break
                self.stage_label[i] = j + 1
                if self.day == self.stage_period[i][0][0] :
                    self.stage_label[i] = 's' # indicating sowing date
            
            # total_available_water & readily_available_water & crop_water_stress_coefficient
            self.total_available_water[i] = (self.field_capacity[i] - self.wilting_point[i]) * self.rooting_depth[i]/constants.MM_TO_M
            self.readily_available_water[i] = self.total_available_water[i] * self.ET_depletion_factor[i]
            if self.root_zone_depletion[i] < self.readily_available_water[i] :
                self.crop_water_stress_coefficient[i] = 1
            else:
                self.crop_water_stress_coefficient[i] = max(0, (self.total_available_water[i] - self.root_zone_depletion[i]) /\
                                                                     ((1 - self.ET_depletion_factor[i]) * self.total_available_water[i]))
        
            # potential_evapotransipiration & irrigation demand
            self.potential_ET[i] = self.crop_water_stress_coefficient[i] * self.crop_factor[i] * self.reference_ET
            self.irrigation_demand[i] = max(0, self.potential_ET[i] - self.precipitation[i]) * self.areas[i] * self.irrigation_switch[i] * constants.MM_KM2_TO_ML # [Ml]
            if self.day in self.fallow_period[i] : # won't irrigate during fallow period
                self.irrigation_demand[i] = 0
    
    def get_borehole_capacity(self):
        f, arcs = self.get_direction_arcs(direction = 'pull', of_type = 'Groundwater')
        total_borehole_capacity = 0 # [Ml/day]
        for arc in arcs:
            total_borehole_capacity += arc.capacity
        return total_borehole_capacity
    
    def get_irrigation_abstraction(self):
        irrigation_demand_from_surfacewater = [i * self.irrigation_percentage_from_surfacewater for i in self.irrigation_demand]
        irrigation_demand_from_groundwater = [i * self.irrigation_percentage_from_groundwater for i in self.irrigation_demand]
        
        irrigation_demand_from_surfacewater_vqip = self.empty_vqip()
        irrigation_demand_from_surfacewater_vqip['volume'] = sum(irrigation_demand_from_surfacewater)
        irrigation_demand_from_surfacewater_vqip['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(irrigation_demand_from_surfacewater_vqip.keys()) - set(['volume']):
            irrigation_demand_from_surfacewater_vqip[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        supply = self.pull_distributed(irrigation_demand_from_surfacewater_vqip,
                                       of_type = ['River'])  # [vqip] TODO
        supply['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(supply.keys()) - set(['volume']):
            supply[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        irrigation_stress_ratio = supply['volume']/max(sum(irrigation_demand_from_surfacewater), constants.FLOAT_ACCURACY)
        self.irrigation_supply_from_surfacewater = [i * irrigation_stress_ratio for i in irrigation_demand_from_surfacewater]
        # TODO - consider other pollutants - modify soil water
        self.irrigation_supply_from_surfacewater_vqip = dict(supply) # DIN/DON/SRP/PP are still calculated but will be replaced in the get_soil_water()
        self.irrigation_supply_from_surfacewater_conc_dissolved_inorganic_nutrients['N'] = self.irrigation_supply_from_surfacewater_vqip['DIN']
        self.irrigation_supply_from_surfacewater_conc_dissolved_inorganic_nutrients['P'] = self.irrigation_supply_from_surfacewater_vqip['SRP']
        self.irrigation_supply_from_surfacewater_conc_dissolved_organic_nutrients['N'] = self.irrigation_supply_from_surfacewater_vqip['DON']
        self.irrigation_supply_from_surfacewater_conc_dissolved_organic_nutrients['P'] = self.irrigation_supply_from_surfacewater_vqip['PP']
        
        total_borehole_capacity = self.get_borehole_capacity()
        to_abstract = min(sum(irrigation_demand_from_groundwater), total_borehole_capacity)
        irrigation_demand_from_groundwater_vqip = self.empty_vqip()
        irrigation_demand_from_groundwater_vqip['volume'] = to_abstract
        irrigation_demand_from_groundwater_vqip['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(irrigation_demand_from_groundwater_vqip.keys()) - set(['volume']):
            irrigation_demand_from_groundwater_vqip[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        supply = self.pull_distributed(irrigation_demand_from_groundwater_vqip,
                                       of_type = ['Groundwater'])  # [vqip]
        supply['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(supply.keys()) - set(['volume']):
            supply[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        irrigation_stress_ratio = supply['volume']/max(sum(irrigation_demand_from_groundwater), constants.FLOAT_ACCURACY)
        self.irrigation_supply_from_groundwater = [i * irrigation_stress_ratio for i in irrigation_demand_from_groundwater]
        # TODO - consider other pollutants - modify soil water
        self.irrigation_supply_from_groundwater_vqip = dict(supply) # DIN/DON/SRP/PP are still calculated but will be replaced in the get_soil_water()
        self.irrigation_supply_from_groundwater_conc_dissolved_inorganic_nutrients['N'] = self.irrigation_supply_from_groundwater_vqip['DIN']
        self.irrigation_supply_from_groundwater_conc_dissolved_inorganic_nutrients['P'] = self.irrigation_supply_from_groundwater_vqip['SRP']
        self.irrigation_supply_from_groundwater_conc_dissolved_organic_nutrients['N'] = self.irrigation_supply_from_groundwater_vqip['DON']
        self.irrigation_supply_from_groundwater_conc_dissolved_organic_nutrients['P'] = self.irrigation_supply_from_groundwater_vqip['PP']
        
    def get_atmospheric_deposition(self):
        self.infiltration = [min(self.infiltration_capacity, self.precipitation[i]) for i in range(self.no_HRUs)] # [mm]
        # calculate wet and dry deposition
        for i in range(0, self.no_HRUs) :
            for j in ['N', 'P'] :
                self.wet_deposition_load[j] = self.precipitation_conc_dissolved_inorganic_nutrients[j] * self.infiltration[i] * constants.MGMM_L_TO_KG_KM2
                # load mixing on soil interface
                if j == 0 : # for nitrogen
                    self.dissolved_inorganic_nutrients_pool[i][j] += self.wet_deposition_load[j] + self.dry_deposition_load[j] * self.fraction_dry_deposition_to_DIN                                                
                    self.fast_nutrients_pool[i][j] += self.dry_deposition_load[j] * (1 - self.fraction_dry_deposition_to_DIN)
                elif j == 1 : # for phosphorus
                    self.dissolved_inorganic_nutrients_pool[i][j] += self.wet_deposition_load[j]
                    self.adsorbed_inorganic_nutrients_pool[i][j] += self.dry_deposition_load[j]                                               

    def get_fertilisers(self):
        for i in range(0, self.no_HRUs) :
            for j in ['N', 'P'] :           
                fertilisers_to_dissolved_inorganic_nutrients = self.fertilisers[i][j] # [kg/km2/day]
                manures_to_dissolved_inorganic_nutrients = self.manure[i][j] * self.fraction_manure_to_dissolved_inorganic_nutrients[j] # [kg/km2]
                manures_to_fast_nutrients = self.manure[i][j] * (1 - self.fraction_manure_to_dissolved_inorganic_nutrients[j]) # [kg/km2]
                residue_to_fast_nutrients = self.residue[i][j] * self.fraction_residue_to_fast_nutrients[j] # [kg/km2]
                residue_to_humus_nutrients = self.residue[i][j] * (1 - self.fraction_residue_to_fast_nutrients[j]) # [kg/km2]
    
                self.dissolved_inorganic_nutrients_pool[i][j] += fertilisers_to_dissolved_inorganic_nutrients + manures_to_dissolved_inorganic_nutrients
                self.fast_nutrients_pool[i][j] += manures_to_fast_nutrients + residue_to_fast_nutrients
                self.humus_nutrients_pool[i][j] += residue_to_humus_nutrients    
    
    def get_soil_pool_transformation(self):
        # calculate temperature_dependence_factor
        self.temperature_dependence_factor = 2 ** ((self.soil_temperature - 20) / 10)
        if self.soil_temperature < 5 :
            self.temperature_dependence_factor *= (self.soil_temperature / 5)
        if self.soil_temperature < 0 :
            self.temperature_dependence_factor = 0
            
        # calculate soil_moisture_dependence_factor
        for i in range(0, self.no_HRUs) :
            pw = self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm]
            wp = self.wilting_point[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm] 
            if self.soil_moisture_content[i] >= pw :
                self.soil_moisture_dependence_factor[i] = self.satact
            elif self.soil_moisture_content[i] <= wp :
                self.soil_moisture_dependence_factor[i] = 0
            else:
                self.soil_moisture_dependence_factor[i] = min(1, \
                                                                (1 - self.satact) * ((pw - self.soil_moisture_content[i]) / (self.thetaupp * self.rooting_depth[i] / constants.MM_TO_M)) ** self.thetapow + self.satact, \
                                                                 ((self.soil_moisture_content[i] - wp) / (self.thetalow * self.rooting_depth[i] / constants.MM_TO_M)) ** self.thetapow
                                                                )
        # calculate fluxes between sub-pools
        for i in range(0, self.no_HRUs) :
            for j in ['N', 'P'] :
                degradh = self.degrhpar[j] * self.temperature_dependence_factor * self.soil_moisture_dependence_factor[i] * self.humus_nutrients_pool[i][j]
                dissolh = self.dishpar[j] * self.temperature_dependence_factor * self.soil_moisture_dependence_factor[i] * self.humus_nutrients_pool[i][j]
                transf = self.minfpar[j] * self.temperature_dependence_factor * self.soil_moisture_dependence_factor[i] * self.fast_nutrients_pool[i][j]
                dissolf = self.disfpar[j] * self.temperature_dependence_factor * self.soil_moisture_dependence_factor[i] * self.fast_nutrients_pool[i][j]
                immobd = self.immobdpar[j] * self.temperature_dependence_factor * self.soil_moisture_dependence_factor[i] * self.dissolved_inorganic_nutrients_pool[i][j]
                
                # humus nutrients pool -
                self.humus_nutrients_pool[i][j] -= degradh
                if self.humus_nutrients_pool[i][j] < 0 :
                    degradh += self.humus_nutrients_pool[i][j]
                    self.humus_nutrients_pool[i][j] = 0
        
                self.humus_nutrients_pool[i][j] -= dissolh
                if self.humus_nutrients_pool[i][j] < 0 :
                    dissolh += self.humus_nutrients_pool[i][j]
                    self.humus_nutrients_pool[i][j] = 0
    
                # fast nutrients pool +
                self.fast_nutrients_pool[i][j] += degradh
                # fast nutrients pool -
                self.fast_nutrients_pool[i][j] -= dissolf
                if self.fast_nutrients_pool[i][j] < 0 :
                    dissolf += self.fast_nutrients_pool[i][j]
                    self.fast_nutrients_pool[i][j] = 0
                
                self.fast_nutrients_pool[i][j] -= transf
                if self.fast_nutrients_pool[i][j] < 0 :
                    transf += self.fast_nutrients_pool[i][j]
                    self.fast_nutrients_pool[i][j] = 0
                # Dissolved organic nutrients +
                self.dissolved_organic_nutrients_pool[i][j] += dissolh + dissolf
                # Dissolved inorganic nutrients +
                self.dissolved_inorganic_nutrients_pool[i][j] += transf
                
                # Dissolved inorganic nutrients - 
                self.dissolved_inorganic_nutrients_pool[i][j] -= immobd
                if self.dissolved_inorganic_nutrients_pool[i][j] < 0 :
                    immobd += self.dissolved_inorganic_nutrients_pool[i][j]
                    self.dissolved_inorganic_nutrients_pool[i][j] = 0
                # fast nutrients pool +
                self.fast_nutrients_pool[i][j] += immobd
    
    def get_potential_crop_uptake(self):
        # calculate potential crop uptake of nitrogen - i.e [0]
        for i in range(0, self.no_HRUs) :
            # non-autumn sowing crops
            if self.sow_day[i] < 181 : 
                # non-fallow period
                if self.stage_label[i] != 0 and self.stage_label[i] != 'h' : # fallow period
                    if self.day >= self.sow_day[i] :
                        dayno = self.day - self.sow_day[i]
                    else:
                        leap_previous = self.judge_leap_year(self.t.year - 1)
                        dayno = self.day - self.sow_day[i] + 365 + leap_previous
                    help_ = (self.uptake1 - self.uptake2) * math.exp(-self.uptake3 * dayno)
                    self.common_uptake[i]['N'] = 0
                    if (help_ + self.uptake2) > 0 :
                        self.common_uptake[i]['N'] = self.uptake1 * self.uptake2 * self.uptake3 * help_ / (self.uptake2 + help_) / (self.uptake2 + help_)
                # fallow period
                else:
                    self.common_uptake[i]['N'] = 0
            # autumn sowing crops
            else:
                # non-fallow period 
                if self.stage_label[i] != 0 and self.stage_label[i] != 'h' : # fallow period
                    if self.day >= self.sow_day[i] :
                        dayno = self.day - (self.sow_day[i] + 25)
                    else:
                        leap_previous = self.judge_leap_year(self.t.year - 1)
                        dayno = self.day - (self.sow_day[i] + 25) + 365 + leap_previous
                    help_ = (self.uptake1 - self.uptake2) * math.exp(-self.uptake3 * dayno)
                    self.common_uptake[i]['N'] = 0
                    if (help_ + self.uptake2) > 0 :
                        self.common_uptake[i]['N'] = self.uptake1 * self.uptake2 * self.uptake3 * help_ / (self.uptake2 + help_) / (self.uptake2 + help_)
                    temp_func = max(0, min(1, (self.mean_temperature - 5) / 20))
                    self.common_uptake[i]['N'] *= temp_func
                # fallow period
                else:
                    self.common_uptake[i]['N'] = 0
                    # Until now common_uptake_N is in [g/m2/d]
            self.common_uptake[i]['N'] *= constants.G_M2_TO_KG_KM2 # [kg/km2/d]
            # calculate potential crop uptake of phosphorus - i.e [1]
            self.common_uptake[i]['P'] = self.common_uptake[i]['N'] * self.uptake_PNratio
        
    def get_soil_water(self):
        maximum_available_dissolved_inorganic_nutrients = {'N' : 0, 'P' : 0} # [kg/km2] dimension = N & P
        last_time_root_zone_depletion = self.root_zone_depletion[:] # For store last timestep root_zone_depletion
        excess_overflow = [max(0, self.precipitation[i] - self.infiltration[i]) for i in range(self.no_HRUs)] # [mm]
        excess_overflow_vqip = [dict(self.precipitation_vqip[i]) for i in range(self.no_HRUs)]
        
        for i in range(0, self.no_HRUs) :
            #TODO different infiltration capacity - move it into for loop
            self.precipitation_vqip[i]['volume'] = self.precipitation[i] # mm
            self.infiltration_vqip[i] = dict(self.precipitation_vqip[i])
            self.infiltration_vqip[i]['volume'] = self.infiltration[i] # mm
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            irrigation_supply = (self.irrigation_supply_from_surfacewater[i] + self.irrigation_supply_from_groundwater[i])/constants.MM_KM2_TO_ML/self.areas[i]  # mm        
            potential_root_zone_depletion = self.root_zone_depletion[i] + self.potential_ET[i] - self.infiltration[i] - irrigation_supply                                      # mm
            for j in ['N', 'P'] :
                self.dissolved_inorganic_nutrients_pool[i][j] += self.irrigation_supply_from_surfacewater_conc_dissolved_inorganic_nutrients[j] * self.irrigation_supply_from_surfacewater[i] / constants.MM_KM2_TO_ML / self.areas[i] * constants.MGMM_L_TO_KG_KM2 + \
                                                                              self.irrigation_supply_from_groundwater_conc_dissolved_inorganic_nutrients[j] * self.irrigation_supply_from_groundwater[i] / constants.MM_KM2_TO_ML / self.areas[i] * constants.MGMM_L_TO_KG_KM2
                self.dissolved_organic_nutrients_pool[i][j] += self.irrigation_supply_from_surfacewater_conc_dissolved_organic_nutrients[j] * self.irrigation_supply_from_surfacewater[i] / constants.MM_KM2_TO_ML / self.areas[i] * constants.MGMM_L_TO_KG_KM2 + \
                                                                              self.irrigation_supply_from_groundwater_conc_dissolved_organic_nutrients[j] * self.irrigation_supply_from_groundwater[i] / constants.MM_KM2_TO_ML / self.areas[i] * constants.MGMM_L_TO_KG_KM2
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            irrigation_supply_from_surfacewater_vqip = dict(self.irrigation_supply_from_surfacewater_vqip)                                                                
            irrigation_supply_from_surfacewater_vqip['volume'] = self.irrigation_supply_from_surfacewater[i]/constants.MM_KM2_TO_ML/self.areas[i]  # mm 
            irrigation_supply_from_groundwater_vqip = dict(self.irrigation_supply_from_groundwater_vqip)  
            irrigation_supply_from_groundwater_vqip['volume'] = self.irrigation_supply_from_groundwater[i]/constants.MM_KM2_TO_ML/self.areas[i]  # mm 
            
            input_vqip = self.blend_vqip(self.infiltration_vqip[i], irrigation_supply_from_surfacewater_vqip)
            input_vqip = self.blend_vqip(input_vqip, irrigation_supply_from_groundwater_vqip)
            
            _ = self.soil_water[i].push_storage(input_vqip)
            #self._mass_balance_in[i] = input_vqip # 'volume' = mm
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            
            potential_soil_moisture_before_ET = self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M - self.root_zone_depletion[i] + \
                                                self.infiltration[i] + irrigation_supply                         
            if self.root_zone_depletion[i] >= self.total_available_water[i] :
                self.actual_ET[i] = 0
                self.root_zone_depletion[i] -= (self.infiltration[i] + irrigation_supply)
                effective_precipitation = 0
                #
                for j in ['N', 'P'] :
                    maximum_available_dissolved_inorganic_nutrients[j] = 0
            else:
                if potential_root_zone_depletion >= self.total_available_water[i] :
                    self.actual_ET[i] = self.total_available_water[i] - self.root_zone_depletion[i] + self.infiltration[i] + irrigation_supply
                    self.root_zone_depletion[i] = self.total_available_water[i]
                    effective_precipitation = 0
                    #
                else:
                    self.actual_ET[i] = self.potential_ET[i]
                    if potential_root_zone_depletion > 0 :
                        self.root_zone_depletion[i] = potential_root_zone_depletion
                        effective_precipitation = 0
                        #
                    else:
                        self.root_zone_depletion[i] = 0
                        effective_precipitation = -potential_root_zone_depletion
                        #
                # 
                for j in ['N', 'P'] :
                    maximum_available_dissolved_inorganic_nutrients[j] = (potential_soil_moisture_before_ET - self.wilting_point[i] * self.rooting_depth[i] / constants.MM_TO_M - effective_precipitation) / potential_soil_moisture_before_ET * self.dissolved_inorganic_nutrients_pool[i][j]
            for j in ['N', 'P'] :
                self.crop_uptake[i][j] = min(self.common_uptake[i][j], maximum_available_dissolved_inorganic_nutrients[j])
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            actual_ET_vqip = self.empty_vqip()
            actual_ET_vqip['volume'] = self.actual_ET[i] # mm
            self.actual_ET_vqip[i] = actual_ET_vqip # mm
            
            self.soil_water[i].storage = self.extract_vqip(self.soil_water[i].storage, actual_ET_vqip)
            
            effective_precipitation_vqip = dict(self.soil_water[i].storage)
            effective_precipitation_vqip['volume'] = effective_precipitation
            
            _ = self.soil_water[i].pull_storage(effective_precipitation_vqip)
            
            self._mass_balance_out[i] = self.blend_vqip(actual_ET_vqip, effective_precipitation_vqip)
            
            
            excess_overflow_vqip[i]['volume'] = excess_overflow[i]
            
            self.runoff_vqip[i] = dict(effective_precipitation_vqip)
            self.runoff_vqip[i]['volume'] = self.runoff_coefficient * effective_precipitation
            self.runoff_vqip[i] = self.blend_vqip(excess_overflow_vqip[i], self.runoff_vqip[i]) # mm
            self.recharge_vqip[i] = dict(self.soil_water[i].storage) # mm
            self.percolation_vqip[i] = dict(self.soil_water[i].storage) # mm
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!            
            self.percolation[i] = self.percolation_coefficient * effective_precipitation
            self.recharge[i] = self.recharge_coefficient * effective_precipitation
            self.runoff[i] = self.runoff_coefficient * effective_precipitation + excess_overflow[i]

            #
            for j in ['N', 'P'] :
                if effective_precipitation > 0 :
                    self.runoff_conc_dissolved_inorganic_nutrients[i][j] = (self.dissolved_inorganic_nutrients_pool[i][j] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M) * \
                                                                                          self.runoff_coefficient * effective_precipitation + \
                                                                                          self.precipitation_conc_dissolved_inorganic_nutrients[j] * excess_overflow[i]) / \
                                                                                          self.runoff[i]
                    self.recharge_conc_dissolved_inorganic_nutrients[i][j] = self.dissolved_inorganic_nutrients_pool[i][j] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M)
                    self.percolation_conc_dissolved_inorganic_nutrients[i][j] = self.recharge_conc_dissolved_inorganic_nutrients[i][j]
                    self.runoff_conc_dissolved_organic_nutrients[i][j] = (self.dissolved_organic_nutrients_pool[i][j] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M) * \
                                                                                          self.runoff_coefficient * effective_precipitation + \
                                                                                          #self.precipitation_conc_dissolved_organic_nutrients[j] * excess_overflow[i]) / \
                                                                                          0 * excess_overflow[i]) / \
                                                                                          self.runoff[i]
                    self.recharge_conc_dissolved_organic_nutrients[i][j] = self.dissolved_organic_nutrients_pool[i][j] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M)
                    self.percolation_conc_dissolved_organic_nutrients[i][j] = self.recharge_conc_dissolved_organic_nutrients[i][j]
                else:
                    if excess_overflow[i] > 0:
                        self.runoff_conc_dissolved_inorganic_nutrients[i][j] = 0 + self.precipitation_conc_dissolved_inorganic_nutrients[j]
                        self.recharge_conc_dissolved_inorganic_nutrients[i][j] = 0
                        self.percolation_conc_dissolved_inorganic_nutrients[i][j] = 0
                        self.runoff_conc_dissolved_organic_nutrients[i][j] = 0 # self.precipitation_conc_dissolved_organic_nutrients[j] = 0
                        self.recharge_conc_dissolved_organic_nutrients[i][j] = 0
                        self.percolation_conc_dissolved_organic_nutrients[i][j] = 0
                    else:
                        self.runoff_conc_dissolved_inorganic_nutrients[i][j] = 0
                        self.recharge_conc_dissolved_inorganic_nutrients[i][j] = 0
                        self.percolation_conc_dissolved_inorganic_nutrients[i][j] = 0
                        self.runoff_conc_dissolved_organic_nutrients[i][j] = 0
                        self.recharge_conc_dissolved_organic_nutrients[i][j] = 0
                        self.percolation_conc_dissolved_organic_nutrients[i][j] = 0
                # update soil dissolved_inorganic_nutrients & dissolved_organic_nutrients pools
                self.dissolved_inorganic_nutrients_pool[i][j] -= (self.crop_uptake[i][j] + \
                                                                                self.runoff_conc_dissolved_inorganic_nutrients[i][j] * self.runoff[i] - \
                                                                                self.precipitation_conc_dissolved_inorganic_nutrients[j] * excess_overflow[i] + \
                                                                                self.recharge_conc_dissolved_inorganic_nutrients[i][j] * self.recharge[i] + \
                                                                                self.percolation_conc_dissolved_inorganic_nutrients[i][j] * self.percolation[i])
                self.dissolved_organic_nutrients_pool[i][j] -= (self.runoff_conc_dissolved_organic_nutrients[i][j] * self.runoff[i] - \
                                                                              0 * excess_overflow[i] + \
                                                                              self.recharge_conc_dissolved_organic_nutrients[i][j] * self.recharge[i] + \
                                                                              self.percolation_conc_dissolved_organic_nutrients[i][j] * self.percolation[i])
            #
            self.soil_water[i].storage['DIN'] = self.dissolved_inorganic_nutrients_pool[i]['N'] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M)
            self.soil_water[i].storage['DON'] = self.dissolved_organic_nutrients_pool[i]['N'] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M)
            self.soil_water[i].storage['SRP'] = self.dissolved_inorganic_nutrients_pool[i]['P'] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M)
            self.soil_water[i].storage['PP'] = self.dissolved_organic_nutrients_pool[i]['P'] / (effective_precipitation + self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M)
            
            
            # for soil nutrient balance
            self.soil_moisture_content[i] = self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M - self.root_zone_depletion[i]
            
            # check balance for each area
            source = self.precipitation[i] + irrigation_supply
            sink = self.actual_ET[i] + self.percolation[i] + self.recharge[i] + self.runoff[i] - self.root_zone_depletion[i] + last_time_root_zone_depletion[i]
            if abs(source - sink) > constants.FLOAT_ACCURACY:
                print('Error: soil water balance unachieved at', i, self.t.strftime('%Y-%m-%d'), 'with ', (source-sink))
    
    def get_soil_erosion(self): 
        for i in range(0, self.no_HRUs) :
            # soil erosion
            [crop_cover, ground_cover] = [self.crop_cover[i], self.ground_cover[i]]
            # Calculate particles that is eroded by rain splash detachment and by overland flow (mobilised sediment)
            if self.precipitation[i] > 5:
                rainfall_energy = 8.95 + 8.44 * math.log10(self.precipitation[i] * (0.257 + math.sin(2 * 3.14 * ((self.day - 70) / 365)) * 0.09) * 2)
            else:
                rainfall_energy = 0
            rainfall_energy *= self.precipitation[i] # [J/m2]
            mobilisedsed = rainfall_energy * (1 - crop_cover) * self.erodibility + \
                           ((((self.runoff[i] - max(0, self.precipitation[i] - self.infiltration[i])) * 365) ** self.sreroexp) * (1 - ground_cover) * (1/(0.5 * self.cohesion)) * math.sin(self.slope / 100)) / 365
    #                       (((min(self.runoff[i], 8) * 365) ** self.sreroexp) * (1 - ground_cover) * (1/(0.5 * self.cohesion)) * math.sin(self.slope / 100)) / 365
                           # [g/m2]
            erodingflow = self.runoff[i] + self.recharge[i]# [mm]
            transportfactor = min(1, (erodingflow / 4) ** 1.3)
            erodedsed = 1000 * mobilisedsed * transportfactor # [kg/km2]
            # soil erosion with adsorbed inorganic phosphorus and humus phosphorus (erodedP as P in eroded sediments and effect of enrichment)
            if erodingflow > 4 :
                enrichment = 1.5
            else:
                enrichment = 4 - (4 - 1.5) * erodingflow / 4
            erodedP = 1e-6 * erodedsed * ((self.adsorbed_inorganic_nutrients_pool[i]['P'] + self.humus_nutrients_pool[i]['P']) / self.rooting_depth[i] / self.bulk_density) * enrichment # [kg/km2]
            fracminP = self.adsorbed_inorganic_nutrients_pool[i]['P'] / (self.adsorbed_inorganic_nutrients_pool[i]['P'] + self.humus_nutrients_pool[i]['P']) # [-] fraction of adsorbed inorganic P in the total P removed
            
            if erodingflow > 0 :
                surface_erodedP = self.srfilt * self.runoff[i] / erodingflow * erodedP # [kg/km2]
                surface_erodedsed = self.srfilt * self.runoff[i] / erodingflow * erodedsed # [kg/km2]
                subsurface_erodedP = self.macrofilt * self.recharge[i] / erodingflow * erodedP # [kg/km2]
                subsurface_erodedsed = self.macrofilt * self.recharge[i] / erodingflow * erodedsed # [kg/km2]
                
                remove_adsorbedP = (surface_erodedP + subsurface_erodedP) * fracminP # [kg/km2]
                remove_humusP = (surface_erodedP + subsurface_erodedP) * (1 - fracminP) # [kg/km2]
                
                self.adsorbed_inorganic_nutrients_pool[i]['P'] -= remove_adsorbedP
                if self.adsorbed_inorganic_nutrients_pool[i]['P'] < 0:
                    remove_adsorbedP += self.adsorbed_inorganic_nutrients_pool[i]['P']
                    self.adsorbed_inorganic_nutrients_pool[i]['P'] = 0
                self.humus_nutrients_pool[i]['P'] -= remove_humusP
                if self.humus_nutrients_pool[i]['P'] < 0:
                    remove_humusP += self.humus_nutrients_pool[i]['P']
                    self.humus_nutrients_pool[i]['P'] = 0
            
                self.runoff_conc_eroded_phosphorus[i] = (remove_adsorbedP + remove_humusP) / erodingflow # [mg/l]
                self.recharge_conc_eroded_phosphorus[i] = (remove_adsorbedP + remove_humusP) / erodingflow # [mg/l]
                self.runoff_conc_sediment[i] = surface_erodedsed / max(self.runoff[i], 0.0001) # [mg/l]
                self.recharge_conc_sediment[i] = subsurface_erodedsed / max(self.recharge[i], 0.0001) # [mg/l]
                self.percolation_conc_sediment[i] = self.recharge_conc_sediment[i] * 0.3 # [mg/l] 10%
            else:
                self.runoff_conc_eroded_phosphorus[i] = 0
                self.recharge_conc_eroded_phosphorus[i] = 0
                self.runoff_conc_sediment[i] = 0
                self.recharge_conc_sediment[i] = 0
                self.percolation_conc_sediment[i] = 0
    
    def get_soil_denitrification(self):  
        # for N only - i.e. [0]
        for i in range(0, self.no_HRUs) :
            # calculate exponential soil moisture dependence factor
            pw = self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm]
            if self.soil_moisture_content[i] > pw :
                self.soil_moisture_dependence_factor_exp[i] = 1
            elif (self.soil_moisture_content[i] / pw) > self.limpar :
                 self.soil_moisture_dependence_factor_exp[i] = (((self.soil_moisture_content[i] / pw) - self.limpar) / (1 - self.limpar)) ** self.exppar
            else:
                 self.soil_moisture_dependence_factor_exp[i] = 0
            # calculate half-saturation concentration factor
            DIN_conc = self.dissolved_inorganic_nutrients_pool[i]['N'] / self.soil_moisture_content[i] / constants.MGMM_L_TO_KG_KM2
            self.half_saturation_concentration_dependence_factor[i] = DIN_conc / (DIN_conc + self.hsatINs)
            # calcualate defnitrification rate
            self.denitrification_rate[i] = self.denpar * self.dissolved_inorganic_nutrients_pool[i]['N'] * \
                                                         self.temperature_dependence_factor * self.soil_moisture_dependence_factor_exp[i] * self.half_saturation_concentration_dependence_factor[i]
            self.dissolved_inorganic_nutrients_pool[i]['N'] -= self.denitrification_rate[i]
            if self.dissolved_inorganic_nutrients_pool[i]['N'] < 0 :
                self.denitrification_rate[i] += self.dissolved_inorganic_nutrients_pool[i]['N']
                self.dissolved_inorganic_nutrients_pool[i]['N'] = 0

    def get_adsoption_desorption_phosphorus(self):
        # for phosphorus only - i.e. [1]
        limit = 0.00001 # Threshold for breaking in Newton-Raphson method
        for i in range(0, self.no_HRUs) :   
            nfrloc = self.nfr
            ad_de_P_pool = self.adsorbed_inorganic_nutrients_pool[i]['P'] + self.dissolved_inorganic_nutrients_pool[i]['P'] # [kg/km2]
            if ad_de_P_pool == 0:
                continue
            conc_sol = self.adsorbed_inorganic_nutrients_pool[i]['P'] / self.bulk_density / self.rooting_depth[i] # [mg P/kg soil]
            if conc_sol <= 0 :
                nfrloc = 1
                print('Warning: soil partP <=0. Freundlich will give error, take shortcut.')
            coeff = self.kfr * self.bulk_density * self.rooting_depth[i] # [mm]
            # calculate equilibrium concentration
            if nfrloc == 1 :
                xn_1 = ad_de_P_pool / (self.soil_moisture_content[i] + coeff) # [mg/l]
                ad_P_equi_conc = self.kfr * xn_1   # [mg/ kg]
            else:
                # Newton-Raphson method
                x0 = math.exp((math.log(conc_sol) - math.log(self.kfr)) / self.nfr) # initial guess of equilibrium liquid concentration
                fxn = x0 * self.soil_moisture_content[i] + coeff * (x0 ** self.nfr) - ad_de_P_pool
                xn = x0
                xn_1 = xn
                j = 0
                while (abs(fxn) > limit and j < 20) : # iteration to calculate equilibrium concentations
                    fxn = xn * self.soil_moisture_content[i] + coeff * (xn ** self.nfr) - ad_de_P_pool
                    fprimxn = self.soil_moisture_content[i] + self.nfr * coeff * (xn ** (self.nfr - 1))
                    dx = fxn / fprimxn
                    if abs(dx) < (0.000001 * xn) :
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
                adsdes = (ad_P_equi_conc - conc_sol) * (1 - math.exp(-self.kadsdes)) # kinetic adsorption/desorption
                help_ = adsdes * self.bulk_density * self.rooting_depth[i]
                if -help_ > self.adsorbed_inorganic_nutrients_pool[i]['P'] or self.dissolved_inorganic_nutrients_pool[i]['P'] < help_ :
                    if -help_ > self.adsorbed_inorganic_nutrients_pool[i]['P'] :
                        help_ = -self.adsorbed_inorganic_nutrients_pool[i]['P']
                    if self.dissolved_inorganic_nutrients_pool[i]['P'] < help_ :
                        help_ = self.dissolved_inorganic_nutrients_pool[i]['P']
                    print('Warning: freundlich flow adjusted, was larger than pool')
                self.adsorbed_inorganic_nutrients_pool[i]['P'] += help_
                self.dissolved_inorganic_nutrients_pool[i]['P'] -= help_

    def get_routing(self):
        # load the variables with special processes into the list (in 'pollutants' + 'volume')
        for i in range(0, self.no_HRUs):
            self.runoff_vqip[i]['volume'] = self.runoff[i] * self.areas[i] * constants.MM_KM2_TO_ML # [Ml/d]
            self.recharge_vqip[i]['volume'] = self.recharge[i] * self.areas[i] * constants.MM_KM2_TO_ML # [Ml/d]
            self.percolation_vqip[i]['volume'] = self.percolation[i] * self.areas[i] * constants.MM_KM2_TO_ML # [Ml/d]
            if set(['SRP', 'PP', 'DIN', 'DON', 'SS']).issubset(constants.POLLUTANTS): # TODO feasibility in splitting these variables
                # [mg/l]
                self.runoff_vqip[i]['DIN'] = self.runoff_conc_dissolved_inorganic_nutrients[i]['N']
                self.runoff_vqip[i]['DON'] = self.runoff_conc_dissolved_organic_nutrients[i]['N']
                self.runoff_vqip[i]['SRP'] = self.runoff_conc_dissolved_inorganic_nutrients[i]['P']
                self.runoff_vqip[i]['PP'] = self.runoff_conc_dissolved_organic_nutrients[i]['P'] + self.runoff_conc_eroded_phosphorus[i]
                self.runoff_vqip[i]['SS'] = self.runoff_conc_sediment[i]
                # [mg/l]
                self.recharge_vqip[i]['DIN'] = self.recharge_conc_dissolved_inorganic_nutrients[i]['N']
                self.recharge_vqip[i]['DON'] = self.recharge_conc_dissolved_organic_nutrients[i]['N']
                self.recharge_vqip[i]['SRP'] = self.recharge_conc_dissolved_inorganic_nutrients[i]['P']
                self.recharge_vqip[i]['PP'] = self.recharge_conc_dissolved_organic_nutrients[i]['P'] + self.recharge_conc_eroded_phosphorus[i]
                self.recharge_vqip[i]['SS'] = self.recharge_conc_sediment[i]
                # [mg/l]
                self.percolation_vqip[i]['DIN'] = self.percolation_conc_dissolved_inorganic_nutrients[i]['N']
                self.percolation_vqip[i]['DON'] = self.percolation_conc_dissolved_organic_nutrients[i]['N']
                self.percolation_vqip[i]['SRP'] = self.percolation_conc_dissolved_inorganic_nutrients[i]['P']
                self.percolation_vqip[i]['PP'] = self.percolation_conc_dissolved_organic_nutrients[i]['P'] + self.percolation_conc_eroded_phosphorus[i]
                self.percolation_vqip[i]['SS'] = self.percolation_conc_sediment[i]
        # blend all inflow to routing reservoirs
        self.total_runoff = self.empty_vqip()
        self.total_recharge = self.empty_vqip()
        self.total_percolation = self.empty_vqip()
        for i in range(0, self.no_HRUs):
            self.total_runoff = self.blend_vqip(self.total_runoff, self.runoff_vqip[i])
            self.total_recharge = self.blend_vqip(self.total_recharge, self.recharge_vqip[i])
            self.total_percolation = self.blend_vqip(self.total_percolation, self.percolation_vqip[i]) # [Ml]
        # runoff from impervious flow
        excess_overflow_vqip = dict(self.precipitation_vqip[0])
        excess_overflow_vqip['volume'] *= self.impervious_area / (1 - self.interception[0]) # [mmkm2 = Ml]
        self.total_runoff = self.blend_vqip(self.total_runoff, excess_overflow_vqip)
        # pull from the routing reservoirs
        _ = self.runoff_storage.pull_storage(self.runoff_flow)
        _ = self.recharge_storage.pull_storage(self.recharge_flow)
        # push to the routing reservoirs
        _ = self.runoff_storage.push_storage(self.total_runoff) #, force = True
        _ = self.recharge_storage.push_storage(self.total_recharge) #, force = True
        
        outflow = self.blend_vqip(self.runoff_flow, self.recharge_flow) # [vqip] [Ml]
        outflow['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(outflow.keys()) - set(['volume']):
            outflow[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        reply = self.push_distributed(outflow,
                                      of_type = ['River'
                                                 #, 'Wetland'
                                                 ])
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('Cropland couldnt push')
            
        # generate flow entering rivers(arcs) - discharged at timestep t+1
        self.runoff_flow = dict(self.runoff_storage.storage) # vqip
        self.runoff_flow['volume'] = self.runoff_storage.storage['volume'] / self.runoff_residence_time # TODO should be [Ml/d]
        
        self.recharge_flow = dict(self.recharge_storage.storage) # vqip
        #self.recharge_flow['volume'] = self.recharge_storage.storage['volume'] / self.recharge_residence_time # TODO should be [Ml/d]
        self.recharge_flow['volume'] = self.recharge_flow_['volume'] + (self.total_recharge['volume'] - self.recharge_flow_['volume']) / self.recharge_residence_time
        
        # generate percolation entering groundwater(nodes)
        _ = dict(self.total_percolation) # [vqip] [Ml]
        _['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
        for i in set(_.keys()) - set(['volume']):
            _[i] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
        reply = self.push_distributed(_,
                                      of_type = ['Groundwater'])
        if reply['volume'] > constants.FLOAT_ACCURACY:
            print('Cropland couldnt push to Groundwater')
        
        # for mass balance
        total_precipitation_vqip = dict(self.precipitation_vqip[0])
        total_precipitation_vqip['volume'] = (sum(list(np.array(self.precipitation) * np.array(self.areas))) + self.precipitation[0] / (1 - self.interception[0]) * self.impervious_area) * constants.MM_KM2_TO_ML # [Ml]
        self._mass_balance_in = self.blend_vqip(total_precipitation_vqip, self.irrigation_supply_from_surfacewater_vqip) # [Ml]
        self._mass_balance_in = self.blend_vqip(self._mass_balance_in, self.irrigation_supply_from_groundwater_vqip) # [Ml]
        
        self._mass_balance_out = self.empty_vqip()
        for i in range(self.no_HRUs):
            self.actual_ET_vqip[i]['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml]
            self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.actual_ET_vqip[i])
        
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.runoff_flow_)
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.recharge_flow_)
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.total_percolation)
        
        #self._mass_balance_ds = deepcopy(self.soil_water)
        self._mass_balance_ds = [Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9) for _ in range(self.no_HRUs)]
        for i in range(self.no_HRUs):
            self._mass_balance_ds[i].storage = dict(self.soil_water[i].storage)
            self._mass_balance_ds[i].storage_ = dict(self.soil_water[i].storage_)
            self._mass_balance_ds[i].storage['volume'] = self.soil_water[i].storage['volume'] * self.areas[i] * constants.MM_KM2_TO_ML
            self._mass_balance_ds[i].storage_['volume'] = self.soil_water[i].storage_['volume'] * self.areas[i] * constants.MM_KM2_TO_ML
        
    # def pull_check_wetland(self, vqip = None):
    #     return self.areas
        
    def push_set_accept(self, vqip):
        #Returns all request accepted
        return self.empty_vqip()

    def push_check_accept(self, vqip = None):
        #Returns unbounded available push capacity
        if not vqip:
            vqip = self.empty_vqip()
            vqip['volume'] = constants.UNBOUNDED_CAPACITY
        return vqip
    
    def end_timestep(self):
        self.runoff_storage.end_timestep()
        self.recharge_storage.end_timestep()
        self.root_zone_depletion_ = self.copy_vqip(self.root_zone_depletion)
        self.runoff_flow_ = self.copy_vqip(self.runoff_flow)
        self.recharge_flow_ = self.copy_vqip(self.recharge_flow)
        
        for i in range(self.no_HRUs):
            self.soil_water[i].end_timestep()
        