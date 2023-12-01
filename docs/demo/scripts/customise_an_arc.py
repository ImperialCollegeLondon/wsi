# %% [markdown]
# :warning: Warning: this code does not represent best practice for
# customisation. Instead we recommend use of decorators to overwrite
# behaviour. Users can see examples of decorators in the
# [customise_interactions](https://barneydobson.github.io/wsi/demo/scripts/customise_interactions/)
# and [customise_riverreservoir](https://barneydobson.github.io/wsi/demo/scripts/customise_riverreservoir/)
# guides. This guide may still be useful for WSIMOD code examples, and it
# will still work in many cases.
#
# There is currently a GitHub (issue)[https://github.com/barneydobson/wsi/issues/11]
# to revise this guide.
#
# # Customise an arc (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/customise_an_arc.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Create baseline](#create-baseline)
#
# 3. [Customise arc](#customise-arc)
#
# 4. [Inspect results](#inspect-results)
#
# %% [markdown]
# ## Introduction
# In this tutorial we will demonstrate how to customise an arc on-the-fly. If
# you are creating a new type of arc that is a generic physical object (e.g., a
# weir), then you should probably create a new subclass of existing classes.
# However, if you are aiming to alter the behaviour of an arc that already has
# a class to fit some super specific behaviour, then it may be more suitable
# to customise on-the-fly. In addition, customising on-the-fly is very similar
# to creating a subclass, so the skills demonstrated here are likely to be
# transferrable.
#
# We will use the [Oxford demo](./../oxford_demo) as our base model, and build
# off it by assigning a varying capacity to the river abstraction depending on
# reservoir storage
#
# ## Create baseline
# We will first create and simulate the Oxford model to formulate baseline
# results. We use a version of the model with the minimum required flow from
# the [node customisation demo](./../customise_a_node).
#
# Start by importing packages.
# %%
import os

import pandas as pd
from matplotlib import pyplot as plt

from wsimod.demo.create_oxford import create_oxford_model_mrf

# %% [markdown]
# The model can be automatically created using the data_folder
# %%
# Select the root path for the data folder. Use the appropriate value for your case.
data_folder = os.path.join(os.path.abspath(""), "docs", "demo", "data")

baseline_model = create_oxford_model_mrf(data_folder)

# %% [markdown]
# Simulate baseline flows
# %%
baseline_flows, baseline_tanks, _, _ = baseline_model.run()
baseline_flows = pd.DataFrame(baseline_flows)
baseline_tanks = pd.DataFrame(baseline_tanks)

# %% [markdown]
# When we plot the results, we see some alarmingly low reservoir levels - I am sure that Thames Water
# would not be happy about this
# %%
f, axs = plt.subplots(3, 1, figsize=(6, 6))
baseline_flows.groupby("arc").get_group("farmoor_to_mixer").set_index("time")[
    ["flow"]
].plot(ax=axs[0], title="River flow downstream of abstractions")
axs[0].set_yscale("symlog")
axs[0].set_ylim([10e3, 10e7])
baseline_flows.groupby("arc").get_group("abstraction_to_farmoor").set_index("time")[
    ["flow"]
].plot(ax=axs[1], title="Abstraction")
axs[1].legend()

baseline_tanks.groupby("node").get_group("farmoor").set_index("time")[["storage"]].plot(
    ax=axs[2], title="Reservoir storage"
)
axs[2].legend()
f.tight_layout()

# %% [markdown]
# ## Customise arc
# The easiest way to customise an arc is by changing its ```get_excess```
# function. This is the function that determines how much capacity there is in
# the arc when called.
#
# In reality it is common for operational constraints to be seasonal, so we will
# define monthly amounts that, when reservoir levels are below them, the
# abstraction capacity can be increased. These amounts have the month as the
# key and the percentage that the reservoir is full as values.
# %%

levels = {
    1: 0.7,
    2: 0.8,
    3: 0.9,
    4: 0.95,
    5: 0.95,
    6: 0.95,
    7: 0.95,
    8: 0.9,
    9: 0.8,
    10: 0.7,
    11: 0.7,
    12: 0.7,
}
# %% [markdown]
# We also need to determine what the new abstraction capacity will be, we will
# choose a simple multiplier on the existing capacity
# %%
capacity_multiplier = 1.25


