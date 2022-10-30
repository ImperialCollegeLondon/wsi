#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""Import packages
"""
from wsimod.nodes.waste import Waste
from wsimod.nodes.land import Land
from wsimod.nodes.nodes import Node
from wsimod.nodes.storage import Groundwater
from wsimod.orchestration.model import Model
from wsimod.arcs.arcs import Arc
from wsimod.core import constants
import os
import pandas as pd
from matplotlib import pyplot as plt

#Make plots interative
# get_ipython().run_line_magic('matplotlib', 'notebook')


# In[2]:


"""Load input data
"""
data_folder= os.path.join(os.path.abspath(''),
                               "docs","demo","data")

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

# In[3]:
example_date = pd.to_datetime('2009-03-03')

print(land_inputs[('precipitation',example_date)])
print(land_inputs[('et0',example_date)])
print(land_inputs[('temperature',example_date)])


# In[4]:
constants.set_simple_pollutants()

print(constants.POLLUTANTS)


# In[5]:
"""Create a simple Land node with one basic surface
"""
#We can pass surfaces as a dictionary when creating a Land node
surface = {'type_' : 'Surface',
           'surface' : 'my_surface',
           'area' : 10,
           'depth' : 1,
           'pollutant_load' : {'phosphate' : 1e-7}}

land = Land(name = 'my_land',
            data_input_dict = land_inputs,
            surfaces = [surface])

#Each surface object is stored in a list of surfaces within the land node
print(land.surfaces[0])

#We can also access a specific surface by name
print(land.get_surface('my_surface'))

#This surface will have all the data we passed to the land node in a dict
print(land.get_surface('my_surface').area)
print(land.get_surface('my_surface').pollutant_load)

#A surface is a generic tank, by default it is initialised as empty
print(land.get_surface('my_surface').storage)


# In[6]:

"""Run a timestep of the land node
"""
land.t = example_date
land.monthyear = land.t.to_period('M')
land.run()

#We see that a day of phosphate deposition has occured on the surface
print(land.get_surface('my_surface').storage)

#The run function in land simply calls the run function in all of its surfaces
land.get_surface('my_surface').run()

#We see that another day of phosphate deposition has occured on the surface
print(land.get_surface('my_surface').storage)

#However... no precipitation has occurred, despite there being rainfall!
print(land.get_data_input('precipitation'))

#The 'run' function in the surface calls all of the functions stored in the
#'inflows' property, then 'processes', then 'outflows'
print(land.get_surface('my_surface').inflows)
print(land.get_surface('my_surface').processes)
print(land.get_surface('my_surface').outflows)

#Only some simple deposition occurs on the basic surface... 
#we need a specific type of surface!

# In[7]:
"""Creating a pervious surface
"""
surface = {'type_' : 'PerviousSurface',
           'surface' : 'my_surface',
           'area' : 10,
           'depth' : 0.5,
           'pollutant_load' : {'phosphate' : 1e-7},
           'wilting_point' : 0.05,
           'field_capacity' : 0.1
           }

land = Land(name = 'my_land',
            data_input_dict = land_inputs,
            surfaces = [surface])

#We have lots of functions now! You will have to look at the documentation of
#PerviousSurface to understand them in detail
print(land.get_surface('my_surface').inflows)
print(land.get_surface('my_surface').processes)
print(land.get_surface('my_surface').outflows)

#But for sure we can see that some rain has happened
land.t = example_date
land.monthyear = land.t.to_period('M')
land.run()
print(land.get_surface('my_surface').storage)

# In[ ]:

"""The pervious surface runs the IHACRES model
"""
#Eventually, when the surface has enough water in, other things will happen
#We will run the surface again to make the same rain happen a few more times and 
#start to fill the surface up with water
for i in range(10):
    land.get_surface('my_surface').run()

#There's now a lot of water in the tank
print(land.get_surface('my_surface').storage)

#Critically, we see that the moisture content than 0.1 (i.e., the field capacity depth)
print(land.get_surface('my_surface').get_smc() / land.get_surface('my_surface').depth)

#Once soil moisture content is greater than the field capacity, flows will be generated
#(this is how IHACRES works)
#These tanks represent flow from the soil layer to either rivers or groundwater
print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)

# In[ ]:

"""WSIMOD expects land to be able to route flows onwards
"""

#Since the land isn't connected to anything
#these won't actually go anywhere if we run it, and they will just build up
for i in range(10):
    land.run()

print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)

#We can create and connect up nodes to make a simple model
node = Node(name = 'my_river')
gw = Groundwater(name = 'my_groundwater',
                 area = 10,
                 capacity = 100)
outlet = Waste(name = 'my_outlet')

arc1 = Arc(in_port = land, out_port = node, name = 'quickflow')
arc2 = Arc(in_port = land, out_port = gw, name = 'percolation')
arc3 = Arc(in_port = gw, out_port = node, name = 'baseflow')
arc4 = Arc(in_port = node, out_port = outlet, name = 'outflow')



#If we run the land a few more times, we see that these tanks start to empty
#(though percolation by nature empties rather slowly!!!)
for i in range(10):
    land.run()

print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)

# In[ ]:
"""We can put these nodes and arcs into the Model object to have a functioning
hydrological model
"""

#Create the model object
my_model = Model()

#Since we have already created our nodes/arcs, we use the add_instantiated functions
my_model.add_instantiated_nodes([land,node,gw,outlet])
my_model.add_instantiated_arcs([arc1,arc2,arc3,arc4])

#Store dates
my_model.dates = dates

#Reinitialise values (I am aware I need a tidier way to do this)
my_model.reinit()
my_model.nodes['my_land'].surface_runoff.storage = land.empty_vqip()
my_model.nodes['my_land'].subsurface_runoff.storage = land.empty_vqip()
my_model.nodes['my_land'].percolation.storage = land.empty_vqip()
my_model.nodes['my_land'].surfaces[0].storage = land.empty_vqip()
my_model.nodes['my_groundwater'].tank.storage = land.empty_vqip()

#Run the model
results = my_model.run()

#Plot the results
flows = pd.DataFrame(results[0])

f, axs = plt.subplots(2,1)
flows.groupby('arc').get_group('outflow').set_index('time').flow.plot(ax=axs[0])
flows.groupby('arc').get_group('outflow').set_index('time').phosphate.plot(ax=axs[1])


# In[ ]:
"""Hydrology is nice, but anyone using WSIMOD probably isn't interested in 
hydrology only! The GrowingSurface adds a lot of sophisticated behaviour for
agriculture and water quality
"""


# In[ ]:
"""Our GrowingSurface needs a bit more data than other surfaces, for fertiliser,
manure and atmospheric deposition of ammonia, nitrate and phosphate. 
We will make up this data.
"""
#Surface pollution data varies at a monthly timestep rather than daily, 
#though it is applied each day
surface_input_data = {}
for pollutant in ['srp','nhx','noy']:
    for source in ['manure','fertiliser','dry','wet']:
        amount = 1e-7 # kg/m2/timestep
        ts = create_timeseries(amount, dates_monthyear, '{0}-{1}'.format(pollutant, source))
        surface_input_data = {**surface_input_data, **ts}

print(surface_input_data[('nhx-manure',example_date.to_period('M'))])

# In[ ]:
"""Create a growing surface
"""
#There are a lot of parameters, see the documentation, but I will use
#the parameters for Maize for this growing surface
crop_factor_stages = [0.   , 0.   , 0.3  , 0.3  , 1.2  , 1.2  , 0.325, 0.   , 0.   ]
crop_factor_stage_dates =[  0,  90,  91, 121, 161, 213, 244, 245, 366]
sowing_day = 91
harvest_day = 244
ET_depletion_factor = 0.55
rooting_depth = 0.5

constants.set_default_pollutants()

surface = {'type_' : 'GrowingSurface',
           'surface' : 'my_growing_surface',
           'area' : 10,
           'rooting_depth' : rooting_depth,
           'crop_factor_stage_dates' : crop_factor_stage_dates,
           'crop_factor_stages' : crop_factor_stages,
           'sowing_day' : sowing_day,
           'harvest_day' : harvest_day,
           'ET_depletion_factor' : ET_depletion_factor,
           'data_input_dict' : surface_input_data,
           'wilting_point' : 0.05,
           'field_capacity' : 0.1
           }

land = Land(name = 'my_land',
            data_input_dict = land_inputs,
            surfaces = [surface])

#We see that the inflows includes IHACRES from the pervious surface
#But has also added a range of other functions related to deposition of 
#pollution
print(land.get_surface('my_growing_surface').inflows)

#And with bio-chemical processes occurring within nutrient pools
print(land.get_surface('my_growing_surface').processes)

# In[ ]:

"""Let's recreate our model with this Maize surface
"""
node = Node(name = 'my_river')
gw = Groundwater(name = 'my_groundwater',
                 area = 10,
                 capacity = 100)
outlet = Waste(name = 'my_outlet')

arc1 = Arc(in_port = land, out_port = node, name = 'quickflow')
arc2 = Arc(in_port = land, out_port = gw, name = 'percolation')
arc3 = Arc(in_port = gw, out_port = node, name = 'baseflow')
arc4 = Arc(in_port = node, out_port = outlet, name = 'outflow')
my_model = Model()

#Since we have already created our nodes/arcs, we use the add_instantiated functions
my_model.add_instantiated_nodes([land,node,gw,outlet])
my_model.add_instantiated_arcs([arc1,arc2,arc3,arc4])

#Store dates
my_model.dates = dates

#Run the model
results = my_model.run()

# In[ ]:

"""Observe the differences between the two sets of timeseries:
    Flows look more or less the same (dynamically), which makes sense since they
    both use IHACRES for hydrology. Only small differences will arise because
    the crops change the evapotranspiration coefficient
    
    Meanwhile, phosphate levels look much more interesting with the 
    GrowingSurface, and are not solely dependent on the hydrology
"""

#Plot the results
flows = pd.DataFrame(results[0])

f, axs = plt.subplots(2,1)
flows.groupby('arc').get_group('outflow').set_index('time').flow.plot(ax=axs[0])
flows.groupby('arc').get_group('outflow').set_index('time').phosphate.plot(ax=axs[1])

