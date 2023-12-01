# %% [markdown]
# # Land nodes - hydrology and agriculture (.py)
#
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/land_demo.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Data](#imports-and-forcing-data)
#
# 3. [Basic surface](#basic-surface)
#
# 4. [Pervious surface](#pervious-surface)
#
# 5. [Connecting land nodes in a model](#connecting-land-nodes-in-a-model)
#
#     5.1 [Model object](#model-object)
#
# 6. [Growing surface](#growing-surface)
#
# %% [markdown]
# ## Introduction
#
# A land node is the object that interfaces with other WSIMOD nodes.
# Each land node can have one or more surfaces.
# Each surface can be parameterised differently or follow different equations,
# similar to the hyrological response unit concept in hydrological models.
#
# The different surfaces within WSIMOD are used to capture hydrological,
# agricultural, and urban runoff processes. In this demo we will see how they
# all work.
#
# %% [markdown]
# ## Imports and forcing data

# %% [markdown]
# Import packages
# %%

import os

import pandas as pd
from matplotlib import pyplot as plt

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.demo.create_oxford import create_timeseries
from wsimod.nodes.land import Land
from wsimod.nodes.nodes import Node
from wsimod.nodes.storage import Groundwater
from wsimod.nodes.waste import Waste
from wsimod.orchestration.model import Model

# %% [markdown]
# Load input data
# %%

# Select the root path for the data folder. Use the appropriate value for your case.
data_folder = os.path.join(os.path.abspath(""), "docs", "demo", "data")

input_fid = os.path.join(data_folder, "processed", "timeseries_data.csv")
input_data = pd.read_csv(input_fid)
input_data.loc[input_data.variable == "flow", "value"] *= constants.M3_S_TO_M3_DT
input_data.loc[input_data.variable == "precipitation", "value"] *= constants.MM_TO_M
input_data.date = pd.to_datetime(input_data.date)
data_input_dict = input_data.set_index(["variable", "date"]).value.to_dict()
data_input_dict = (
    input_data.groupby("site")
    .apply(lambda x: x.set_index(["variable", "date"]).value.to_dict())
    .to_dict()
)

dates = input_data.date.drop_duplicates()
dates_monthyear = input_data.date.dt.to_period("M").unique()
print(input_data.sample(10))

# %% [markdown]
# Input data is stored in dicts
# %%

land_inputs = data_input_dict["oxford_land"]

example_date = pd.to_datetime("2009-03-03")

print(land_inputs[("precipitation", example_date)])
print(land_inputs[("et0", example_date)])
print(land_inputs[("temperature", example_date)])


# %% [markdown]
# We are just using some basic pollutants for demonstration
# %%

constants.set_simple_pollutants()

print(constants.POLLUTANTS)


# %% [markdown]
# ## Basic surface

# %% [markdown]
# Create a simple [Land node](./../../../reference-land/#wsimod.nodes.land.Land)
# with one [basic surface](./../../../reference-land/#wsimod.nodes.land.Surface).
# We can pass surfaces as a dictionary when creating a Land node.
# %%
surface = {
    "type_": "Surface",
    "surface": "my_surface",
    "area": 10,
    "depth": 1,
    "pollutant_load": {"phosphate": 1e-7},
}

land = Land(name="my_land", data_input_dict=land_inputs, surfaces=[surface])

# %% [markdown]
# Each surface object is stored in a list of surfaces within the land node.
# %%
print(land.surfaces[0])

# %% [markdown]
# We can also access a specific surface by name.
# %%
print(land.get_surface("my_surface"))

# %% [markdown]
# This surface will have all the data we passed to the land node in a dict.
# %%
print(land.get_surface("my_surface").area)
print(land.get_surface("my_surface").pollutant_load)

# %% [markdown]
# A surface is a generic tank, by default it is initialised as empty.
# %%
print(land.get_surface("my_surface").storage)


# %% [markdown]
# Let's try to run a timestep for a land node
# %%
land.t = example_date
land.monthyear = land.t.to_period("M")
land.run()


# %% [markdown]
# We see that a day of phosphate deposition has occured on the surface.
# %%
print(land.get_surface("my_surface").storage)

# %% [markdown]
# The run function in land simply calls the run function in all of its surfaces.
# %%

land.get_surface("my_surface").run()

# %% [markdown]
# After running the surface, we see that another day of phosphate deposition
# has occured.
# %%

print(land.get_surface("my_surface").storage)


# %% [markdown]
# However... no precipitation has occurred (no volume above),
# despite there being rainfall!
# %%
print(land.get_data_input("precipitation"))

# %% [markdown]
# To understand why this is, we have to understand how the 'run' function in a
# surface works. Each surface has a list of functions stored in 'inflows', in
# 'processes', and in 'outflows'. When 'run' is called, all of the functions in
# inflows are executed, then processes, then outflows.
#
# If we print the lists of functions, we see only some simple deposition occurs
# on the basic surface in the inflows...
# %%

print(land.get_surface("my_surface").inflows)
print(land.get_surface("my_surface").processes)
print(land.get_surface("my_surface").outflows)

# %% [markdown]
# We need a specific subclass of surface to implement more sophisticated
# hydrological processes!
#
# %% [markdown]
# ## Pervious surface

# %% [markdown]
# The pervious surface contains a simple lumped hydrological model.
#
# We can create the surface, again via parameters stored in a dictionary that
# is passed to the Land node.
# is passed to the Land node. Note that the subclass of surface to be created
# must be specified by the `type_` keyword.
# %%
surface = {
    "type_": "PerviousSurface",
    "surface": "my_surface",
    "area": 10,
    "depth": 0.5,
    "pollutant_load": {"phosphate": 1e-7},
    "wilting_point": 0.05,
    "field_capacity": 0.1,
}

land = Land(name="my_land", data_input_dict=land_inputs, surfaces=[surface])

# %% [markdown]
# We have lots of functions now! You will have to look at the documentation of
# [PerviousSurface](./../../../reference-land/#wsimod.nodes.land.PerviousSurface)
# to understand them in detail
#
# We note that the function 'ihacres' in the inflows is the hydrological
# processes representation, using equations based off the IHACRES model.
# If a user preferred to use a different hydrological model, they would simply
# need to substitute out this function in the inflows list.
# %%

print(land.get_surface("my_surface").inflows)
print(land.get_surface("my_surface").processes)
print(land.get_surface("my_surface").outflows)

# %% [markdown]
# Now when we run the model, we can see that some rain has happened, because the
# storage volume has increased (as well as the deposition).
# %%
land.t = example_date
land.monthyear = land.t.to_period("M")
land.run()
print(land.get_surface("my_surface").storage)

# %% [markdown]
# However, if we look at the land node, which is the parent of the surfaces that
# interfaces with other WSIMOD components, we see that all of its tanks are still
# empty.
# %%
print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)

