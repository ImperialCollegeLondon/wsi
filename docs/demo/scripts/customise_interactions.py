# %% [markdown]
# # Customise interactions (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/customise_interactions.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Create baseline](#create-baseline)
#
# 3. [Customise node](#customise-node)
#
# 4. [Inspect results](#inspect-results)
#
# 5. [What next](#what-next?)
#
# %% [markdown]
# ## Introduction
# In this tutorial we will demonstrate how to customise interactions between
# nodes using the handler functionality. Custom handlers are to be used when
# you want for a node to respond differently to one type of node than another.
# An example of handlers can be found in the 
# [sewer node](https://github.com/barneydobson/wsi/blob/main/wsimod/nodes/sewer.py)
# where you can see that the sewer uses different functions to respond to 
# differently tagged push requests. We higlight the `push_set_handler` customisations
# below for a sewer object below.
# %%
from wsimod.nodes.sewer import Sewer
from pprint import pprint as print
my_sewer = Sewer(name = 'mr_sewer')
print(my_sewer.push_set_handler)

# %% [markdown]
# We can see that `my_sewer` has two different functions (`push_set_land`
# and `push_set_sewer`) stored in its `push_set_handler` dictionary. There are
# four different entries in the handler (`'Demand'`, `'Land'`, `'Sewer'`, 
# `'default'`). This means that the `Sewer` node can respond to these four 
# different tags. Tags can take any value, but by convention they specify a
# WSIMOD node type, or a tuple containing a node type and a specific type of 
# interaction (e.g., `('Demand','Garden')` in the 
# [land node](https://barneydobson.github.io/wsi/reference-land/#wsimod.nodes.land.Land).
# All nodes must have a `push_set_handler`, `push_check_handler`, `pull_set_handler`,
# `pull_check_handler`, and at least one `default` tag entry in each of these
# dictionaries. If you do not want to define behaviour for a certain kind of interaction
# (e.g., maybe you can never pull from this type of node), then you can use, e.g.,
# the `pull_set_deny` and `pull_check_deny` functions for the `default` tag.
#
# ## Create baseline
# We will first create and simulate the Oxford model to formulate baseline 
# results.
#
# Start by importing packages.
# %%
from wsimod.core import constants
import os
import pandas as pd
from matplotlib import pyplot as plt
from wsimod.demo.create_oxford import create_oxford_model
