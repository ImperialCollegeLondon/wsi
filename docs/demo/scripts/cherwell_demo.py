# -*- coding: utf-8 -*-
"""
Created on Fri Dec 30 09:56:02 2022

@author: leyan
"""


from wsimod.nodes.waste import Waste
from wsimod.nodes.land import Land
from wsimod.nodes.nodes import Node
from wsimod.nodes.wtw import WWTW
from wsimod.nodes.storage import River
from wsimod.nodes.discharge_point import Discharge_point
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.storage import Groundwater
from wsimod.orchestration.model import Model
from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.demo.create_oxford import create_timeseries
import os
import pandas as pd
from matplotlib import pyplot as plt
from datetime import datetime

data_folder= os.path.join(os.path.abspath(os.path.join(os.path.dirname("__file__"),os.path.pardir)), "data", "processed", "cherwell")

precipitation = pd.read_csv(os.path.join(data_folder, "Cherwell, Thame and Wye_rainfall_1975_2018_day_25_km.csv"))
precipitation.columns = ['date', 'value']
precipitation['variable'] = 'precipitation'
precipitation['value'] *= constants.MM_TO_M
et0 = pd.read_csv(os.path.join(data_folder, "reference_ET.csv"))
et0.columns = ['date', 'value']
et0['variable'] = 'et0'
et0['value'] *= constants.MM_TO_M
tasmax = pd.read_csv(os.path.join(data_folder, "Cherwell, Thame and Wye_tasmax_1975_2018_day_25_km.csv")).set_index('date')
tasmin = pd.read_csv(os.path.join(data_folder, "Cherwell, Thame and Wye_tasmin_1975_2018_day_25_km.csv")).set_index('date')
temperature = (tasmax['tasmax'] + tasmin['tasmin']) / 2
temperature.name = 'value'
temperature = pd.DataFrame(temperature)
temperature['variable'] = 'temperature'
temperature = temperature.reset_index(drop=False)

input_data = pd.concat([precipitation, et0, temperature])
input_data.date = pd.to_datetime(input_data.date)
land_inputs = input_data.set_index(['variable','date']).value.to_dict()
dates = input_data.date.drop_duplicates()

constants.set_default_pollutants()