# %% [markdown]
# This is because the IHACRES model requires soil moisture to be more than a
# specified amount (the field capacity) for flows to be generated.
#
# We can run the surface multiple times to fill it up with water.
# %%
for i in range(10):
    land.get_surface("my_surface").run()

# %% [markdown]
# There's now a lot of water in the tank
# %%
print(land.get_surface("my_surface").storage)


# %% [markdown]
# Critically, we see that the moisture content is greater than 0.1
# (i.e., the field capacity moisture content)
# %%
print(land.get_surface("my_surface").get_smc() / land.get_surface("my_surface").depth)

# %% [markdown]
# Once soil moisture content is greater than the field capacity,
# flows will be generated and the land tanks will fill up.
# %%
print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)


# %% [markdown]
# These tanks represent flow from the soil layer to either rivers or groundwater.
# However, land nodes expect to be able to route flow onwards to other nodes.
#
# Since the land isn't connected to anything, these won't actually go anywhere
# if we run it, and they will just build up
# %%
for i in range(10):
    land.run()

print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)

# %% [markdown]
# ## Connecting land nodes in a model
# As mentioned, the land node expects to be able to discharge to [groundwater](./../../../reference-storage/#wsimod.nodes.storage.Groundwater),
# and rivers (where a river could be the
# [River node](./../../../reference-storage/#wsimod.nodes.storage.River)
# or just a generic [Node](./../../../reference-nodes/#wsimod.nodes.nodes.Node)).
# We also provide a [Waste node](./../../../reference-other/#wsimod.nodes.waste.Waste),
# which is just a model outlet.
# %%
node = Node(name="my_river")
gw = Groundwater(name="my_groundwater", area=10, capacity=100)
outlet = Waste(name="my_outlet")

# %% [markdown]
# We use [arcs](./../../../reference-arc/#wsimod.arcs.arcs.Arc) to join up all of the different nodes according to a standard
# hydrological representation.
# %%
arc1 = Arc(in_port=land, out_port=node, name="quickflow")
arc2 = Arc(in_port=land, out_port=gw, name="percolation")
arc3 = Arc(in_port=gw, out_port=node, name="baseflow")
arc4 = Arc(in_port=node, out_port=outlet, name="outflow")

# %% [markdown]
# If we run the land a few more times, we see that these tanks start to empty
# (though percolation by nature empties rather slowly!!!)
# %%

for i in range(10):
    land.run()

print(land.percolation.storage)
print(land.subsurface_runoff.storage)
print(land.surface_runoff.storage)

# %% [markdown]
# ### Model object
# We can put these nodes and arcs into the [Model object](./../../../reference-model/#wsimod.orchestration.model.Model)
# to have a functioning hydrological model.
#
# We start by creating a model object.
# %%

my_model = Model()

# %% [markdown]
# Since we have already created our nodes/arcs, we use the add_instantiated functions
# %%
my_model.add_instantiated_nodes([land, node, gw, outlet])
my_model.add_instantiated_arcs([arc1, arc2, arc3, arc4])

