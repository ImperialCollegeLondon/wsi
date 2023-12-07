# %% [markdown]
# # WSIMOD model demonstration - Oxford (.py)
#
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/oxford_demo.py)
#
# 1. [Introduction](#we-will-cover-a-demo-wsimod-case-study)
#
# 2. [Data](#imports-and-forcing-data)
#
# 3. [Nodes](#create-nodes)
#
#     3.1 [Freshwater Treatment Works](#freshwater-treatment-works)
#
#     3.2 [Land](#land)
#
#     3.3 [Demand](#residential-demand)
#
#     3.4 [Reservoir](#reservoir)
#
#     3.5 [Distribution](#distribution)
#
#     3.6 [Wastewater Treatment Works](#wastewater-treatment-works)
#
#     3.7 [Sewers](#sewers)
#
#     3.8 [Groundwater](#groundwater)
#
#     3.9 [Node list](#create-a-nodelist)
#
# 4. [Arcs](#arcs)
#
#     4.1 [Arc parameters](#arc-parameters)
#
#     4.2 [Create the arcs](#create-arcs)
#
# 5. [Mapping](#mapping)
#
# 6. [Orchestration](#orchestration)
#
#     6.1 [Orchestrating an individual timestep](#orchestrating-an-individual-timestep)
#
#     6.2 [Ending a timestep](#ending-to-timestep)
#
# 7. [Model object](#model-object)
#
#     7.1 [Validation](#validation-plots)
# %% [markdown]
# ## We will cover a demo WSIMOD case study
#
# The glamorous town of Oxford will be our demo case study.
# Below, we will create these nodes and arcs, orchestrate them into a model, and run simulations.
#
# ![alt text](./../images/oxford.svg)
#
# Although GIS is pretty, the schematic below is a more accurate representation of what will be created.
# WSIMOD treats everything as a node or an arc.
#
# ![alt text](./../images/schematic.svg)
#

# %% [markdown]
# ## Imports and forcing data

# %% [markdown]
# Import packages
# %%

import os

import pandas as pd

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.catchment import Catchment
from wsimod.nodes.demand import ResidentialDemand
from wsimod.nodes.land import Land
from wsimod.nodes.nodes import Node
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.storage import Groundwater, Reservoir
from wsimod.nodes.waste import Waste
from wsimod.nodes.wtw import FWTW, WWTW
from wsimod.orchestration.model import Model

os.environ["USE_PYGEOS"] = "0"
import geopandas as gpd
from matplotlib import pyplot as plt
from shapely.geometry import LineString

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
print(input_data.sample(10))

# %% [markdown]
# Input data is stored in dicts
# %%


print(data_input_dict["cherwell"][("boron", pd.to_datetime("2010-11-20"))])

# %% [markdown]
# We select dates that are available in the input data

# %%


dates = input_data.date.unique()
dates = dates[dates.argsort()]
dates = [pd.Timestamp(x) for x in dates]
print(dates[0:10])
# %% [markdown]
# We can specify the pollutants.
# In this example we choose based on what pollutants we have input data for.
# %%


constants.POLLUTANTS = input_data.variable.unique().tolist()
constants.POLLUTANTS.remove("flow")
constants.POLLUTANTS.remove("precipitation")
constants.POLLUTANTS.remove("et0")
constants.NON_ADDITIVE_POLLUTANTS = ["temperature"]
constants.ADDITIVE_POLLUTANTS = list(
    set(constants.POLLUTANTS).difference(constants.NON_ADDITIVE_POLLUTANTS)
)
constants.FLOAT_ACCURACY = 1e-11
print(constants.POLLUTANTS)


# %% [markdown]
# ## Create nodes

# %% [markdown]
# For [waste nodes](./../../../reference-other/#wsimod.nodes.waste.Waste),
# no parameters are needed, they are just the model outlet
# %%
thames_above_abingdon = Waste(name="thames_above_abingdon")

# %% [markdown]
# For junctions and abstraction locations, we can simply use the default
# [nodes](./../../../reference-nodes/#wsimod.nodes.nodes.Node)
# %%
farmoor_abstraction = Node(name="farmoor_abstraction")
evenlode_thames = Node(name="evenlode_thames")
cherwell_ray = Node(name="cherwell_ray")
cherwell_thames = Node(name="cherwell_thames")
thames_mixer = Node(name="thames_mixer")