# %% [markdown]
# We can now redefine the ```get_excess``` function. We can start with a trimmed down
# version of the original ```get_excess``` function:
# ```
# def get_excess(self, direction, vqip = None, tag = 'default'):
#     pipe_excess = self.capacity - self.flow_in
#     node_excess = self.in_port.pull_check(vqip, tag)
#     excess = min(pipe_excess, node_excess['volume'])
#     return self.v_change_vqip(node_excess, excess)
# ```
# This shows only the bits of the function that are relevant for pulls.
# In order to implement the new variable capacity, we will need to:
#
#   -identify the month
#
#   -identify the reservoir volume expressed as a percent
#
#   -adjust the capacity to reflect possibility of increased abstractions
# %%
def get_excess_new(arc, direction, vqip=None, tag="default"):
    """

    Args:
        arc:
        direction:
        vqip:
        tag:

    Returns:

    """
    # All nodes have access to the 't' parameter, which is a datetime object
    # that can return the month
    month = arc.out_port.t.month

    # Get percent full
    pct = arc.out_port.get_percent()

    # Adjust capacity
    if arc.levels[month] > pct:
        capacity = arc.capacity * arc.capacity_multiplier
    else:
        capacity = arc.capacity

    # Proceed with get_excess function as normal
    pipe_excess = capacity - arc.flow_in
    node_excess = arc.in_port.pull_check(vqip, tag)
    excess = min(pipe_excess, node_excess["volume"])
    return arc.v_change_vqip(node_excess, excess)


# %% [markdown]
# Finally we need a wrapper to assign the new function and the associated
# parameters
# %%
def apply_variable_capacity(arc, levels, multiplier):
    """

    Args:
        arc:
        levels:
        multiplier:
    """
    # Assign parameters
    arc.levels = levels
    arc.capacity_multiplier = multiplier

    # Change get_excess function to new one above
    arc.get_excess = lambda **x: get_excess_new(arc, **x)


# %% [markdown]
# Now we can create a new model
# %%
customised_model = create_oxford_model_mrf(data_folder)

# %% [markdown]
# .. and assign the new variable capacity
# %%
apply_variable_capacity(
    customised_model.arcs["abstraction_to_farmoor"], levels, capacity_multiplier
)

# %% [markdown]
# ## Inspect results
# Let us rerun and view the results to see if it has worked.
# %%

flows_var_cap, tanks_var_cap, _, _ = customised_model.run()

flows_var_cap = pd.DataFrame(flows_var_cap)
tanks_var_cap = pd.DataFrame(tanks_var_cap)

# %% [markdown]
# We can see that the reservoir storage is able to recharge much more quickly
# from the lowest point because of the increased abstractions. We also see
# negligible change in river flow because the increased abstractions are mainly
# occurring when the flow is quite high. This is still unlikely to be a
# preferred option in practice because the lowest reservoir storage is
# unchanged. This happens because the increased capacity available is not helpful when the flows are
# so low that the minimum required flow is active. Better luck next time Thames Water!
# %%

f, axs = plt.subplots(3, 1, figsize=(6, 6))
plot_flows1 = pd.concat(
    [
        baseline_flows.groupby("arc")
        .get_group("farmoor_to_mixer")
        .set_index("time")
        .flow.rename("Baseline"),
        flows_var_cap.groupby("arc")
        .get_group("farmoor_to_mixer")
        .set_index("time")
        .flow.rename("Customised"),
    ],
    axis=1,
)
plot_flows1.plot(ax=axs[0], title="River flow downstream of abstractions")
axs[0].set_yscale("symlog")
axs[0].set_ylim([10e3, 10e7])

plot_flows2 = pd.concat(
    [
        baseline_flows.groupby("arc")
        .get_group("abstraction_to_farmoor")
        .set_index("time")
        .flow.rename("Baseline"),
        flows_var_cap.groupby("arc")
        .get_group("abstraction_to_farmoor")
        .set_index("time")
        .flow.rename("Customised"),
    ],
    axis=1,
)
plot_flows2.plot(ax=axs[1], title="Abstraction")
axs[1].legend()

plot_tanks = pd.concat(
    [
        baseline_tanks.groupby("node")
        .get_group("farmoor")
        .set_index("time")
        .storage.rename("Baseline"),
        tanks_var_cap.groupby("node")
        .get_group("farmoor")
        .set_index("time")
        .storage.rename("Customised"),
    ],
    axis=1,
)
plot_tanks.plot(ax=axs[2], title="Reservoir storage")
axs[2].legend()
f.tight_layout()