# %% [markdown]
# Store dates
# %%
my_model.dates = dates

# %% [markdown]
# We have run the surfaces a few times, so will just set all of the model tanks
# to empty to give a clean start for the model.
# %%
my_model.reinit()

# %% [markdown]
# We can run the model with the run function
# %%
results = my_model.run()

# %% [markdown]
# .. and plot the results!
# %%
flows = pd.DataFrame(results[0])

f, axs = plt.subplots(2, 1)
flows.groupby("arc").get_group("outflow").set_index("time").flow.plot(ax=axs[0])
flows.groupby("arc").get_group("outflow").set_index("time").phosphate.plot(ax=axs[1])

# %% [markdown]
# ## Growing surface
# Hydrology is nice, but anyone using WSIMOD probably isn't interested in
# hydrology only! The GrowingSurface adds a lot of sophisticated behaviour for
# agriculture and water quality.
#
# Our GrowingSurface needs a bit more data than other surfaces, for fertiliser,
# manure and atmospheric deposition of ammonia, nitrate and phosphate.
# We will make up this data.
#
# Surface pollution data varies at a monthly timestep rather than daily,
# though it is applied each day.
# %%

surface_input_data = {}
for pollutant in ["srp", "nhx", "noy"]:
    for source in ["manure", "fertiliser", "dry", "wet"]:
        amount = 1e-7  # kg/m2/timestep
        ts = create_timeseries(
            amount, dates_monthyear, "{0}-{1}".format(pollutant, source)
        )
        ts = ts.set_index(["variable", "date"]).value.to_dict()
        surface_input_data = {**surface_input_data, **ts}

print(surface_input_data[("nhx-manure", example_date.to_period("M"))])

# %% [markdown]
# Because the surface represents the nitrogen and phosphorus cycles, we need
# to simulate a greater number of pollutants
# %%
constants.set_default_pollutants()

# %% [markdown]
# As with the other surfaces, we create the surface by passing it as a dictionary
# to the created Land node. I will use the parameters for Maize for this growing surface
# %%
crop_factor_stages = [0.0, 0.0, 0.3, 0.3, 1.2, 1.2, 0.325, 0.0, 0.0]
crop_factor_stage_dates = [0, 90, 91, 121, 161, 213, 244, 245, 366]
sowing_day = 91
harvest_day = 244
ET_depletion_factor = 0.55
rooting_depth = 0.5

surface = {
    "type_": "GrowingSurface",
    "surface": "my_growing_surface",
    "area": 10,
    "rooting_depth": rooting_depth,
    "crop_factor_stage_dates": crop_factor_stage_dates,
    "crop_factor_stages": crop_factor_stages,
    "sowing_day": sowing_day,
    "harvest_day": harvest_day,
    "ET_depletion_factor": ET_depletion_factor,
    "data_input_dict": surface_input_data,
    "wilting_point": 0.05,
    "field_capacity": 0.1,
}

land = Land(name="my_land", data_input_dict=land_inputs, surfaces=[surface])

# %% [markdown]
# We see that the inflows includes IHACRES from the pervious surface.
# But has also added a range of other functions related to deposition.
# %%
print(land.get_surface("my_growing_surface").inflows)

# %% [markdown]
# And in particular with the bio-chemical processes occurring within nutrient pools
# %%
print(land.get_surface("my_growing_surface").processes)

# %% [markdown]
# Let's recreate our model with this Maize surface and run the model
# %%
node = Node(name="my_river")
gw = Groundwater(name="my_groundwater", area=10, capacity=100)
outlet = Waste(name="my_outlet")

arc1 = Arc(in_port=land, out_port=node, name="quickflow")
arc2 = Arc(in_port=land, out_port=gw, name="percolation")
arc3 = Arc(in_port=gw, out_port=node, name="baseflow")
arc4 = Arc(in_port=node, out_port=outlet, name="outflow")
my_model = Model()

my_model.add_instantiated_nodes([land, node, gw, outlet])
my_model.add_instantiated_arcs([arc1, arc2, arc3, arc4])

my_model.dates = dates

results = my_model.run()

# %% [markdown]
# We can now plot the results
# %%

flows = pd.DataFrame(results[0])

f, axs = plt.subplots(2, 1)
flows.groupby("arc").get_group("outflow").set_index("time").flow.plot(ax=axs[0])
flows.groupby("arc").get_group("outflow").set_index("time").phosphate.plot(ax=axs[1])

# %% [markdown]
# Observe the differences between the two sets of timeseries:
# Flows look more or less the same (dynamically), which makes sense since they
# both use IHACRES for hydrology. Only small differences will arise because
# the crops change the evapotranspiration coefficient
#
# Meanwhile, phosphate levels look much more interesting with the
# GrowingSurface, and are not solely dependent on the hydrology.
