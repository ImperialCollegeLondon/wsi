# -*- coding: utf-8 -*-
"""
Created on Tue Nov 16 14:15:13 2021

@author: bdobson
"""
import pandas as pd
import os
import re
from wsimod.preprocessing.geoprocessing_tools import create_timeseries
data_dir = os.path.join(
               os.path.dirname(
                  os.path.dirname(
                      os.path.dirname(
                          os.path.abspath(__file__)))),
               "demo",
                "data")


UG_L_TO_KG_M3 = 1e-6
MG_L_TO_KG_M3 = 1e-3

q_lab = [('39008_gdf.csv','thames'),
         ('39034_gdf.csv','evenlode'),
         ('39021_gdf.csv','cherwell'),
         ('39140_gdf.csv','ray')
         ]
          
flows = []
for fn, river in q_lab:
    df = pd.read_csv(os.path.join(data_dir, "raw", fn), skiprows=19, error_bad_lines=False)
    if df.shape[1] == 2:
        df.columns = ['date', 'flow']
    else:
        df.columns = ['date', 'flow', 'missing']
    df['site'] = river
    flows.append(df)
    
flows = pd.concat(flows)
flows = flows.pivot(columns = 'site', index = 'date', values = 'flow')
flows.index = pd.to_datetime(flows.index)

wq_data = pd.read_csv(os.path.join(data_dir, "raw", "CEHThamesInitiative_WaterQualityData_2009-2013.csv"))

rain = pd.read_csv(os.path.join(data_dir, "raw", "39008_cdr.csv"), skiprows=19, error_bad_lines=False)
rain.columns = ['date','value','misc']
rain['site'] = 'oxford_land'
rain['variable'] = 'precipitation'
rain = rain.drop('misc', axis = 1)
rain.date = pd.to_datetime(rain.date)

sites = {'River Thames at Swinford' : 'thames',
         'River Evenlode at Cassington Mill' : 'evenlode',
         'River Ray at Islip' : 'ray',
         'River Cherwell at Hampton Poyle' : 'cherwell'}
wq = wq_data.loc[wq_data.Site.isin(sites.keys())]
wq['Sampling date (dd/mm/yyyy)'] = pd.to_datetime(wq['Sampling date (dd/mm/yyyy)'], format="%d/%m/%Y")
wq = wq.rename(columns = {'Sampling date (dd/mm/yyyy)' : 'date',
                          'Site' : 'site'})

wq.site = [sites[x] for x in wq.site]

wq = wq.set_index('date').drop('Sampling time (hh:mm)', axis = 1)
wq[wq.columns.drop('site')] = wq[wq.columns.drop('site')].apply(lambda x : pd.to_numeric(x, errors='coerce'))
wq = wq.dropna(axis=1, how='any')
wq = wq.drop('Mean daily river discharge (m3 s-1)', axis = 1)
wq = wq.groupby('site').resample('d').interpolate().drop('site', axis = 1)
wq = wq.reset_index()
wq.loc[:,wq.columns.str.contains('ug')] *= UG_L_TO_KG_M3
wq.loc[:,wq.columns.str.contains('mg')] *= MG_L_TO_KG_M3

columns = []
for pol in wq.columns.unique():
    text = pol.lower()
    for sub in ['water','dissolved','total',' ', r"\(.*\)"]:
        text = re.sub(sub, '', text)
    columns.append(text)
wq.columns = columns

#Convert to nitrate as N
wq['nitrate'] /= 4.43

#Convert to Silica as SiO2
wq['silicon'] *= 2.14

wq = wq.melt(id_vars = ['site', 'date'])

# wq.date = pd.to_datetime(wq.date.dt.date)

flows = flows.loc[flows.index.isin(wq.date)]
flows = flows.unstack().rename('value').reset_index()
flows['variable'] = 'flow'

rain = rain.loc[rain.date.isin(wq.date)]
evaporation = create_timeseries(2 / 1000, rain.date, 'et0')
evaporation['site'] = 'oxford_land'

temperature_ = wq.loc[wq.variable == 'temperature'].groupby('date').mean().reset_index()
temperature_['site'] = 'oxford_land'
temperature_['variable'] = 'temperature'

input_data = pd.concat([wq, flows, rain, evaporation, temperature_], axis = 0)
input_data.to_csv(os.path.join(data_dir, "processed", "timeseries_data.csv"), index = False)