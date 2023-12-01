# %% [markdown]
# # Quickstart (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/quickstart_demo.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Data](#imports-and-forcing-data)
#
# 3. [Create nodes](#create-nodes)
#
# 4. [Create arcs](#create-arcs)
#
# 5. [Create model](#create-model)
#
# 6. [Run model](#run-model)
#
# 7. [What next?](#what-next?)
# %% [markdown]
# ## Introduction
#
# WSIMOD is a Python package that lets you create nodes that represent physical
# things in the water cycle and enables them talk to each other. In this demo,
# we will create some nodes, some arcs (the things that link nodes), and make
# a model that lets us simulate the flow of water through the water cycle.
#
# We will create a simple catchment model that contains a hydrological node,
# a sewer node, a groundwater node, and a river node. Using these nodes, we
# will simulate a mixed urban-rural catchment.
#
# %% [markdown]
# ## Imports and forcing data

# %% [markdown]
# Import packages
# %%

import os

import pandas as pd
from matplotlib import pyplot as plt

from wsimod.core import constants
from wsimod.orchestration.model import Model

# %% [markdown]
# Load input data, in this example we use precipitation, temperature, and
# evapotranspiration (et0).
# %%

# Select the root path for the data folder. Use the appropriate value for your case.
data_folder = os.path.join(os.path.abspath(""), "docs", "demo", "data")


input_fid = os.path.join(data_folder, "processed", "timeseries_data.csv")
input_data = pd.read_csv(input_fid)
input_data.loc[input_data.variable == "precipitation", "value"] *= constants.MM_TO_M
input_data.date = pd.to_datetime(input_data.date)
input_data = input_data.loc[input_data.site == "oxford_land"]
dates = input_data.date.drop_duplicates()
print(input_data.sample(10))

# %% [markdown]
# Input data is stored in dicts, where a key is a variable on a given day.
# %%

land_inputs = input_data.set_index(["variable", "date"]).value.to_dict()

example_date = pd.to_datetime("2009-03-03")

print(land_inputs[("precipitation", example_date)])
print(land_inputs[("et0", example_date)])
print(land_inputs[("temperature", example_date)])

# %% [markdown]
# ## Create nodes
# %% [markdown]
# Nodes can be defined as dictionaries of parameters. Different nodes require
# different parameters, you can see the documentation in the
# [API](./../../../reference) to understand what parameters can be set.
# Although every node should have a type (type_) and a name.
# %%

sewer = {"type_": "Sewer", "capacity": 0.04, "name": "my_sewer"}

surface1 = {
    "type_": "ImperviousSurface",
    "surface": "urban",
    "area": 10,
    "pollutant_load": {"phosphate": 1e-7},
}

surface2 = {
    "type_": "PerviousSurface",
    "surface": "rural",
    "area": 100,
    "depth": 0.5,
    "pollutant_load": {"phosphate": 1e-7},
}

land = {
    "type_": "Land",
    "data_input_dict": land_inputs,
    "surfaces": [surface1, surface2],
    "name": "my_land",
}

gw = {"type_": "Groundwater", "area": 100, "capacity": 100, "name": "my_groundwater"}

node = {"type_": "Node", "name": "my_river"}

waste = {"type_": "Waste", "name": "my_outlet"}

# %% [markdown]
# ## Create arcs
# %% [markdown]
# [Arcs](./../../../reference-arc/#wsimod.arcs.arcs.Arc) can also be
# created as dictionaries, they don't typically need any
# numerical parameters (although there are some exceptions in the
# [case study demo](./../oxford_demo/#Arc-parameters)). Though they do need
# to specify the in_port (where the arc starts), and out_port (where it
# finishes). It's also handy to give each arc a name.
# %%
urban_drainage = {
    "type_": "Arc",
    "in_port": "my_land",
    "out_port": "my_sewer",
    "name": "urban_drainage",
}

percolation = {
    "type_": "Arc",
    "in_port": "my_land",
    "out_port": "my_groundwater",
    "name": "percolation",
}

runoff = {
    "type_": "Arc",
    "in_port": "my_land",
    "out_port": "my_river",
    "name": "runoff",
}

storm_outflow = {
    "type_": "Arc",
    "in_port": "my_sewer",
    "out_port": "my_river",
    "name": "storm_outflow",
}

baseflow = {
    "type_": "Arc",
    "in_port": "my_groundwater",
    "out_port": "my_river",
    "name": "baseflow",
}

catchment_outflow = {
    "type_": "Arc",
    "in_port": "my_river",
    "out_port": "my_outlet",
    "name": "catchment_outflow",
}

# %% [markdown]
# ## Create model
# %% [markdown]
# We can create a [model object](./../../../reference-model/#wsimod.orchestration.model.Model) and add dates
# %%
my_model = Model()
my_model.dates = dates
# %% [markdown]
# Add nodes in a list. The Model object will create the nodes from the dict
# entries.
# %%
my_model.add_nodes([sewer, land, gw, node, waste])

# %% [markdown]
# Add arcs in a list.
# %%
my_model.add_arcs(
    [urban_drainage, percolation, runoff, storm_outflow, baseflow, catchment_outflow]
)
# %% [markdown]
# ## Run model
# %% [markdown]
# Run the model
# %%
flows, _, _, _ = my_model.run()
flows = pd.DataFrame(flows)

# %% [markdown]
# Plot results
# %%
f, axs_ = plt.subplots(3, 2, figsize=(10, 10))

for axs, variable in zip(axs_.T, ["flow", "phosphate"]):
    flows_plot = flows.pivot(index="time", columns="arc", values=variable)
    input_data.pivot(index="date", columns="variable", values="value")[
        ["precipitation"]
    ].plot(ax=axs[0], xlabel="", xticks=[], sharex=True)

    flows_plot[["runoff", "urban_drainage", "percolation"]].plot(
        ax=axs[1], xlabel="", xticks=[], sharex=True
    )
    flows_plot[["catchment_outflow", "storm_outflow", "baseflow"]].plot(ax=axs[2])
axs_[1, 0].set_title("Flows (m3/d)")
axs_[1, 1].set_title("Phosphate (kg/d)")
f.tight_layout()

# %% [markdown]
# ## What next?
# If you are hydrologically minded then you might be interested in a more detailed
# tutorial for our [Land node](./../land_demo). If you want an overview to
# see how many different nodes in WSIMOD work, then the
# [Oxford case study](./../oxford_demo) might be more interesting.