crop_para = pd.read_csv(os.path.join(data_folder, "Crop_parameters.csv")).set_index('lucode')
fer = pd.read_csv(os.path.join(data_folder, "fer_timeseries.csv")).set_index('date')
man = pd.read_csv(os.path.join(data_folder, "man_timeseries.csv")).set_index('date')
surfaces = []
for i in range(0, len(crop_para.index)):
    
    idx = crop_para.index[i]
    
    area = crop_para.loc[idx, 'area'] * constants.KM2_TO_M2
    kc_ini = crop_para.loc[idx, 'Kc_ini']
    kc_mid = crop_para.loc[idx, 'Kc_mid']
    kc_end = crop_para.loc[idx, 'Kc_end']
    cc_s1 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s1'], '%Y-%m-%d').timetuple().tm_yday
    cc_s2 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s2'], '%Y-%m-%d').timetuple().tm_yday
    cc_s3 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s3'], '%Y-%m-%d').timetuple().tm_yday
    cc_s4 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s4'], '%Y-%m-%d').timetuple().tm_yday
    cc_h = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_h'], '%Y-%m-%d').timetuple().tm_yday
    Zr = crop_para.loc[idx, 'Zr']
    p = crop_para.loc[idx, 'p']
    
    sowing_day = cc_s1
    harvest_day = cc_h
    if sowing_day < harvest_day:
        # spring sown        
        crop_factor_stages = [kc_ini   , kc_ini  , kc_ini  , kc_mid  , kc_mid   , kc_end, kc_ini, kc_ini   ]
        crop_factor_stage_dates =[  0,  cc_s1, cc_s2, cc_s3, cc_s4, cc_h-1, cc_h, 366]
    else:
        # autumn sown
        if cc_s2 < cc_s3:
            crop_factor_stages = [kc_ini  , kc_ini, kc_ini  , kc_mid  , kc_mid  , kc_end   , kc_ini, kc_ini, kc_ini   ]
            crop_factor_stage_dates =[  0,  cc_s2, cc_s2+1, cc_s3, cc_s4, cc_h-1, cc_h, cc_s1, 366]
        else:
            kc_split = kc_ini + (366 - cc_s2)/(366 - cc_s2 + cc_s3) * (kc_mid - kc_ini)
            crop_factor_stages = [kc_split  , kc_mid, kc_mid  , kc_end  , kc_ini  , kc_ini   , kc_ini, kc_split  ]
            crop_factor_stage_dates =[  0,  cc_s3, cc_s4, cc_h-1, cc_h, cc_s1, cc_s2, 366]
    sowing_day = cc_s1
    harvest_day = cc_h
    ET_depletion_factor = p
    rooting_depth = Zr
    
    fer_ = pd.DataFrame(fer['fer_N_'+str(i+1)] / constants.KM2_TO_M2).reset_index(drop = False)
    fer_.date = pd.to_datetime(fer_.date)
    fer_ = fer_[~fer_.date.dt.strftime('%Y-%m').duplicated()].copy().set_index('date')
    fer_nhx = fer_ * 0
    fer_nhx.columns = ['value']
    fer_nhx = pd.DataFrame(fer_nhx).reset_index(drop = False)
    fer_nhx['variable'] = 'nhx-fertiliser'
    fer_nhx.date = fer_nhx.date.dt.to_period('M').unique()
    fer_noy = fer_ * 1
    fer_noy.columns = ['value']
    fer_noy = pd.DataFrame(fer_noy).reset_index(drop = False)
    fer_noy['variable'] = 'noy-fertiliser'
    fer_noy.date = fer_noy.date.dt.to_period('M').unique()
    fer_srp = pd.DataFrame(fer['fer_P_'+str(i+1)] / constants.KM2_TO_M2).reset_index(drop = False)
    fer_srp.date = pd.to_datetime(fer_srp.date)
    fer_srp = fer_srp[~fer_srp.date.dt.strftime('%Y-%m').duplicated()].copy()
    fer_srp.columns = ['date', 'value']
    fer_srp['variable'] = 'srp-fertiliser'
    fer_srp.date = fer_srp.date.dt.to_period('M').unique()
    
    man_ = pd.DataFrame(man['man_N_'+str(i+1)] / constants.KM2_TO_M2).reset_index(drop = False)
    man_.date = pd.to_datetime(man_.date)
    man_ = man_[~man_.date.dt.strftime('%Y-%m').duplicated()].copy().set_index('date')
    man_nhx = man_ * 0
    man_nhx.columns = ['value']
    man_nhx = pd.DataFrame(man_nhx).reset_index(drop = False)
    man_nhx['variable'] = 'nhx-manure'
    man_nhx.date = man_nhx.date.dt.to_period('M').unique()
    man_noy = man_ * 1
    man_noy.columns = ['value']
    man_noy = pd.DataFrame(man_noy).reset_index(drop = False)
    man_noy['variable'] = 'noy-manure'
    man_noy.date = man_noy.date.dt.to_period('M').unique()
    man_srp = pd.DataFrame(man['man_P_'+str(i+1)] / constants.KM2_TO_M2).reset_index(drop = False)
    man_srp.date = pd.to_datetime(man_srp.date)
    man_srp = man_srp[~man_srp.date.dt.strftime('%Y-%m').duplicated()].copy()
    man_srp.columns = ['date', 'value']
    man_srp['variable'] = 'srp-manure'
    man_srp.date = man_srp.date.dt.to_period('M').unique()
    
    dates_monthyear = fer_srp.date
    dry_nhx = create_timeseries(1.6 / constants.KM2_TO_M2 * 0, dates_monthyear, '{0}-{1}'.format('nhx', 'dry'))
    dry_noy = create_timeseries(1.6 / constants.KM2_TO_M2 * 1, dates_monthyear, '{0}-{1}'.format('noy', 'dry'))
    dry_srp = create_timeseries(0.0316 / constants.KM2_TO_M2, dates_monthyear, '{0}-{1}'.format('srp', 'dry'))
    wet_nhx = create_timeseries(1.6 / constants.KM2_TO_M2 * 0, dates_monthyear, '{0}-{1}'.format('nhx', 'wet'))
    wet_noy = create_timeseries(1.6 / constants.KM2_TO_M2 * 1, dates_monthyear, '{0}-{1}'.format('noy', 'wet'))
    wet_srp = create_timeseries(0.0316 / constants.KM2_TO_M2, dates_monthyear, '{0}-{1}'.format('srp', 'wet'))
    
    surface_input_data = pd.concat([fer_nhx, fer_noy, fer_srp, man_nhx, man_noy, man_srp, dry_nhx, dry_noy, dry_srp, wet_nhx, wet_noy, wet_srp])
    surface_input_data = surface_input_data.set_index(['variable','date']).value.to_dict()
    
    surface = {'type_' : 'GrowingSurface',
               'surface' : 'my_growing_surface'+str(i),
               'area' : area,
               'rooting_depth' : rooting_depth,
               'crop_factor_stage_dates' : crop_factor_stage_dates,
               'crop_factor_stages' : crop_factor_stages,
               'sowing_day' : sowing_day,
               'harvest_day' : harvest_day,
               'ET_depletion_factor' : ET_depletion_factor,
               'data_input_dict' : surface_input_data,
               'wilting_point' : 0.12,
               'field_capacity' : 0.3,
               'surface_coefficient' : 0.3,
               'percolation_coefficient' : 0,
               'infiltration_capacity' : 0.04
               }
    surfaces.append(surface)

pollutant_deposition = {'nitrate' : 1.6 / constants.KM2_TO_M2,
                        'phosphate' : 0.0316 / constants.KM2_TO_M2
                        }
