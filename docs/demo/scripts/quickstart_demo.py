# -*- coding: utf-8 -*-
"""
Created on Fri Oct 28 08:52:22 2022

@author: Barney
"""

from numpy.random import random
from wsimod.orchestration.model import Model
from wsimod.core import constants
import os
import pandas as pd
from matplotlib import pyplot as plt

# In[2]:


"""Load input data
"""
data_folder= os.path.join(os.path.dirname(
                               os.path.abspath('')),
                          "data")

input_fid = os.path.join(data_folder, "processed", "timeseries_data.csv")
input_data = pd.read_csv(input_fid)
input_data.date = pd.to_datetime(input_data.date)

dates = input_data.date.drop_duplicates()
dates_monthyear = input_data.date.dt.to_period('M').unique()
print(input_data.sample(10))

# In[]:
"""I didn't create evapotranspiration data for this demo,
so we will make up some fake data
"""
#Precipitation and evapotranspiration timeseries are in m/m2/d
def create_timeseries(amount, dates, variable):
    df = pd.DataFrame(index = dates, columns = ['date','variable', 'value'])
    df['date'] = dates
    df['variable'] = variable
    df['value'] = amount
    return df.set_index(['variable','date']).value.to_dict()

evaporation_timeseries = create_timeseries(1 * constants.MM_TO_M,
                                           dates = dates.values,
                                           variable = 'et0')


precipitation_timeseries = input_data.groupby('site').get_group('oxford_land').set_index(['variable','date']).value.mul(constants.MM_TO_M).to_dict()
#(temperature should be air temperature but I didn't have time to format it)
temperature_timeseries = input_data.loc[input_data.variable == 'temperature'].groupby(['site','date']).mean()
temperature_timeseries['variable'] = 'temperature'
temperature_timeseries = temperature_timeseries.reset_index().set_index(['variable','date']).value.to_dict()

land_inputs = {**evaporation_timeseries,
               **precipitation_timeseries,
               **temperature_timeseries}

# In[]

"""Nodes can be defined as dictionaries of parameters
"""

sewer = {'type_' : 'Sewer',
         'capacity' : 2,
         'name' : 'my_sewer'}

surface1 = {'type_' : 'Impervious',
           'area' : 10,
           'pollutant_load' : {'phosphate' : 1e-7}}
surface2 = {'type_' : 'Pervious',
            'area' : 10,
            'pollutant_load' : {'phosphate' : 1e-7}}
            
land = {'type_' : 'Land',
        'data_input_dict' : land_inputs,
        'surfaces' : [surface1, 
                      surface2]}