# %% [markdown]
# For [catchment nodes](./../../../reference-other/#wsimod.nodes.catchment.Catchment),
# we only need to specify the input data (as a dictionary format).
# %%
evenlode = Catchment(name="evenlode", data_input_dict=data_input_dict["evenlode"])
thames = Catchment(name="thames", data_input_dict=data_input_dict["thames"])
ray = Catchment(name="ray", data_input_dict=data_input_dict["ray"])
cherwell = Catchment(name="cherwell", data_input_dict=data_input_dict["cherwell"])


# %% [markdown]
# We can see that, even though we provided mimimal information (name and input data) each node comes with many predefined functions.
# %%
print(dir(evenlode))

# %% [markdown]
# ### Freshwater treatment works
# Each type of node uses different parameters (see [API reference](./../../../../reference)).
# Below we create a [freshwater treatment works (FWTW)](./../../../reference-wtw/#wsimod.nodes.wtw.FWTW)

# %%

oxford_fwtw = FWTW(
    service_reservoir_storage_capacity=1e5,
    service_reservoir_storage_area=2e4,
    treatment_throughput_capacity=4.5e4,
    name="oxford_fwtw",
)

# %% [markdown]
# Each node type has different types of functionality available
# %%

print(dir(oxford_fwtw))

# %% [markdown]
# The FWTW node has a tank representing the service reservoirs, we can see that it has been initialised empty.

# %%

print(oxford_fwtw.service_reservoir_tank.storage)

# %% [markdown]
# If we try to pull water from the FWTW, it responds that there is no water to pull.

# %%

print(oxford_fwtw.pull_check({"volume": 10}))

# %% [markdown]
# If we add in some water, we see the pull check responds that water is available.

# %%

oxford_fwtw.service_reservoir_tank.storage["volume"] += 25
print(oxford_fwtw.pull_check({"volume": 10}))

# %% [markdown]
# When we set a pull request, we see that we successfully receive the water and the tank is updated.

# %%


reply = oxford_fwtw.pull_set({"volume": 10})
print(reply)
print(oxford_fwtw.service_reservoir_tank.storage)

# %% [markdown]
# ### Land
# We will now create a [land node](./../../../reference-land/#wsimod.nodes.land.Land),
# it is a bit involved so you might want to skip ahead to [demand](#Residential-demand),
# or check out the [land node tutorial](./../land_demo)
# %% [markdown]
# Data inputs are a single dictionary

# %%

land_inputs = data_input_dict["oxford_land"]

print(land_inputs[("precipitation", pd.to_datetime("2010-11-20"))])
print(land_inputs[("et0", pd.to_datetime("2010-11-20"))])
print(land_inputs[("temperature", pd.to_datetime("2009-10-15"))])

# %% [markdown]
# Assign some default pollutant deposition values (kg/m2/d)
# %%
pollutant_deposition = {
    "boron": 100e-10,
    "calcium": 70e-7,
    "chloride": 60e-10,
    "fluoride": 0.2e-7,
    "magnesium": 6e-7,
    "nitrate": 2e-9,
    "nitrogen": 4e-7,
    "potassium": 7e-7,
    "silicon": 7e-9,
    "sodium": 30e-9,
    "sulphate": 70e-7,
}
# %% [markdown]
# Create two surfaces as a list of dicts
# %%
surface = [
    {
        "type_": "PerviousSurface",
        "area": 2e7,
        "pollutant_load": pollutant_deposition,
        "surface": "rural",
        "field_capacity": 0.3,
        "depth": 0.5,
        "initial_storage": 2e7 * 0.4 * 0.5,
    },
    {
        "type_": "ImperviousSurface",
        "area": 1e7,
        "pollutant_load": pollutant_deposition,
        "surface": "urban",
        "initial_storage": 5e6,
    },
]

# %% [markdown]
# Create the land node from these surfaces and the input data
# %%
oxford_land = Land(surfaces=surface, name="oxford_land", data_input_dict=land_inputs)

# %% [markdown]
# We can see the land node has various tanks that have been initialised empty

# %%

print(oxford_land.surface_runoff.storage)
print(oxford_land.subsurface_runoff.storage)
print(oxford_land.percolation.storage)
# %% [markdown]
# We can see the surfaces have also been initialised, although they are not empty because we provided 'initial_storage' parameters.

