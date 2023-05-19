# %% [markdown]
# # WSIMOD model demonstration - Cherwell (.py)
#
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/cherwell_demo.py)
#
# 1. [Introduction](#Introduction)
#
# 2. [Data](#Imports-and-forcing-data)
#
# 3. [Basic surface](#Basic-surface)
#
# 4. [Pervious surface](#Pervious-surface)
#
# 5. [Connecting land nodes in a model](#Connecting-land-nodes-in-a-model)
#
#     5.1 [Model object](#Model-object)
#
# 6. [Growing surface](#Growing-surface)
# 
# %% [markdown]
# ## Introduction
#
# This case study demonstrates the performance of using WSIMOD to simulate river water quality in the
# cherwell catchment, which is upstream Oxford city. 
#
#
# %% [markdown]
# ## Imports and forcing data

# %% [markdown]
# Import packages
# %%

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
import numpy as np

# %% [markdown]
# Load input data
# %%

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

### generate crop parameters for growing surfaces based on input - a function
def generate_crop_calendar(calendar_type = 'Single',
                       kc1_ini = None,
                       kc1_mid = None,
                       kc1_end = None,
                       cc1_s1 = None,
                       cc1_s2 = None,
                       cc1_s3 = None,
                       cc1_s4 = None,
                       cc1_h = None,
                       Zr1 = None,
                       p1 = None,
                       kc2_ini = None,
                       kc2_mid = None,
                       kc2_end = None,
                       cc2_s1 = None,
                       cc2_s2 = None,
                       cc2_s3 = None,
                       cc2_s4 = None,
                       cc2_h = None,
                       Zr2 = None,
                       p2 = None
                       ):
    
    def sort_and_interp(crop_factor_stage_dates,
                        crop_factor_stages,
                        harvest_sow_stages,
                        cover_stages,
                        ET_depletion_factor_stages,
                        rooting_depth_stages,
                        sort_out_index
                        ):
        # formulate into a dataframe for sorting
        sort_out = pd.DataFrame([crop_factor_stage_dates, crop_factor_stages, harvest_sow_stages, cover_stages, ET_depletion_factor_stages, rooting_depth_stages]).transpose()
        sort_out.columns = ['crop_factor_stage_dates', 'crop_factor_stages', 'harvest_sow_stages', 'cover_stages', 'ET_depletion_factor_stages', 'rooting_depth_stages']
        sort_out.index = sort_out_index
        sort_out = sort_out.sort_values(['crop_factor_stage_dates'])
        sort_out = sort_out.transpose()
        ### interpolation for 0 and 366
        sorted_columns = sort_out.columns
        for interp_var in ['crop_factor_stages', 'cover_stages', 'ET_depletion_factor_stages', 'rooting_depth_stages']:
            sort_out.loc[interp_var, '366'] = np.interp(366, 
                                                              [sort_out.loc['crop_factor_stage_dates', sorted_columns[-2]], sort_out.loc['crop_factor_stage_dates', sorted_columns[1]]+366],
                                                              [sort_out.loc[interp_var, sorted_columns[-2]], sort_out.loc[interp_var, sorted_columns[1]]]
                                                              )
        # havest_sow_stages
        _0_aft = sort_out.loc['harvest_sow_stages', sorted_columns[1]]
        _366_pre = sort_out.loc['harvest_sow_stages', sorted_columns[-2]]
        if [_366_pre, _0_aft] == ['f', 's']:
            sort_out.loc['harvest_sow_stages', '366'] = 'f'
        else:
            sort_out.loc['harvest_sow_stages', '366'] = 'g'
        sort_out['0'] = sort_out['366']
        sort_out.loc['crop_factor_stage_dates','0'] = 0
        
        ### convert to lists
        sort_out_list = []
        for index, rows in sort_out.iterrows():
            sort_out_list.append(rows.to_list())
        [crop_factor_stage_dates, crop_factor_stages, harvest_sow_stages, cover_stages, ET_depletion_factor_stages, rooting_depth_stages] = sort_out_list

        return [crop_factor_stage_dates, crop_factor_stages, harvest_sow_stages, cover_stages, ET_depletion_factor_stages, rooting_depth_stages]
    
    if calendar_type == 'Single':
        ### check whether inputs of the second crop have Nones
        inputs = [kc1_ini, kc1_mid, kc1_end, cc1_s1, cc1_s2, cc1_s3, cc1_s4, cc1_h, p1, Zr1]
        inputs_var = ['kc1_ini', 'kc1_mid', 'kc1_end', 'cc1_s1', 'cc1_s2', 'cc1_s3', 'cc1_s4', 'cc1_h', 'p1', 'Zr1']
        nones = [inputs_var[i] for i, val in enumerate(inputs) if val == None]
        if len(nones) > 1:
            print("ERROR: These variables need input values: " + nones)
        ### sort out the crop calendar in an ascending order
        crop_factor_stage_dates = [0, cc1_s1, cc1_s2, cc1_s3, cc1_s4, cc1_h-1, cc1_h, 366]
        crop_factor_stages = [None, kc1_ini, kc1_ini, kc1_mid, kc1_mid, kc1_end, kc1_ini, None]
        harvest_sow_stages = [None, 's', 'g', 'g', 'g', 'h', 'f', None]
        if cc1_s1 < cc1_s3:
            cc1_s2_cover_stage = np.interp(cc1_s2, [cc1_s1, cc1_s3], [0,1])
        else:
            if cc1_s2 < cc1_s1:
                cc1_s2_cover_stage = np.interp(cc1_s2+366, [cc1_s1, cc1_s3+366], [0,1])
            else:
                cc1_s2_cover_stage = np.interp(cc1_s2, [cc1_s1, cc1_s3+366], [0,1])
        cover_stages = [None, 0, cc1_s2_cover_stage, 1, 1, 1, 0, None]
        ET_depletion_factor_stages = [None, p1, p1, p1, p1, p1, p1, None]
        rooting_depth_stages = [None, Zr1, Zr1, Zr1, Zr1, Zr1, Zr1, None]
        sort_out_index = ['0', 'cc_s1', 'cc_s2', 'cc_s3', 'cc_s4', 'cc_h-1', 'cc_h', '366']
        
    elif calendar_type == 'Double':
        ### check whether inputs of the second crop have Nones
        inputs = [kc1_ini, kc1_mid, kc1_end, cc1_s1, cc1_s2, cc1_s3, cc1_s4, cc1_h, p1, Zr1,
                  kc2_ini, kc2_mid, kc2_end, cc2_s1, cc2_s2, cc2_s3, cc2_s4, cc2_h, p2, Zr2]
        inputs_var = ['kc1_ini', 'kc1_mid', 'kc1_end', 'cc1_s1', 'cc1_s2', 'cc1_s3', 'cc1_s4', 'cc1_h', 'p1', 'Zr1',
                      'kc2_ini', 'kc2_mid', 'kc2_end', 'cc2_s1', 'cc2_s2', 'cc2_s3', 'cc2_s4', 'cc2_h', 'p2', 'Zr2']
        nones = [inputs_var[i] for i, val in enumerate(inputs) if val == None]
        if len(nones) > 1:
            print("ERROR: These variables need input values: " + nones)
        ### It is assumed cc1_s1 must < cc1_s3!
        if cc1_s1 > cc1_h:
            print('ERROR: the first crop calendar in the double cropping must be spring-sown!')
        ### sort out the crop calendar in an ascending order
        crop_factor_stage_dates = [0, cc1_s1, cc1_s2, cc1_s3, cc1_s4, cc1_h-1, cc1_h,
                                      cc2_s1, cc2_s2, cc2_s3, cc2_s4, cc2_h-1, cc2_h, 366]
        crop_factor_stages = [None, kc1_ini, kc1_ini, kc1_mid, kc1_mid, kc1_end, kc1_ini,
                                    kc2_ini, kc2_ini, kc2_mid, kc2_mid, kc2_end, kc2_ini, None]
        harvest_sow_stages = [None, 's', 'g', 'g', 'g', 'h', 'f', 
                                    's', 'g', 'g', 'g', 'h', 'f', None]
        cc1_s2_cover_stage = np.interp(cc1_s2, [cc1_s1, cc1_s3], [0,1]) # CAUTIOUS: it is assumed cc1_s1 must < cc1_s3
        if cc2_s1 < cc2_s3:
            cc2_s2_cover_stage = np.interp(cc2_s2, [cc2_s1, cc2_s3], [0,1])
        else:
            if cc2_s2 < cc2_s1:
                cc2_s2_cover_stage = np.interp(cc2_s2+366, [cc2_s1, cc2_s3+366], [0,1])
            else:
                cc2_s2_cover_stage = np.interp(cc2_s2, [cc2_s1, cc2_s3+366], [0,1])
        cover_stages = [None, 0, cc1_s2_cover_stage, 1, 1, 1, 0,
                              0, cc2_s2_cover_stage, 1, 1, 1, 0, None]
        ET_depletion_factor_stages = [None, p1, p1, p1, p1, p1, p1,
                                            p2, p2, p2, p2, p2, p2, None]
        rooting_depth_stages = [None, Zr1, Zr1, Zr1, Zr1, Zr1, Zr1, 
                                      Zr2, Zr2, Zr2, Zr2, Zr2, Zr2, None]
        sort_out_index = ['0', 'cc1_s1', 'cc1_s2', 'cc1_s3', 'cc1_s4', 'cc1_h-1', 'cc1_h',
                               'cc2_s1', 'cc2_s2', 'cc2_s3', 'cc2_s4', 'cc2_h-1', 'cc2_h', '366']
        
    [crop_factor_stage_dates_, crop_factor_stages_, harvest_sow_stages_, cover_stages_, ET_depletion_factor_stages_, rooting_depth_stages_] = sort_and_interp(crop_factor_stage_dates, 
                                                                                                                                                           crop_factor_stages, 
                                                                                                                                                           harvest_sow_stages, 
                                                                                                                                                           cover_stages, 
                                                                                                                                                           ET_depletion_factor_stages, 
                                                                                                                                                           rooting_depth_stages,
                                                                                                                                                           sort_out_index)

    return [crop_factor_stage_dates_, crop_factor_stages_, harvest_sow_stages_, cover_stages_, ET_depletion_factor_stages_, rooting_depth_stages_]

