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

class Wetland(Node):
    def __init__(self, **kwargs):
        # parameters required input
        self.no_HRUs = 0 # !!! input
        self.areas = [] # cannot include 0 !!! input
        self.rooting_depth = [] # m (FAO 56 (http://www.fao.org/docrep/X0490E/x0490e0e.htm)) !!! input
        self.crop_factor_stage1_4 = [] # [-] (FAO 56) initial stage, middle stage, end stage !!! input
        self.start_date_stage1_4 = [] # date %m-%d !!! input
        self.harvest_date = [] # date %m-%d !!! input
        self.ET_depletion_factor = [] # mm !!! input

        #Update args
        super().__init__(**kwargs)
        
        #Default parameters determined by input
        self.field_capacity = [0.3 for _ in range(self.no_HRUs)] # [-] (FAO 56)
        self.wilting_point = [0.12 for _ in range(self.no_HRUs)] # [-] (FAO 56)
        ## def irrigation_demand()
        self.day = None # [-] (0 - 365 or 366) day number for the date under calculation within the year
        self.stage_lengths = [None for _ in range(self.no_HRUs)] # [-] should have the same format as 'start_date_stage1-4'
        self.stage_label = [None for _ in range(self.no_HRUs)] # [-] indicating which stage the crop is in
        self.recharge_coefficient = 0.02 # [-] ratio of net rainfall transformed into recharge
        self.recharge_residence_time = 3 # [d]
        self.percolation_coefficient = 0.02 # [0-1] ratio of net rainfall transformed into percolation
        self.crop_factor = [None for _ in range(self.no_HRUs)] # mm
        self.total_available_water = [None for _ in range(self.no_HRUs)] # mm
        self.readily_available_water = [None for _ in range(self.no_HRUs)] # mm
        self.crop_water_stress_coefficient = [None for _ in range(self.no_HRUs)] # [-]
        self.sow_day = [None for _ in range(self.no_HRUs)] # [-] day of sowing date
        ## def atmospheric_deposition()
        self.fraction_dry_deposition_to_DIN = 0.9 # [-] DIN = dissolved inorganic nitrogen
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
        ## def denitrification()
        self.soil_moisture_dependence_factor_exp = [None for _ in range(self.no_HRUs)] # [-] for calculating denitrification
        self.limpar = 0.7 # [-] above which denitrification begins
        self.exppar = 2.5 # [-] exponential parameter for soil_moisture_dependence_factor_exp calculation
        self.half_saturation_concentration_dependence_factor = [None for _ in range(self.no_HRUs)] # [-] for calculating denitrification
        self.hsatINs = 1 # [mg/l] for calculation of half-saturation concentration dependence factor
        self.denpar = 0.03#0.015 # [-] denitrification rate coefficient
        ## def adsoprption_desorption_phosphorus()
        self.bulk_density = 1300 # [kg/m3] soil density
        self.kfr = 153.7 # [1/kg] freundlich adsorption isoterm
        self.nfr = 1/2.6 # [-] freundlich exponential coefficient
        self.kadsdes = 0#0.03 # [1/day] adsorption/desorption coefficient

        self.macrofilt = 0.2
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.w0 = 0.5 # [m] threshold level above soil surface
        self.pore_volume = [0.4 for _ in range(self.no_HRUs)] # [-]
        
        self.wlproddep = 0.5 # [m] wetland production depth
        self.sedvel = 0.1 # [m/day] sedimentation velocity
        
        self.T_wdays = 20 # [days] weighting constant for river temperature calculation (similar to moving average period)
        self.T_5_days = [] # [degree C] average water temperature of 10 days
        self.T_30_days = [] # [degree C] average water temperature of 30 days
        self.wltmpexp = 1 # [-] exponential temporal factor for biochemical processes
        self.wl_temperature = 15 # [degree C] wetland temperature
        
        self.wlmphuptin = 0.001 * 1e6 # [kg/km2/day] DIN macrophyte uptake rate
        self.wlmphuptsp = 0.0001 * 1e6 # [kg/km2/day] SRP macrophyte uptake rate
        self.wlfastfrac = 0.7 # [-] fraction of macrouptake into fastN
        self.wlpartfrac = 0.5 # [-] fraction of sedimentation into partN
        self.SS = 0 # [kg/km2] sedimentation pool - SS
        
        self.fracarea = 1 # [0-1] percentage of area with submerged plants
        self.pan_coefficient = 0.7 # [-] doi: 10.2166/wcc.2017.139
        
        self.k = 1 # [-]
        self.p = 2 # [-]
        self.standingwater = [0 for _ in range(self.no_HRUs)] # [mm] standingwater above pore volume
        
        self.outflow_vqip = self.empty_vqip()
        #####################
        #Initialise variables
        #####################
        ## def irrigation_demand()
        self.root_zone_depletion = [50 for _ in range(self.no_HRUs)] # [mm]
        self.potential_ET = [None for _ in range(self.no_HRUs)] # [mm]
        self.actual_ET = [0 for _ in range(self.no_HRUs)] # [mm]
        ## def atmospheric_deposition()
        self.precipitation_conc_dissolved_inorganic_nutrients = {'N' : 0.8, 
                                                                 'P' : 0.022} # [mg/l] used to calculate wet deposition
        self.dry_deposition_load = {'N' : 1, 
                                    'P' : 0.316} # [kg/km2/d] - On agri: 1. nitrogen to DIN & fastN; 2. phosphorus to adsorbed P; On urban: all is into dissolved inorganic pools        0.0316
        self.wet_deposition_load = {'N' : 0,
                                    'P' : 0} # [kg/km2] - dimension = N & P
        ## def calculate_wetland_processes
        self.fast_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.humus_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.dissolved_inorganic_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.dissolved_organic_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        self.adsorbed_inorganic_nutrients_pool = [{'N' : 0.1, 'P' : 0.1} for _ in range(self.no_HRUs)] # [kg (N/P)/km2]
        ## def soil_denitrification()
        self.denitrification_rate = [0 for _ in range(self.no_HRUs)] # [kg/km2] dimension = agricultural_class
        ## def adsoprption_desorption_phosphorus()
        self.soil_moisture_content = [None for _ in range(self.no_HRUs)] # [mm] for adsorption-desorption calculation only
        ## def potential_crop_uptake()
        self.crop_uptake = [{'N' : 0, 'P' : 0} for _ in range(self.no_HRUs)] # [kg/km2/d]
        ## def routing()
        self.recharge_flow = self.empty_vqip() # vqip
        self.recharge_flow['volume'] = 0 # [Ml/d]
        self.recharge_flow_ = self.empty_vqip()
        self.recharge_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)] # subsurface runoff (with constituents) generated for each HRU [mg/l, Ml/d]
                                                                                # dimension = {'pollutants' + 'volume'} * no_HRUs
        self.percolation_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)] # percolation (with constituents) generated for each HRU [mg/l, Ml/d]
                                                                                # dimension = {'pollutants' + 'volume'} * no_HRUs
        self.recharge_storage = Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9)
        self.recharge_storage.storage['volume'] = 15 * 1e4
        self.soil_water = [Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9) for _ in range(self.no_HRUs)]
        for i in range(self.no_HRUs):
            self.soil_water[i].storage['volume'] = 250
        
        self.precipitation = 0
        self.reference_ET = 0
        
        #Update handlers
        self.pull_set_handler['default'] = self.pull_set_deny
        self.pull_check_handler['default'] = self.pull_check_deny
        self.push_set_handler['default'] = self.add_to_irrigation # TODO - potential modelling for floodplain that can accomodate flood
        self.push_check_handler['default'] = self.push_check_accept # TODO - potential modelling for floodplain that can accomodate flood
        
        #Mass balance TODO just water - need to include pollutants balance
        self.precipitation_vqip = self.empty_vqip()
        self.precipitation_vqip['do'] = 10
        self.actual_ET_vqip = [self.empty_vqip() for i in range(0, self.no_HRUs)]
        self.irrigation_supply_from_surfacewater_vqip = self.empty_vqip()

        self.precipitation_vqip['volume'] = self.precipitation * sum(self.areas) * constants.MM_KM2_TO_ML # [Ml]
        
        self._mass_balance_in = self.blend_vqip(self.precipitation_vqip, self.irrigation_supply_from_surfacewater_vqip) # [Ml]

        self._mass_balance_out = self.empty_vqip()
        for i in range(self.no_HRUs):
            self.actual_ET_vqip[i]['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml]
            self.outflow_vqip['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml]
            self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.actual_ET_vqip[i])
        
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.outflow_vqip) # [Ml]
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.recharge_flow_) # [Ml]
        self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.percolation_vqip[0]) # [Ml]
        
        #self._mass_balance_ds = deepcopy(self.soil_water)
        self._mass_balance_ds = [Tank(capacity = 1e9, # vqip
                                        area = 1e9,
                                        datum = 1e9) for _ in range(self.no_HRUs)]
        for i in range(self.no_HRUs):
            self._mass_balance_ds[i].storage = dict(self.soil_water[i].storage)
            self._mass_balance_ds[i].storage_ = dict(self.soil_water[i].storage_)
            self._mass_balance_ds[i].storage['volume'] = self.soil_water[i].storage['volume'] * self.areas[i] * constants.MM_KM2_TO_ML
            self._mass_balance_ds[i].storage_['volume'] = self.soil_water[i].storage_['volume'] * self.areas[i] * constants.MM_KM2_TO_ML
        
        
        self.mass_balance_in = [lambda : self._mass_balance_in]
        self.mass_balance_out = [lambda : self._mass_balance_out]

        self.mass_balance_ds = []
        for i in range(0, self.no_HRUs):
            l = lambda i = i : self._mass_balance_ds[i].ds()
            self.mass_balance_ds.append(l)
        self.mass_balance_ds.append(lambda : self.recharge_storage.ds()) 
    
    def get_input_variables(self, input_variables):
        #!!! read reference ET
        self.precipitation = input_variables['precipitation']
        self.reference_ET = input_variables['reference_ET']
        self.mean_temperature = input_variables['mean_temperature']
        self.precipitation_conc_dissolved_inorganic_nutrients = input_variables['precipitation_conc_dissolved_inorganic_nutrients']
        self.dry_deposition_load = input_variables['dry_deposition_load']

    
    def add_to_irrigation(self, vqip):
        vqip = self.copy_vqip(vqip)
        vqip['volume'] /= constants.ML_TO_M3 # [M3 -> Ml]
        for i in set(vqip.keys()) - set(['volume']):
            vqip[i] /= constants.MG_L_TO_KG_M3 # [kg/m3 -> mg/l]
        self.irrigation_supply_from_surfacewater_vqip = self.empty_vqip()
        self.irrigation_supply_from_surfacewater_vqip = self.blend_vqip(self.irrigation_supply_from_surfacewater_vqip, vqip)
        return self.empty_vqip()
    
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
        for i in range(0, self.no_HRUs) :
            dates = [date_str] + self.start_date_stage1_4[i] + [self.harvest_date[i]]
            [self.day, fallow_period, stage_period, self.stage_lengths[i]] = crop_calendar_days(dates)  
            self.sow_day[i] = stage_period[0][0]
            # pseudo date for last year indication
            dates_pre = [date_str_pre] + self.start_date_stage1_4[i] + [self.harvest_date[i]]
            [stage_period_pre, stage_lengths_pre] = crop_calendar_days(dates_pre)[2:4]  
            
            # assign ET_depletion_factor and crop_factor based on crop calendar
            if self.day in fallow_period :
                self.crop_factor[i] = self.crop_factor_stage1_4[i][0]   # choose bare soil condition & single crop coefficient during fallow period (http://www.fao.org/3/X0490E/x0490e0h.htm)
                self.stage_label[i] = 0 # indicating fallow period
                if self.day == fallow_period[0] :
                    self.stage_label[i] = 'h' # indicating havest date
                #self.crop_cover[i] = 0
                #self.ground_cover[i] = 0
            else:
                for j in range(0, len(stage_period)) :
                    if self.day in stage_period[j] :
                        if j == 0 : # initial stage or mid-season
                            self.crop_factor[i] = self.crop_factor_stage1_4[i][j]
                            
                            # if self.day >= stage_period[j][0] :
                            #     self.crop_cover[i] = 0 + (self.day - stage_period[j][0]) / self.stage_lengths[i][j] * self.crop_cover_max * 0.1
                            #     self.ground_cover[i] = 0 + (self.day - stage_period[j][0]) / self.stage_lengths[i][j] * self.ground_cover_max * 0.1
                            # else:
                            #     self.crop_cover[i] = 0 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - stage_period_pre[j][0]) / stage_lengths_pre[j] * self.crop_cover_max * 0.1                       
                            #     self.ground_cover[i] = 0 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - stage_period_pre[j][0]) / stage_lengths_pre[j] * self.ground_cover_max * 0.1                       
                        elif j == 1: # development stage or late stage
                            if self.day >= stage_period[j][0] :
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-1] + (self.day - stage_period[j][0]) / self.stage_lengths[i][j] * (self.crop_factor_stage1_4[i][j] - self.crop_factor_stage1_4[i][j-1])
                                # self.crop_cover[i] = self.crop_cover_max * 0.1 + (self.day - stage_period[j][0]) / self.stage_lengths[i][j] * (self.crop_cover_max - self.crop_cover_max * 0.1)
                                # self.ground_cover[i] = self.ground_cover_max * 0.1 + (self.day - stage_period[j][0]) / self.stage_lengths[i][j] * (self.ground_cover_max - self.ground_cover_max * 0.1)
                            else:
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-1] + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - stage_period_pre[j][0]) / stage_lengths_pre[j] * (self.crop_factor_stage1_4[i][j] - self.crop_factor_stage1_4[i][j-1])                       
                                # self.crop_cover[i] = self.crop_cover_max * 0.1 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - stage_period_pre[j][0]) / stage_lengths_pre[j] * (self.crop_cover_max - self.crop_cover_max * 0.1)
                                # self.ground_cover[i] = self.ground_cover_max * 0.1 + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - stage_period_pre[j][0]) / stage_lengths_pre[j] * (self.ground_cover_max - self.ground_cover_max * 0.1)                           
                        elif j == 2:
                            self.crop_factor[i] = self.crop_factor_stage1_4[i][j-1]
                            
                            # self.crop_cover[i] = self.crop_cover_max
                            # self.ground_cover[i] = self.ground_cover_max
                        else: # late stage
                            if self.day >= stage_period[j][0] :
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-2] + (self.day - stage_period[j][0]) / self.stage_lengths[i][j] * (self.crop_factor_stage1_4[i][j-1] - self.crop_factor_stage1_4[i][j-2])
                            else:
                                self.crop_factor[i] = self.crop_factor_stage1_4[i][j-2] + (self.day + 365 + self.judge_leap_year(self.t.year - 1) - stage_period_pre[j][0]) / stage_lengths_pre[j] * (self.crop_factor_stage1_4[i][j-1] - self.crop_factor_stage1_4[i][j-2])                       
                        
                            # self.crop_cover[i] = self.crop_cover_max
                            # self.ground_cover[i] = self.ground_cover_max
                        break
                self.stage_label[i] = j + 1
                if self.day == stage_period[0][0] :
                    self.stage_label[i] = 's' # indicating sowing date
            
            # total_available_water & readily_available_water & crop_water_stress_coefficient
            self.total_available_water[i] = (self.field_capacity[i] - self.wilting_point[i]) * self.rooting_depth[i]/constants.MM_TO_M
            self.readily_available_water[i] = self.total_available_water[i] * self.ET_depletion_factor[i]
            self.root_zone_depletion[i] = max(0, self.field_capacity[i] * self.rooting_depth[i]/constants.MM_TO_M - self.soil_water[i].storage['volume']) # [mm]
            if self.root_zone_depletion[i] < self.readily_available_water[i] :
                self.crop_water_stress_coefficient[i] = 1
            else:
                self.crop_water_stress_coefficient[i] = max(0, (self.total_available_water[i] - self.root_zone_depletion[i]) /\
                                                                     ((1 - self.ET_depletion_factor[i]) * self.total_available_water[i]))
        
            # potential_evapotransipiration & irrigation demand
            self.potential_ET[i] = self.crop_water_stress_coefficient[i] * self.crop_factor[i] * self.reference_ET * (1 - self.fracarea) + \
                                    self.fracarea * self.pan_coefficient * self.reference_ET # # land plant evapotranspiration + water surface evaporation
    
    def get_atmospheric_deposition(self):
        # calculate wet and dry deposition
        for i in range(0, self.no_HRUs) :
            self.dissolved_inorganic_nutrients_pool[i]['N'] = self.concentration_to_total(self.soil_water[i].storage)['DIN'] # [kg/km2]
            self.dissolved_inorganic_nutrients_pool[i]['P'] = self.concentration_to_total(self.soil_water[i].storage)['SRP'] # [kg/km2]
               
            for j in ['N', 'P'] :
                self.wet_deposition_load[j] = self.precipitation_conc_dissolved_inorganic_nutrients[j] * self.precipitation * constants.MGMM_L_TO_KG_KM2
                # load mixing on soil interface
                if j == 0 : # for nitrogen
                    self.dissolved_inorganic_nutrients_pool[i][j] += self.wet_deposition_load[j] + self.dry_deposition_load[j] * self.fraction_dry_deposition_to_DIN                                                
                    self.fast_nutrients_pool[i][j] += self.dry_deposition_load[j] * (1 - self.fraction_dry_deposition_to_DIN)
                elif j == 1 : # for phosphorus
                    self.dissolved_inorganic_nutrients_pool[i][j] += self.wet_deposition_load[j]
                    self.adsorbed_inorganic_nutrients_pool[i][j] += self.dry_deposition_load[j]                                               
            
            self.soil_water[i].storage['DIN'] = self.dissolved_inorganic_nutrients_pool[i]['N'] / self.soil_water[i].storage['volume']
            self.soil_water[i].storage['SRP'] = self.dissolved_inorganic_nutrients_pool[i]['P'] / self.soil_water[i].storage['volume']
    
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
        #TODO different infiltration capacity - move it into for loop
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.precipitation_vqip['volume'] = self.precipitation
        maximum_available_dissolved_inorganic_nutrients = {'N' : 0, 'P' : 0} # [kg/km2] dimension = N & P
        for i in range(0, self.no_HRUs) :
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            irrigation_supply_from_surfacewater_vqip = dict(self.irrigation_supply_from_surfacewater_vqip)                                                            
            irrigation_supply_from_surfacewater_vqip['volume'] /= constants.MM_KM2_TO_ML * self.areas[i]  # mm 
            
            input_vqip = self.blend_vqip(self.precipitation_vqip, irrigation_supply_from_surfacewater_vqip)
            
            _ = self.soil_water[i].push_storage(input_vqip)
            
            self.dissolved_inorganic_nutrients_pool[i]['N'] = self.concentration_to_total(self.soil_water[i].storage)['DIN'] # [kg/km2]
            self.dissolved_inorganic_nutrients_pool[i]['P'] = self.concentration_to_total(self.soil_water[i].storage)['SRP'] # [kg/km2]
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            potential_soil_moisture_before_ET = self.soil_water[i].storage['volume'] # [mm]
            potential_soil_moisture = self.soil_water[i].storage['volume'] - self.potential_ET[i] # [mm]
            
            wp = self.wilting_point[i] * self.rooting_depth[i] / constants.MM_TO_M # wilting point in [mm]
            fc = self.field_capacity[i] * self.rooting_depth[i] / constants.MM_TO_M # field capacity in [mm]
            pw = self.pore_volume[i] * self.rooting_depth[i] / constants.MM_TO_M # pore volume in [mm]
            
            if self.soil_water[i].storage_['volume'] <= wp :
                self.actual_ET[i] = 0
                effective_precipitation = 0
                #
                for j in ['N', 'P'] :
                    maximum_available_dissolved_inorganic_nutrients[j] = 0
            else:
                if potential_soil_moisture <= wp :
                    self.actual_ET[i] = self.soil_water[i].storage['volume'] - wp
                    effective_precipitation = 0
                    #
                else:
                    self.actual_ET[i] = self.potential_ET[i]
                    if potential_soil_moisture < fc :
                        effective_precipitation = 0
                        #
                    else:
                        effective_precipitation = potential_soil_moisture - fc
                # 
                for j in ['N', 'P'] :
                    maximum_available_dissolved_inorganic_nutrients[j] = (potential_soil_moisture_before_ET - self.wilting_point[i] * self.rooting_depth[i] / constants.MM_TO_M - effective_precipitation) / potential_soil_moisture_before_ET * self.dissolved_inorganic_nutrients_pool[i][j]
            for j in ['N', 'P'] :
                self.crop_uptake[i][j] = min(self.common_uptake[i][j], maximum_available_dissolved_inorganic_nutrients[j])
                self.dissolved_inorganic_nutrients_pool[i][j] -= self.crop_uptake[i][j]
            self.soil_water[i].storage['DIN'] = self.dissolved_inorganic_nutrients_pool[i]['N'] / self.soil_water[i].storage['volume'] # [mg/l]
            self.soil_water[i].storage['SRP'] = self.dissolved_inorganic_nutrients_pool[i]['P'] / self.soil_water[i].storage['volume'] # [mg/l]
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            actual_ET_vqip = self.empty_vqip()
            actual_ET_vqip['volume'] = self.actual_ET[i] # mm
            self.actual_ET_vqip[i] = actual_ET_vqip # mm
            
            self.soil_water[i].storage = self.extract_vqip(self.soil_water[i].storage, actual_ET_vqip)
            
            self.percolation_vqip[i] = dict(self.soil_water[i].storage) # mm            
            self.percolation_vqip[i]['volume'] = self.percolation_coefficient * effective_precipitation
            
            _ = self.soil_water[i].pull_storage(self.percolation_vqip[i])
            
            self.recharge_vqip[i] = dict(self.soil_water[i].storage) # mm            
            self.recharge_vqip[i]['volume'] = self.recharge_coefficient * effective_precipitation
            
            _ = self.soil_water[i].pull_storage(self.recharge_vqip[i])
            
            # generate percolation entering groundwater(nodes)
            for i in range(0, self.no_HRUs):
                self.recharge_vqip[i]['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml/d]
                self.percolation_vqip[i]['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml/d]
            
            # pull from the routing reservoirs
            _ = self.recharge_storage.pull_storage(self.recharge_flow)
            # push to the routing reservoirs
            _ = self.recharge_storage.push_storage(self.recharge_vqip[i]) #, force = True
            
            self.recharge_flow['SS'] *= self.macrofilt # macroflow filtration of suspended solids
            _ = dict(self.recharge_flow) # [vqip] [Ml]
            _['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
            for key in set(_.keys()) - set(['volume']):
                _[key] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
            reply = self.push_distributed(_,
                                          of_type = ['River'])
            if reply['volume'] > constants.FLOAT_ACCURACY:
                print('Wetland couldnt push')
            
            self.recharge_flow = dict(self.recharge_storage.storage) # vqip
            self.recharge_flow['volume'] = self.recharge_storage.storage['volume'] / self.recharge_residence_time # TODO should be [Ml/d]
        
            _ = dict(self.percolation_vqip[i]) # [vqip] [Ml]
            _['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
            for key in set(_.keys()) - set(['volume']):
                _[key] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
            reply = self.push_distributed(_,
                                          of_type = ['Groundwater'])
            if reply['volume'] > constants.FLOAT_ACCURACY:
                print('Wetland couldnt push to Groundwater')
            #self._mass_balance_out[i] = self.blend_vqip(actual_ET_vqip, effective_precipitation_vqip)
            

            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!            
            
            self.standingwater[i] = self.soil_water[i].storage['volume'] - pw # [mm]
            
            self.calculate_wetland_processes()
            
            #Calculate wetland outflow from standing water of uppermost soil layer
            
            if self.standingwater[i] * constants.MM_TO_M > self.w0:

                wst = self.standingwater[i] * constants.MM_TO_M - self.w0 # [m]
                dh = (input_vqip['volume'] - self.actual_ET[i] - self.percolation_vqip[i]['volume']/self.areas[i]/constants.MM_KM2_TO_ML) * constants.MM_TO_M # [m]
                h0 = wst - dh # [m]
                if h0 > 0:
                    t2 = constants.D_TO_S # [s/day]
                    hr = h0 # [m]
                elif h0 + dh > 0:
                    t1 = -h0 / dh
                    t2 = constants.D_TO_S * (1 - t1)
                    hr = dh / constants.D_TO_S * t2 / 10 # [m]
                else:
                    t2 = 0
                
                qut = 0
                if t2 > 0:
                    r = self.p * self.k * hr ** (self.p - 1) / self.areas[i] / constants.KM2_TO_M2 # [1/s]
                    if r > 0:
                        z = hr + dh / constants.D_TO_S / r - hr / self.p # [m]
                        h = (hr - z) * math.exp(-r * t2) + z # [m]
                        qut = self.areas[i] * constants.KM2_TO_M2 * (dh - (h - h0)) / constants.D_TO_S * constants.M3_S_TO_ML_D # [ML/day]
                        if qut < 0:
                            qut = 0
                
                #self.outflow = self.k * (self.standingwater[i] * constants.MM_TO_M - self.w0) ** self.p * constants.M3_S_TO_ML_D # [ML/day]
                qut = min(qut, wst * self.areas[i] * constants.KM2_TO_M2 / constants.ML_TO_M3)   # [Ml/d]
            else:
                qut = 0
            
            self.outflow_vqip = dict(self.soil_water[i].storage)
            self.outflow_vqip['volume'] = qut / constants.MM_KM2_TO_ML / self.areas[i] # [mm]
            _ = self.soil_water[i].pull_storage(self.outflow_vqip)
            
            self.outflow_vqip['volume'] = qut # [Ml]
            _ = dict(self.outflow_vqip) # [vqip] [Ml]
            _['volume'] *= constants.ML_TO_M3 # [Ml -> M3]
            for key in set(_.keys()) - set(['volume']):
                _[key] *= constants.MG_L_TO_KG_M3 # [mg/l -> kg/m3]
            reply = self.push_distributed(_,
                                          of_type = ['River'])
            if reply['volume'] > constants.FLOAT_ACCURACY:
                print('Wetland couldnt push')
            
            # check balance for each area
            source = self.precipitation + irrigation_supply_from_surfacewater_vqip['volume']
            sink = self.actual_ET[i] + self.percolation_vqip[i]['volume']/(self.areas[i] * constants.MM_KM2_TO_ML) + \
                self.outflow_vqip['volume'] / constants.MM_KM2_TO_ML / self.areas[i] + self.recharge_flow_['volume']/(self.areas[i] * constants.MM_KM2_TO_ML)
            ds = self.soil_water[i].storage['volume'] - self.soil_water[i].storage_['volume'] + \
                (self.recharge_storage.storage['volume'] - self.recharge_storage.storage_['volume'])/(self.areas[i] * constants.MM_KM2_TO_ML)
            if abs(source - sink - ds) > constants.FLOAT_ACCURACY:
                print('Error: soil water balance unachieved at', i, self.t.strftime('%Y-%m-%d'), 'with ', (source-sink-ds))
            
            self.precipitation_vqip['volume'] = self.precipitation * sum(self.areas) * constants.MM_KM2_TO_ML # [Ml]
            
            self._mass_balance_in = self.blend_vqip(self.precipitation_vqip, self.irrigation_supply_from_surfacewater_vqip) # [Ml]
    
            self._mass_balance_out = self.empty_vqip()
            for i in range(self.no_HRUs):
                self.actual_ET_vqip[i]['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml]
                self.outflow_vqip['volume'] *= self.areas[i] * constants.MM_KM2_TO_ML # [Ml]
                self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.actual_ET_vqip[i])
            
            self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.outflow_vqip) # [Ml]
            self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.recharge_flow_) # [Ml]
            self._mass_balance_out = self.blend_vqip(self._mass_balance_out, self.percolation_vqip[0]) # [Ml]
            
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
            self.mass_balance_ds.append(lambda : self.recharge_storage.ds())
            
    def calculate_wetland_processes(self):
        i = 0
        if self.standingwater[i] > 0:
            inivolume = self.standingwater[i] * self.areas[i] * constants.MM_KM2_TO_ML # [ML]
            inivolume_vqip = dict(self.soil_water[i].storage)
            inivolume_vqip['volume'] = inivolume
            inivolume_vqip['SS'] *= self.soil_water[i].storage['volume'] * self.areas[i] * constants.MM_KM2_TO_ML / inivolume #!!!! assume no SS in soil water

            
            halfsatTPwater = 0.05
            #Initialisation of wetland variables
            wetlandnutrient = self.concentration_to_total(inivolume_vqip)         # [kg]
            retention = self.empty_vqip()                                         # [kg]
    
            #Fractional area of wetland with macrophyte uptake
            self.fracarea = min(1.0, self.wlproddep * (1/((inivolume * constants.ML_TO_M3/self.areas[i]/constants.KM2_TO_M2)*2)))
            
    
            # calculate T_5_days & T_30_days & temperature dependence factor
            self.T_5_days.append(self.wl_temperature)
            if len(self.T_5_days) > 5 :
                del(self.T_5_days[0])
            self.T_30_days.append(self.wl_temperature)
            if len(self.T_30_days) > 30 :
                del(self.T_30_days[0])
            T_5 = np.array(self.T_5_days).mean()
            T_30 = np.array(self.T_30_days).mean()
            
            #Temperature dependent factor
            tmpfcn1 = (max(0, T_5) / 20) ** self.wltmpexp
            tmpfcn2 = (T_5 - T_30) / 5
            tmpfcn = max(0, tmpfcn1 * tmpfcn2)
            
            waterTPmean = inivolume_vqip['SRP'] + inivolume_vqip['PP']
            TPfcn = waterTPmean / (waterTPmean + halfsatTPwater)
            
            # N
            # Denitrification - the same as soil routines
            #Sedimentation
            sedimentation_on = self.sedvel * inivolume_vqip['DON'] * self.areas[i] * 1e3      # [kg/day] sedimentation
            if sedimentation_on > 0.999 * wetlandnutrient['DON']:
                sedimentation_on = 0.999 * wetlandnutrient['DON']
            retention['DON'] = retention['DON'] + sedimentation_on
            self.fast_nutrients_pool[i]['N'] += sedimentation_on / self.areas[i]                   # [kg/km2]
            #Uptake of IN by macrophytes
            macrouptake_in = self.wlmphuptin * tmpfcn * self.fracarea * self.areas[i] * TPfcn  # [kg]
            if macrouptake_in > 0.5 * wetlandnutrient['DIN']:
                macrouptake_in = 0.5 * wetlandnutrient['DIN']  
            retention['DIN'] = retention['DIN'] + macrouptake_in
            self.fast_nutrients_pool[i]['N'] += self.wlfastfrac * macrouptake_in / self.areas[i]
            self.humus_nutrients_pool[i]['N'] += (1 - self.wlfastfrac) * (macrouptake_in / self.areas[i])
            # P
            # Denitrification - the same as soil routines
            #Sedimentation
            sedimentation_pp = self.sedvel * inivolume_vqip['PP'] * self.areas[i] * 1e3      # [kg/day] sedimentation
            if sedimentation_pp > 0.999 * wetlandnutrient['PP']:
                sedimentation_pp = 0.999 * wetlandnutrient['PP']
            retention['PP'] = retention['PP'] + sedimentation_pp
            self.fast_nutrients_pool[i]['P'] += (1 - self.wlpartfrac) * sedimentation_pp / self.areas[i]                   # [kg/km2]
            self.adsorbed_inorganic_nutrients_pool[i]['P'] += self.wlpartfrac * sedimentation_pp / self.areas[i]                   # [kg/km2]
            #Uptake of IN by macrophytes
            macrouptake_sp = self.wlmphuptsp * tmpfcn * self.fracarea * self.areas[i] * TPfcn  # [kg]
            if macrouptake_sp > 0.5 * wetlandnutrient['SRP']:
                macrouptake_sp = 0.5 * wetlandnutrient['SRP']  
            retention['SRP'] = retention['SRP'] + macrouptake_sp
            self.fast_nutrients_pool[i]['P'] += self.wlfastfrac * macrouptake_sp / self.areas[i]
            self.humus_nutrients_pool[i]['P'] += (1 - self.wlfastfrac) * (macrouptake_sp / self.areas[i])
            # SS
            #Sedimentation
            sedimentation_ss = self.sedvel * inivolume_vqip['SS'] * self.areas[i] * 1e3      # [kg/day] sedimentation
            if sedimentation_ss > 0.999 * wetlandnutrient['SS']:
                sedimentation_ss = 0.999 * wetlandnutrient['SS']
            #print(sedimentation_ss / wetlandnutrient['SS'])
            retention['SS'] = retention['SS'] + sedimentation_ss
            self.SS += sedimentation_ss / self.areas[i]                   # [kg/km2]

            for pollutant in constants.POLLUTANTS:
                inivolume_vqip[pollutant] = (wetlandnutrient[pollutant] - retention[pollutant]) / inivolume_vqip['volume'] # [mg/l]

            self.soil_water[i].storage['volume'] -= self.standingwater[i]
            self.soil_water[i].storage['SS'] = 0 #!!!!! assume no SS in soil water
            inivolume_vqip['volume'] /= self.areas[i] * constants.MM_KM2_TO_ML # [mm]
            self.soil_water[i].storage = self.blend_vqip(self.soil_water[i].storage, inivolume_vqip)
        else:
            self.fracarea = 0
    
    def get_soil_denitrification(self):  
        # for N only - i.e. [0]
        # calculate temperature_dependence_factor
        # water temperature
        self.wl_temperature = (1 - 1/self.T_wdays) * self.wl_temperature + 1/self.T_wdays * self.mean_temperature
        self.temperature_dependence_factor = 2 ** ((self.wl_temperature - 20) / 10)
        if self.wl_temperature < 5 :
            self.temperature_dependence_factor *= (self.wl_temperature / 5)
        if self.wl_temperature < 0 :
            self.temperature_dependence_factor = 0
        for i in range(0, self.no_HRUs) :
            # calculate exponential soil moisture dependence factor
            pw = self.pore_volume[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm]
            if self.soil_water[i].storage['volume'] > pw :
                self.soil_moisture_dependence_factor_exp[i] = 1
            elif (self.soil_water[i].storage['volume'] / pw) > self.limpar :
                self.soil_moisture_dependence_factor_exp[i] = (((self.soil_water[i].storage['volume'] / pw) - self.limpar) / (1 - self.limpar)) ** self.exppar
            else:
                self.soil_moisture_dependence_factor_exp[i] = 0
            # calculate half-saturation concentration factor
            DIN_conc = self.soil_water[i].storage['DIN']
            self.half_saturation_concentration_dependence_factor[i] = DIN_conc / (DIN_conc + self.hsatINs)
            # calcualate defnitrification rate
            DIN_pool = self.concentration_to_total(self.soil_water[i].storage)['DIN'] # [kg]
            self.denitrification_rate[i] = self.denpar * DIN_pool * \
                                                         self.temperature_dependence_factor * self.soil_moisture_dependence_factor_exp[i] * self.half_saturation_concentration_dependence_factor[i]
            DIN_pool -= self.denitrification_rate[i]
            if DIN_pool < 0 :
                self.denitrification_rate[i] += DIN_pool
                DIN_pool = 0
            
            self.soil_water[i].storage['DIN'] = DIN_pool / self.soil_water[i].storage['volume']
    
    def get_soil_pool_transformation(self):
        # calculate temperature_dependence_factor - the same as the soil_denitrification
            
        # calculate soil_moisture_dependence_factor
        for i in range(0, self.no_HRUs) :
            pw = self.pore_volume[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm]
            wp = self.wilting_point[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm]

            if self.soil_water[i].storage['volume'] >= pw :
                self.soil_moisture_dependence_factor[i] = self.satact
            elif self.soil_water[i].storage['volume'] <= wp :
                self.soil_moisture_dependence_factor[i] = 0
            else:
                self.soil_moisture_dependence_factor[i] = min(1, \
                                                                (1 - self.satact) * ((pw - self.soil_water[i].storage['volume']) / (self.thetaupp * self.rooting_depth[i] / constants.MM_TO_M)) ** self.thetapow + self.satact, \
                                                                 ((self.soil_water[i].storage['volume'] - wp) / (self.thetalow * self.rooting_depth[i] / constants.MM_TO_M)) ** self.thetapow
                                                                )
        # calculate fluxes between sub-pools
        for i in range(0, self.no_HRUs) :
            self.dissolved_organic_nutrients_pool[i]['N'] = self.concentration_to_total(self.soil_water[i].storage)['DON']
            self.dissolved_organic_nutrients_pool[i]['P'] = self.concentration_to_total(self.soil_water[i].storage)['PP']
            self.dissolved_inorganic_nutrients_pool[i]['N'] = self.concentration_to_total(self.soil_water[i].storage)['DIN']
            self.dissolved_inorganic_nutrients_pool[i]['P'] = self.concentration_to_total(self.soil_water[i].storage)['SRP']
                
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
                
            self.soil_water[i].storage['DIN'] = self.dissolved_inorganic_nutrients_pool[i]['N'] / self.soil_water[i].storage['volume']
            self.soil_water[i].storage['DON'] = self.dissolved_organic_nutrients_pool[i]['N'] / self.soil_water[i].storage['volume']
            self.soil_water[i].storage['SRP'] = self.dissolved_inorganic_nutrients_pool[i]['P'] / self.soil_water[i].storage['volume']
            self.soil_water[i].storage['PP'] = self.dissolved_organic_nutrients_pool[i]['P'] / self.soil_water[i].storage['volume']
                
    def get_adsoption_desorption_phosphorus(self):
        # for phosphorus only - i.e. [1]
        limit = 0.00001 # Threshold for breaking in Newton-Raphson method
        for i in range(0, self.no_HRUs) :
            pw = self.pore_volume[i] * self.rooting_depth[i] / constants.MM_TO_M # [mm]
            self.soil_moisture_content[i] = min(self.soil_water[i].storage['volume'], pw) # [mm]
            self.dissolved_inorganic_nutrients_pool[i]['P'] = self.concentration_to_total(self.soil_water[i].storage)['SRP']
            
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
            
            self.soil_water[i].storage['SRP'] = self.dissolved_inorganic_nutrients_pool[i]['P'] / self.soil_water[i].storage['volume']
                
    def push_check_accept(self, vqip = None):
        #Returns unbounded available push capacity
        if not vqip:
            vqip = self.empty_vqip()
            vqip['volume'] = constants.UNBOUNDED_CAPACITY
        return vqip
    
    def end_timestep(self):
        self.irrigation_supply_from_surfacewater_vqip = self.empty_vqip()
        self.recharge_storage.end_timestep()
        self.recharge_flow_ = self.copy_vqip(self.recharge_flow)
        for i in range(self.no_HRUs):
            self.soil_water[i].end_timestep()

        