# %%
rural_surface = oxford_land.get_surface("rural")
urban_surface = oxford_land.get_surface("urban")
print("{0}-{1}".format("rural", rural_surface.storage))
print("{0}-{1}".format("urban", urban_surface.storage))

# %% [markdown]
# We can run a timestep of the land node with the 'run' command

# %%
oxford_land.t = pd.to_datetime("2012-12-22")

oxford_land.run()

# %% [markdown]
# We can see that the land and surface tanks have been updated

# %%
print(oxford_land.surface_runoff.storage)
print(oxford_land.subsurface_runoff.storage)
print(oxford_land.percolation.storage)

print("{0}-{1}".format("rural", rural_surface.storage))
print("{0}-{1}".format("urban", urban_surface.storage))

# %% [markdown]
# ### Residential demand
# The [residential demand](./../../../reference-other/#wsimod.nodes.demand.ResidentialDemand)
# node requires population, per capita demand and a pollutant_load dictionary that defines
# how much (weight in kg) pollution is generated per person per day.

# %%
oxford = ResidentialDemand(
    name="oxford",
    population=2e5,
    per_capita=0.15,
    pollutant_load={
        "boron": 500 * constants.UG_L_TO_KG_M3 * 0.15,
        "calcium": 150 * constants.MG_L_TO_KG_M3 * 0.15,
        "chloride": 180 * constants.MG_L_TO_KG_M3 * 0.15,
        "fluoride": 0.4 * constants.MG_L_TO_KG_M3 * 0.15,
        "magnesium": 30 * constants.MG_L_TO_KG_M3 * 0.15,
        "nitrate": 60 * constants.MG_L_TO_KG_M3 * 0.15,
        "nitrogen": 50 * constants.MG_L_TO_KG_M3 * 0.15,
        "potassium": 30 * constants.MG_L_TO_KG_M3 * 0.15,
        "silicon": 20 * constants.MG_L_TO_KG_M3 * 0.15,
        "sodium": 200 * constants.MG_L_TO_KG_M3 * 0.15,
        "sulphate": 250 * constants.MG_L_TO_KG_M3 * 0.15,
        "temperature": 14,
    },
    data_input_dict=land_inputs,
)
# pollutant_load calculated based on expected effluent at WWTW


# %% [markdown]
# ### Reservoir
# A [reservoir node](./../../../reference-storage/#wsimod.nodes.storage.Reservoir)
# is used to make abstractions from rivers and supply FWTWs

# %%
farmoor = Reservoir(
    name="farmoor", capacity=1e7, initial_storage=1e7, area=1.5e6, datum=62
)

# %% [markdown]
# ### Distribution
# We use a generic [Node](./../../../reference-nodes/#wsimod.nodes.nodes.Node) as a junction to represent the distribution network between the FWTW and households

# %%

distribution = Node(name="oxford_distribution")

# %% [markdown]
# ### Wastewater treatment works
# [Wastewater treatment works (WWTW)](./../../../reference-wtw/#wsimod.nodes.wtw.WWTW)
# are nodes that can store sewage water temporarily in storm tanks, and reduce the pollution
# amounts in water before releasing them onwards to rivers.

# %%

oxford_wwtw = WWTW(
    stormwater_storage_capacity=2e4,
    stormwater_storage_area=2e4,
    treatment_throughput_capacity=5e4,
    name="oxford_wwtw",
)

# %% [markdown]
# ### Sewers
# [Sewer nodes](./../../../reference-sewer/#wsimod.nodes.sewer.Sewer) enable water to transition
# between households and WWTWs, and between impervious surfaces and rivers or WWTWs.
# They use a timearea diagram to represent travel time, which assigns a specified percentage
# of water to take a specified duration to pass through the sewer node.
# %%
combined_sewer = Sewer(
    capacity=4e6, pipe_timearea={0: 0.8, 1: 0.15, 2: 0.05}, name="combined_sewer"
)

# %% [markdown]
# ### Groundwater
# [Groundwater nodes](./../../../reference-storage/#wsimod.nodes.storage.Groundwater)
# implement a simple residence time to determine baseflow

# %%

gw = Groundwater(capacity=3.2e9, area=3.2e8, name="gw", residence_time=20)