for i in range(0, len(crop_para.index)):
    
    idx = crop_para.index[i]
    
    name = crop_para.loc[idx, 'Meaning']
    calendar_type = 'Single'
    area = crop_para.loc[idx, 'area'] * 1e6 #[m2]
    kc1_ini = crop_para.loc[idx, 'Kc_ini']
    kc1_mid = crop_para.loc[idx, 'Kc_mid']
    kc1_end = crop_para.loc[idx, 'Kc_end']
    cc1_s1 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s1'], '%Y-%m-%d').timetuple().tm_yday
    cc1_s2 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s2'], '%Y-%m-%d').timetuple().tm_yday
    cc1_s3 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s3'], '%Y-%m-%d').timetuple().tm_yday
    cc1_s4 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_s4'], '%Y-%m-%d').timetuple().tm_yday
    cc1_h = datetime.strptime('2001-'+crop_para.loc[idx, 'cc_h'], '%Y-%m-%d').timetuple().tm_yday
    Zr1 = crop_para.loc[idx, 'Zr']
    p1 = crop_para.loc[idx, 'p']
    kc2_ini = np.nan
    kc2_mid = np.nan
    kc2_end = np.nan
    cc2_s1 = np.nan
    cc2_s2 = np.nan
    cc2_s3 = np.nan
    cc2_s4 = np.nan
    cc2_h = np.nan
    if not np.nan in [cc2_s1, cc2_s2, cc2_s3, cc2_s4, cc2_h]: 
        cc2_s1 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc2_s1'], '%Y-%m-%d').timetuple().tm_yday
        cc2_s2 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc2_s2'], '%Y-%m-%d').timetuple().tm_yday
        cc2_s3 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc2_s3'], '%Y-%m-%d').timetuple().tm_yday
        cc2_s4 = datetime.strptime('2001-'+crop_para.loc[idx, 'cc2_s4'], '%Y-%m-%d').timetuple().tm_yday
        cc2_h = datetime.strptime('2001-'+crop_para.loc[idx, 'cc2_h'], '%Y-%m-%d').timetuple().tm_yday
    Zr2 = np.nan
    p2 = np.nan
    
    [crop_factor_stage_dates, crop_factor_stages, harvest_sow_stages, cover_stages, ET_depletion_factor_stages, rooting_depth_stages] = generate_crop_calendar(
        calendar_type,
        kc1_ini,
        kc1_mid,
        kc1_end,
        cc1_s1,
        cc1_s2,
        cc1_s3,
        cc1_s4,
        cc1_h,
        Zr1,
        p1,
        kc2_ini,
        kc2_mid,
        kc2_end,
        cc2_s1,
        cc2_s2,
        cc2_s3,
        cc2_s4,
        cc2_h,
        Zr2,
        p2
        )
    
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
               'rooting_depth_stages' : rooting_depth_stages,
               'crop_factor_stage_dates' : crop_factor_stage_dates,
               'crop_factor_stages' : crop_factor_stages,
               'harvest_sow_stages' : harvest_sow_stages,
               'cover_stages' : cover_stages,
               'ET_depletion_factor_stages' : ET_depletion_factor_stages,
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

# plot surface results
surface_name = 'my_growing_surface2'
surface_vars = [#'et0_coef',
               #'crop_factor',
               #'et_depletion_factor',
               #'rooting_depth',
               #'crop_cover',
               'evaporation',
               'precipitation',
               'storage'
                ]
for surface_var in surface_vars:
    f, axs = plt.subplots()
    x = surfaces.groupby('surface').get_group(surface_name).set_index('time').index
    y = surfaces.groupby('surface').get_group(surface_name).set_index('time')[surface_var]
    axs.plot(x, y)
    axs.set_ylabel(surface_var + ' at '+ surface_name)