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
# # Customise a node (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/customise_a_node.py)
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
# In this tutorial we will demonstrate how to customise a node on-the-fly. If
# you are creating a new type of node that is a generic physical object, then
# you should probably create a new subclass of existing classes. However, if
# you are aiming to alter the behaviour of a physical object that already has
# a class to fit some super specific behaviour, then it may be more suitable
# to customise on-the-fly. In addition, customising on-the-fly is very similar
# to creating a subclass, so the skills demonstrated here are likely to be
# transferrable.
#
# We will use the [Oxford demo](./../oxford_demo) as our base model, and build
# off it by implementing a minimum required flow at the abstraction location.
#
# ## Create baseline
# We will first create and simulate the Oxford model to formulate baseline
# results.
#
# Start by importing packages.
# %%
import os

import pandas as pd
from matplotlib import pyplot as plt

from wsimod.core import constants
from wsimod.demo.create_oxford import create_oxford_model

# %% [markdown]
# The model can be automatically created using the data_folder
# %%
# Select the root path for the data folder. Use the appropriate value for your case.
data_folder = os.path.join(os.path.abspath(""), "docs", "demo", "data")

baseline_model = create_oxford_model(data_folder)
# %% [markdown]
# Simulate baseline flows
# %%
baseline_flows, baseline_tanks, _, _ = baseline_model.run()
baseline_flows = pd.DataFrame(baseline_flows)
baseline_tanks = pd.DataFrame(baseline_tanks)

# %% [markdown]
# When we plot results, we see no variability in abstractions and reservoir
# levels, maybe this is fine, but the river flow is getting drawn down quite low
# (down to 0.75m3/s, which is less than one quarter of the Q95 flow).
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
# ## Customise node
# To protect the river from abstractions during low flows, we can customise the
# abstraction node to implement a MRF.
#
# Our new node will want to behave similar to the old node, but with
# different behaviour when another node is pulling water from it. Thus we will
# define new functions to accommodate this.
#
# The first function we will define is a 'pull check' - that is, how should the
# node respond when another node queries how much water could be pulled from it.
#
# The only new line in comparison to that defined in the
# [default node](./../../../reference-nodes/#wsimod.nodes.nodes.Node) is where
# we 'Apply MRF'. We introduce two new variables, one for the minimum required
# flow (mrf), and one for the mrf already satisfied.
# %%
def pull_check_mrf(node, vqip=None):
    """

    Args:
        node:
        vqip:

    Returns:

    """
    # Respond to a pull check to the node

    # Work out how much water is available upstream
    reply = node.pull_check_basic()

    # Apply MRF
    reply["volume"] = max(
        reply["volume"] - (node.mrf - node.mrf_satisfied_this_timestep), 0
    )

    # If the pulled amount has been specified, pick the minimum of the available and that
    if vqip is not None:
        reply["volume"] = min(reply["volume"], vqip["volume"])

    # Return avaiable
    return reply


# %% [markdown]
# We must also define what will happen during a 'pull set' - that is, how should
# the node respond when another node requests water to pull from it.
#
# The default function for a node to do this is ```pull_distributed```, which pulls
# water from upstream nodes. We still call pull_distributed, however we
# increase the amount we request via it by the amount of MRF yet to satisfy.
# Any water which satsifies the MRF goes towards ```mrf_satisfied_this_timestep```,
# then the rest is available in the 'reply', for use in the pull request.
# Finally, we route the water that was used to satisfy the mrf downstream so
# that it cannot be used again this timestep.
# %%
def pull_set_mrf(node, vqip):
    """

    Args:
        node:
        vqip:

    Returns:

    """
    # Respond to a pull request to the node

    # Copy the request for boring reasons
    request = node.copy_vqip(vqip)

    # Increase the request by the amount of MRF not yet satisfied
    request["volume"] += node.mrf - node.mrf_satisfied_this_timestep

    # Pull the new updated request from upstream nodes
    reply = node.pull_distributed(request)

    # First satisfy the MRF
    reply_to_mrf = min((node.mrf - node.mrf_satisfied_this_timestep), reply["volume"])
    node.mrf_satisfied_this_timestep += reply_to_mrf

    reply_to_mrf = node.v_change_vqip(reply, reply_to_mrf)

    # Update reply (less the amount for MRF)
    reply = node.extract_vqip(reply, reply_to_mrf)

    # Then route that water downstream so it is not available
    mrf_route_reply = node.push_distributed(reply_to_mrf, of_type=["Node"])
    if mrf_route_reply["volume"] > constants.FLOAT_ACCURACY:
        print("warning MRF not able to push")

    # Return pulled amount
    return reply