# %% [markdown]
# ### Create a nodelist
# To keep all the nodes in one place, we put them into a list
# %%
nodelist = [
    thames_above_abingdon,
    evenlode,
    thames,
    ray,
    cherwell,
    oxford,
    distribution,
    farmoor,
    oxford_fwtw,
    oxford_wwtw,
    combined_sewer,
    oxford_land,
    gw,
    farmoor_abstraction,
    evenlode_thames,
    cherwell_ray,
    cherwell_thames,
    thames_mixer,
]

print(nodelist)

# %% [markdown]
# ## Arcs
# [Arcs](./../../../reference-arc/#wsimod.arcs.arcs.Arc) link nodes.
# An example arc is the link between a FWTW and the distribution node
# %%

# Standard simple arcs
fwtw_to_distribution = Arc(
    in_port=oxford_fwtw, out_port=distribution, name="fwtw_to_distribution"
)
print(fwtw_to_distribution)

# %% [markdown]
# As with nodes, even though we only gave it a few parameters, the arc comes with a lot built in
# %%
print(dir(fwtw_to_distribution))

# %% [markdown]
# We can see that the arc links the two nodes
# %%


print(fwtw_to_distribution.in_port)


# %%


print(fwtw_to_distribution.out_port)

# %% [markdown]
# And that it has updated the nodes that it is connecting.
# %%


print(oxford_fwtw.out_arcs)


# %%


print(distribution.in_arcs)

# %% [markdown]
# We use arcs to send checks and requests..
# %%


print(fwtw_to_distribution.send_pull_check({"volume": 20}))


# %%


reply = fwtw_to_distribution.send_pull_request({"volume": 20})
print(reply)

# %% [markdown]
# They convey this information to the nodes that they connect to, which update their state variables
# %%


print(oxford_fwtw.service_reservoir_tank.storage)

# %% [markdown]
# In turn, the arcs update their own state variables.
# %%


print(fwtw_to_distribution.flow_in)
print(fwtw_to_distribution.flow_out)

# %% [markdown]
# ## Arc parameters
# Besides the in/out ports and names, arcs can have a parameter for their capacity, to limit the flow that may pass through it each timestep.
# A typical example would be on river abstractions to a reservoir
# %%
abstraction_to_farmoor = Arc(
    in_port=farmoor_abstraction,
    out_port=farmoor,
    name="abstraction_to_farmoor",
    capacity=5e4,
)

# %% [markdown]
# A bit more sophisticated is the 'preference' parameter.
# We use preference to express where we would prefer the model to send water.
# In this example, the sewer can send water to both the treatment plant and directly into the river.
# Of course we would always to prefer to send water to the plant, so we give it a very high preference.
# Discharging into the river should only be done if there is no capacity left at the WWTW, so we give the arc a very low preference.
# %%
sewer_to_wwtw = Arc(
    in_port=combined_sewer, out_port=oxford_wwtw, preference=1e10, name="sewer_to_wwtw"
)
sewer_overflow = Arc(
    in_port=combined_sewer,
    out_port=thames_mixer,
    preference=1e-10,
    name="sewer_overflow",
)


# %% [markdown]
# ## Create arcs
# Arcs are a bit less interesting than nodes because they generally don't capture complicated physical behaviours.
# So we just create all of them below.
# %%


evenlode_to_thames = Arc(
    in_port=evenlode, out_port=evenlode_thames, name="evenlode_to_thames"
)

thames_to_thames = Arc(
    in_port=thames, out_port=evenlode_thames, name="thames_to_thames"
)

ray_to_cherwell = Arc(in_port=ray, out_port=cherwell_ray, name="ray_to_cherwell")

cherwell_to_cherwell = Arc(
    in_port=cherwell, out_port=cherwell_ray, name="cherwell_to_cherwell"
)

thames_to_farmoor = Arc(
    in_port=evenlode_thames, out_port=farmoor_abstraction, name="thames_to_farmoor"
)

farmoor_to_mixer = Arc(
    in_port=farmoor_abstraction, out_port=thames_mixer, name="farmoor_to_mixer"
)

cherwell_to_mixer = Arc(
    in_port=cherwell_ray, out_port=thames_mixer, name="cherwell_to_mixer"
)

wwtw_to_mixer = Arc(in_port=oxford_wwtw, out_port=thames_mixer, name="wwtw_to_mixer")