impervious_surface = {'type_' : 'ImperviousSurface',
                        'area' : 140.5 * constants.KM2_TO_M2,
                        'pore_depth' : 0.1,
                        'pollutant_load' : pollutant_deposition,
                          'surface' : 'urban',
                          'initial_storage' : 5e5}
surfaces.append(impervious_surface)

land = Land(name = 'my_land',
            data_input_dict = land_inputs,
            surfaces = surfaces,
            surface_residence_time = 4,
            subsurface_residence_time = 25)

gw = Groundwater(name = 'my_groundwater',
                  area = 900e6,
                  capacity = constants.UNBOUNDED_CAPACITY,
                  residence_time = 500)

sewer = Sewer(capacity = 4e6,
              name = 'sewer'
              )

discharge_point = Discharge_point(name = 'discharge_point',
                                  effluent_conc={
                                                'ammonia' : 0.13 * constants.MG_L_TO_KG_M3,
                                                'nitrate' : 18 * constants.MG_L_TO_KG_M3,
                                                'phosphate' : 1. * 0.85 * constants.MG_L_TO_KG_M3,
                                                'solids' : 10 * constants.MG_L_TO_KG_M3,
                                                'temperature' : 14
                                                },
                                  effluent_volume=0.15 * 137000
                                                )

river = River(name = 'river',
              length = 30 * constants.KM_TO_M,
              data_input_dict = land_inputs)

outlet = Waste(name = 'my_outlet')

arc1 = Arc(in_port = land, out_port = river, name = 'land-river')
arc2 = Arc(in_port = discharge_point, out_port = river, name = 'wwtw-river')
arc3 = Arc(in_port = river, out_port = outlet, name = 'river-outlet')
arc4 = Arc(in_port = land, out_port = gw, name = 'land-gw')
arc5 = Arc(in_port = gw, out_port = river, name = 'gw-river')
arc6 = Arc(in_port = land, out_port = sewer, name = 'land-sewer')
arc7 = Arc(in_port = sewer, out_port = river, name = 'sewer-river')

my_model = Model()

my_model.add_instantiated_nodes([land,discharge_point,river,outlet,gw,sewer])
my_model.add_instantiated_arcs([arc1,arc2,arc3,arc4,arc5,arc6,arc7])

my_model.dates = dates

results = my_model.run()

flows = pd.DataFrame(results[0])
surfaces = pd.DataFrame(results[3])
#Convert to mg/l
for pol in constants.ADDITIVE_POLLUTANTS:
    flows[pol] *= constants.KG_M3_TO_MG_L / flows.flow

# compare with observed data
flow_obs = pd.read_csv(os.path.join(data_folder, "Observed_riverflow.csv")).set_index('date')
flow_obs.index = pd.to_datetime(flow_obs.index)

wq_obs = pd.read_csv(os.path.join(data_folder, "EA_WQ.csv")).set_index('date')
wq_obs.index = pd.to_datetime(wq_obs.index)

f, axs = plt.subplots(4,1)
x = flows.groupby('arc').get_group('river-outlet').set_index('time').index
y = flows.groupby('arc').get_group('river-outlet').set_index('time').flow / constants.M3_S_TO_M3_DT
axs[0].plot(x, y)
axs[0].scatter(flow_obs.index, flow_obs['flow'], c = 'red', s = 1)
axs[0].set_xlim([flow_obs.index[0], flow_obs.index[-1]])
x = flows.groupby('arc').get_group('river-outlet').set_index('time').index
y = flows.groupby('arc').get_group('river-outlet').set_index('time').phosphate
axs[1].plot(x, y)
axs[1].scatter(wq_obs.index, wq_obs['Orthophosphate, reactive as P'], c = 'red', s = 1, zorder = 10)
axs[1].set_xlim([wq_obs.index[0], wq_obs.index[-1]])
x = flows.groupby('arc').get_group('river-outlet').set_index('time').index
y = flows.groupby('arc').get_group('river-outlet').set_index('time').nitrate + \
    flows.groupby('arc').get_group('river-outlet').set_index('time').nitrite + \
    flows.groupby('arc').get_group('river-outlet').set_index('time').ammonia
axs[2].plot(x, y)
axs[2].scatter(wq_obs.index, wq_obs['Nitrogen, Total Oxidised as N'], c = 'red', s = 1, zorder = 10)
axs[2].set_xlim([wq_obs.index[0], wq_obs.index[-1]])
x = flows.groupby('arc').get_group('river-outlet').set_index('time').index
y = flows.groupby('arc').get_group('river-outlet').set_index('time').solids
axs[3].plot(x, y)
axs[3].scatter(wq_obs.index, wq_obs['Solids, Suspended at 105 C'], c = 'red', s = 1, zorder = 10)
axs[3].set_xlim([wq_obs.index[0], wq_obs.index[-1]])
axs[3].set_ylim([wq_obs['Solids, Suspended at 105 C'].min(), wq_obs['Solids, Suspended at 105 C'].max()])