# %% [markdown]
# We should also adjust the behaviour of a 'push set' - that is, how should the
# node respond when another node pushes water to it. We will need to do this
# because we want water that this node sends downstream on interactions that
# are not to do with pulls to still update the minimum required flow.
#
# The default behaviour for a node to do a push set is ```push_distributed```, which
# pushes water to downstream nodes. We do this as normal, but then update the
# ```mrf_satisfied_this_timestep```
# %%
def push_set_mrf(node, vqip):
    """

    Args:
        node:
        vqip:

    Returns:

    """
    # Respond to a push request to the node

    # Push water downstream
    reply = node.push_distributed(vqip)
    total_pushed_downstream = vqip["volume"] - reply["volume"]

    # Allow this water to contribute to mrf
    node.mrf_satisfied_this_timestep = min(
        node.mrf, node.mrf_satisfied_this_timestep + total_pushed_downstream
    )

    # Return the amount not pushed
    return reply


# %% [markdown]
# We also create a function to reset the ```mrf_satisfied_this_timestep``` at the end
# of each timestep
# %%
def end_timestep(node):
    """

    Args:
        node:
    """
    # Update MRF satisfied
    node.mrf_satisfied_this_timestep = 0


# %% [markdown]
# Finally we write a wrapper to assign the predefined functions to the node,
# and to set the mrf parameter.
# %%
def convert_to_mrf(node, mrf=5):
    """

    Args:
        node:
        mrf:
    """
    # Initialise MRF variables
    node.mrf = mrf
    node.mrf_satisfied_this_timestep = 0

    # Change pull functions to the ones defined above
    node.pull_set_handler["default"] = lambda x: pull_set_mrf(node, x)
    node.pull_check_handler["default"] = lambda x: pull_check_mrf(node, x)

    # Change end timestep function to one defined above
    node.end_timestep = lambda: end_timestep(node)


# %% [markdown]
# Now we can create a new model
# %%
customised_model = create_oxford_model(data_folder)

# %% [markdown]
# .. and convert the abstraction node to apply an MRF
# %%
new_mrf = 3 * constants.M3_S_TO_M3_DT
convert_to_mrf(customised_model.nodes["farmoor_abstraction"], mrf=new_mrf)

# %% [markdown]
# ## Inspect results
# Let us rerun and view the results to see if it has worked.
# %%

flows_mrf, tanks_mrf, _, _ = customised_model.run()

flows_mrf = pd.DataFrame(flows_mrf)
tanks_mrf = pd.DataFrame(tanks_mrf)

# %% [markdown]
# We can see that, at multiple low flow points in the timeseries, the
# customised river flow downstream of abstractions is higher than the baseline.
# We also see that this results in highly variable abstractions, which are non-
# existant when the river flow is below the MRF, and much higher following low flows.
# Finally we see significant impacts on the reservoir storage, which is now
# dynamic and much more realistic looking.
# %%

f, axs = plt.subplots(3, 1, figsize=(6, 6))
plot_flows1 = pd.concat(
    [
        baseline_flows.groupby("arc")
        .get_group("farmoor_to_mixer")
        .set_index("time")
        .flow.rename("Baseline"),
        flows_mrf.groupby("arc")
        .get_group("farmoor_to_mixer")
        .set_index("time")
        .flow.rename("Customised"),
    ],
    axis=1,
)
plot_flows1.plot(ax=axs[0], title="River flow downstream of abstractions")
plot_mrf = pd.DataFrame(
    index=[customised_model.dates[0], customised_model.dates[-1]],
    columns=["MRF"],
    data=[new_mrf, new_mrf],
)
plot_mrf.plot(ax=axs[0], color="k", ls="--")
axs[0].set_yscale("symlog")
axs[0].set_ylim([10e3, 10e7])

plot_flows2 = pd.concat(
    [
        baseline_flows.groupby("arc")
        .get_group("abstraction_to_farmoor")
        .set_index("time")
        .flow.rename("Baseline"),
        flows_mrf.groupby("arc")
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
        tanks_mrf.groupby("node")
        .get_group("farmoor")
        .set_index("time")
        .storage.rename("Customised"),
    ],
    axis=1,
)
plot_tanks.plot(ax=axs[2], title="Reservoir storage")
axs[2].legend()
f.tight_layout()

# %% [markdown]
# ## What next
# Creating a new node is one way to achieve customisable behaviour to fit your
# use case, but it is not the only way to do this. Sometimes it may be easier
# to [customise an arc](./../customise_an_arc).