mixer_to_waste = Arc(
    in_port=thames_mixer, out_port=thames_above_abingdon, name="mixer_to_waste"
)

distribution_to_demand = Arc(
    in_port=distribution, out_port=oxford, name="distribution_to_demand"
)

reservoir_to_fwtw = Arc(in_port=farmoor, out_port=oxford_fwtw, name="reservoir_to_fwtw")

fwtw_to_sewer = Arc(in_port=oxford_fwtw, out_port=combined_sewer, name="fwtw_to_sewer")

demand_to_sewer = Arc(in_port=oxford, out_port=combined_sewer, name="demand_to_sewer")

land_to_sewer = Arc(in_port=oxford_land, out_port=combined_sewer, name="land_to_sewer")

land_to_gw = Arc(in_port=oxford_land, out_port=gw, name="land_to_gw")

garden_to_gw = Arc(in_port=oxford, out_port=gw, name="garden_to_gw")

gw_to_mixer = Arc(in_port=gw, out_port=thames_mixer, name="gw_to_mixer")

# %% [markdown]
# Again, we keep all the arcs in a tidy list together.

# %%
arclist = [
    evenlode_to_thames,
    thames_to_thames,
    ray_to_cherwell,
    cherwell_to_cherwell,
    thames_to_farmoor,
    farmoor_to_mixer,
    cherwell_to_mixer,
    wwtw_to_mixer,
    sewer_overflow,
    mixer_to_waste,
    abstraction_to_farmoor,
    distribution_to_demand,
    demand_to_sewer,
    land_to_sewer,
    sewer_to_wwtw,
    fwtw_to_sewer,
    fwtw_to_distribution,
    reservoir_to_fwtw,
    land_to_gw,
    garden_to_gw,
    gw_to_mixer,
]


# %% [markdown]
# ## Mapping
# Remember, WSIMOD is an integrated model.
# Because it covers so many different things, it is very easy to make mistakes.
# Thus it is always good practice to plot your data!
#
# Below we load the node location data and create arcs from the information in the arclist.
# %%

location_fn = os.path.join(data_folder, "raw", "points_locations.geojson")
nodes_gdf = gpd.read_file(location_fn).set_index("name")
arcs_gdf = []

for arc in arclist:
    arcs_gdf.append(
        {
            "name": arc.name,
            "geometry": LineString(
                [
                    nodes_gdf.loc[arc.in_port.name, "geometry"],
                    nodes_gdf.loc[arc.out_port.name, "geometry"],
                ]
            ),
        }
    )

arcs_gdf = gpd.GeoDataFrame(arcs_gdf, crs=nodes_gdf.crs)
# %% [markdown]
# Because we converted the information as GeoDataFrames, we can simply plot them below
# %%

f, ax = plt.subplots()
arcs_gdf.plot(ax=ax)
nodes_gdf.plot(color="r", ax=ax, zorder=10)

# %% [markdown]
# ## Orchestration
# Orchestration is making the simulation happen by calling functions in the nodes.
# These functions simulate physical behaviour within the node, and cause pulls/pushes to happen which in turn triggers physical behaviour in other nodes.
#
# ### Orchestrating an individual timestep
#
# We will start below by manually orchestrating a single timestep.
#
# We start by setting the date, so that every node knows what forcing data to read for this timestep.

# %%
date = dates[0]

for node in nodelist:
    node.t = date

print(date)
print(oxford_fwtw.t)

# %% [markdown]
# We can see the service reservoirs are empty but the supply reservoir is not!
# %%

print(oxford_fwtw.service_reservoir_tank.storage)
print(farmoor.tank.storage)
# %% [markdown]
# If we call the FWTW's treat_water function it will pull water from the supply reservoir and update its service reservoirs
# %%

oxford_fwtw.treat_water()

print(oxford_fwtw.service_reservoir_tank.storage)
print(farmoor.tank.storage)

# %% [markdown]
# This information is tracked in the arcs that enter the FWTW
# %%


print(oxford_fwtw.in_arcs)


# %%


print(reservoir_to_fwtw.flow_in)
print(reservoir_to_fwtw.flow_out)

# %% [markdown]
# Although none of that water has yet entered the distribution network (only some small flow from the earlier demonstration)
# %%


print(fwtw_to_distribution.flow_in)

# %% [markdown]
# That is because no water consumption demand had yet been generated.
#
# If we call the demand node's create_demand function we see that the distribution arc becomes utilised.
# %%

oxford.create_demand()
print(fwtw_to_distribution.flow_in)

# %% [markdown]
# We also see that this gets pushed onwards into the sewer system

# %%
print(demand_to_sewer.flow_in)


# %% [markdown]
# Many nodes have functions intended to be called during orchestration.
# These functions are described in the documentation.
# For example, we see in the [Land node](./../../../reference-land/#wsimod.nodes.land.Land) API reference that the 'run' function is intended to be called from orchestration.
# %%
oxford_land.run()

# %% [markdown]
# Below we call the functions for other nodes
# %%

# Discharge GW
gw.distribute()

# Discharge sewers (pushed to other sewers or WWTW)
combined_sewer.make_discharge()

# Run WWTW model
oxford_wwtw.calculate_discharge()

# Make abstractions
farmoor.make_abstractions()

# Discharge WW
oxford_wwtw.make_discharge()

# Route catchments
evenlode.route()
thames.route()
ray.route()
cherwell.route()

# %% [markdown]
# ## Ending a timestep
# Because mistakes happen, it is essential to carry out mass balance testing.
# Each node has a mass balance function that can be called.
# We see a mass balance violation resulting from the demonstration with the FWTW earlier.
# %%

for node in nodelist:
    in_, ds_, out_ = node.node_mass_balance()


# %% [markdown]
# We should also call the end_timestep function in nodes and arcs.
# This is important for mass balance testing and capturing the behaviour of some dynamic processes in nodes.

# %%

for node in nodelist:
    node.end_timestep()

for arc in arclist:
    arc.end_timestep()

# %% [markdown]
# ## Model object
# Of course it would be a massive pain to manually orchestrate every timestep.
# So instead we store node and arc information in a [model object](./../../../reference-model/#wsimod.orchestration.model.Model)
# that will do the orchestration for us.
#
# Because we have already created the nodes/arcs above, we simply need to add the instantiated lists above.

# %%

my_model = Model()
my_model.add_instantiated_nodes(nodelist)
my_model.add_instantiated_arcs(arclist)
my_model.dates = dates

# %% [markdown]
# The model object lets us reinitialise the nodes/arcs, and run all of the orchestration with a 'run' function.
# %%

my_model.reinit()

flows, _, _, _ = my_model.run()

# %% [markdown]
# The model outputs flows as a dictionary which can be converted to a dataframe
# %%

flows = pd.DataFrame(flows)

print(flows.sample(10))

# %% [markdown]
# ## Validation plots
# Of course we shouldn't trust a model without proof, and this is doubly true for an integrated model whose errors may easily propagate.
#
# Thankfully we have rich in-river water quality sampling in Oxford that we can use for validation
#
# We load and format this data for dates and pollutants that overlap with what we have simulated
# %%

mixer_val_df = pd.read_csv(os.path.join(data_folder, "raw", "mixer_wims_val.csv"))
mixer_val_df.date = pd.to_datetime(mixer_val_df.date)
mixer_val_df = mixer_val_df.loc[mixer_val_df.date.isin(dates)]
val_pollutants = mixer_val_df.variable.unique()
mixer_val_df = mixer_val_df.pivot(index="date", columns="variable", values="value")

# %% [markdown]
# We get rid of the first day of flows because our tanks were initialised empty and will not be informative

# %%
flows = flows.loc[flows.time != dates[0]]

# %% [markdown]
# We convert our flows, which are simulated in kg/d into a concentration value (kg/m3/d).
# %%
flows_plot = flows.copy()

# Convert to KG/M3
for pol in set(val_pollutants):
    if pol != "temperature":
        flows_plot[pol] /= flows_plot.flow
# %% [markdown]
# We pick the model outlet as a validation location and make a pretty plot - fantastic!
# %%

plot_arc = "mixer_to_waste"
f, axs = plt.subplots(val_pollutants.size, 1)
for pol, ax in zip(val_pollutants, axs):
    ax.plot(
        flows_plot.loc[flows_plot.arc == plot_arc, [pol, "time"]].set_index("time"),
        color="b",
        label="simulation",
    )
    ax.plot(mixer_val_df[pol], ls="", marker="o", color="r", label="spot sample")
    ax.set_ylabel(pol)
plt.legend()
