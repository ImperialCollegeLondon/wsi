# %% [markdown]
# # Customise interactions (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/customise_interactions.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Illustration](#illustration)
#
# 3. [More realistic example](#more-realistic-example)
#
# 4. [What next](#what-next)
#
# %% [markdown]
# ## Introduction
# In this tutorial we will demonstrate how to customise interactions between
# nodes using the handler functionality. Custom handlers are to be used when
# you want for a node to respond differently to one type of node than another.
# An example of custom handlers can be found in the
# [sewer node](https://github.com/barneydobson/wsi/blob/main/wsimod/nodes/sewer.py)
# where you can see that the sewer uses different functions to respond to
# differently tagged push requests. We highlight the `push_set_handler` customisations
# below for a sewer object below.
# %%
from pprint import pprint as print

from wsimod.nodes.sewer import Sewer

my_sewer = Sewer(name="mr_sewer")
print(my_sewer.push_set_handler)

# %% [markdown]
# We can see that `my_sewer` has two different functions (`push_set_land`
# and `push_set_sewer`) stored in its `push_set_handler` dictionary. There are
# four different entries in the handler (`'Demand'`, `'Land'`, `'Sewer'`,
# `'default'`). This means that the `Sewer` node can respond to these four
# different tags. Tags can take any value, but by convention they specify a
# WSIMOD node type, or a tuple containing a node type and a specific type of
# interaction (e.g., `('Demand','Garden')` in the
# [land node](https://barneydobson.github.io/wsi/reference-land/#wsimod.nodes.land.Land)).
# All nodes must have the dictionaries: `push_set_handler`, `push_check_handler`,
# `pull_set_handler`, `pull_check_handler`, and at least one `default` key in each
# (see the [Node](https://barneydobson.github.io/wsi/reference-nodes/#wsimod.nodes.nodes.Node)
# class for defaults). If you do not want to define behaviour for a certain kind of interaction,
# e.g., maybe you can never pull from this type of node, then you can use, e.g.,
# the `pull_set_deny` and `pull_check_deny` functions for the `'default'` tag.
#
# It is important to note that unless a tag is specified in the request, the `'default'`
# tag is used.
# %% [markdown]
# ## Illustration
# We can illustrate the behaviour of handlers by creating a simple model.

# %%
# Import packages
from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes import Distribution, Node

# Set simple pollutants (i.e., temperature and phosphate only)
constants.set_simple_pollutants()

# Create objects
my_node = Node(name="my_node")
my_dist = Distribution(name="my_dist")
my_arc = Arc(name="my_arc", in_port=my_node, out_port=my_dist)

# Inspect push_check_handler for distribution
print(my_dist.push_check_handler)

# %% [markdown]
# We have created a `Node` that is connected to a `Distribution`, and we can see by inspecting its `push_check_handler`
# that the `Distribution` object has a denial behaviour for push checks (i.e., it says it cannot be pushed to). We can
# verify this by sending a `push_check`.
#
# Remember that a `push_check` requires sending a VQIP (a dictionary with a key for 'volume' and each pollutant
# simulated).
# %%
reply = my_arc.send_push_check({"volume": 10, "phosphate": 1, "temperature": 10})
print(reply)


# %% [markdown]
# The `Distribution` node replied that it can accept 0 water.
#
# But we might try and customise the `my_dist` object so that it calls some function before carrying on with its default push check.


# %%
def custom_handler_function(x):
    """

    Args:
        x:

    Returns:

    """
    print("I reached a custom handler")
    return my_dist.push_check_handler["default"](x)


my_dist.push_check_handler["Node"] = custom_handler_function
print(my_dist.push_check_handler)

# %% [markdown]
# We have added a new custom function for the `'Node'` tag! It includes a print statement so we should be able to see if it is triggered. Note, this is an example of how custom handlers **do not** work!

# %%
reply = my_arc.send_push_check({"volume": 10, "phosphate": 1, "temperature": 10})
print(reply)

# %% [markdown]
# Even though `my_arc` starts at a `Node` object, the custom handler wasn't used. That is because, as explained earlier, if the tag is not specified, the `'default'` tag will always be used, no matter what node type the push check is originating from. Let us instead specify a tag. Note, this is an example of how custom handlers **do** work!

# %%
reply = my_arc.send_push_check(
    {"volume": 10, "phosphate": 1, "temperature": 10}, tag="Node"
)
print(reply)

# %% [markdown]
# Great - we have successfully customised a handler and used it properly.

# %% [markdown]
# ## More realistic example
# A typical kind of behaviour we might be keen to introduce through handlers would be customising how the `Reservoir` object
# responds to pulls. By default, any node can pull from a reservoir:

# %%
from wsimod.nodes.storage import Reservoir

my_reservoir = Reservoir(name="my_reservoir", capacity=10, initial_storage=9)
print(my_reservoir.pull_set_handler)

# %% [markdown]
# We see in the `pull_set_handler` that all pull requests are channeled through the `'default'` tag function, which presumably
# updates the reservoir storage. Let's just verify that:

# %%
# Inspect initial conditions
print("Initial storage: {0}".format(my_reservoir.tank.storage))

# Send a pull request
reply = my_reservoir.pull_set_handler["default"]({"volume": 1})

# Inspect new conditions
print("Amount pulled: {0}".format(reply))
print("Remaining storage: {0}".format(my_reservoir.tank.storage))

# %% [markdown]
# Behaviour as expected, but this might be a problem. Especially if this reservoir is intended only as a raw water supply,
# we may want to customise its handlers such that only the `FWTW` object can pull from it.
#
# Well if we want to do this we will have to take some steps to implement this:
#  1. Create a simple model to test this behaviour.
#  2. Update the reservoir's `pull_set_handler` and `pull_check_handler`.
#  3. Ensure that the `FWTW` pulls from a `Reservoir` with the `'FWTW'` tag.

# %% [markdown]
# ### 1. Create a test model
# We will create two nodes that pull water, a [`FWTW`](https://barneydobson.github.io/wsi/reference-wtw/#wsimod.nodes.wtw.FWTW)
# and a [`Demand`](https://barneydobson.github.io/wsi/reference-other/#wsimod.nodes.demand.Demand). And link them both to
# `my_reservoir`. Under the default behaviour of a `Reservoir`, it can be pulled from both of these node types, but we may decide
# that the water is not clean enough to go straight to `Demand`, and thus wish to customise the handler. (Of course we could more
# simply remove the arc between `my_demand` and `my_reservoir` - but you will have to use your imagination and decide that it is
# better to customise the handler).

# %%
# We will use the previous reservoir

# Create a FWTW
from wsimod.nodes.wtw import FWTW

my_fwtw = FWTW(
    name="my_fwtw",
    service_reservoir_storage_capacity=2,
)

# Create another object to pull from the reservoir, e.g., a demand node
from wsimod.nodes.demand import Demand

my_demand = Demand(name="my_demand", constant_demand=2)

# Link both objects to the reservoir
reservoir_to_fwtw = Arc(
    name="reservoir_to_fwtw", in_port=my_reservoir, out_port=my_fwtw
)
reservoir_to_demand = Arc(
    name="reservoir_to_fwtw", in_port=my_reservoir, out_port=my_demand
)

# %% [markdown]
# By inspecting their documentation, we see that the
# [`create_demand`](https://barneydobson.github.io/wsi/reference-other/#wsimod.nodes.demand.Demand.create_demand)
# function pulls water for a `Demand` node, while the
# [`treat_water`](https://barneydobson.github.io/wsi/reference-wtw/#wsimod.nodes.wtw.FWTW.treat_water)
# does so for a `FWTW` node.

# %%
# Inspect initial conditions
print("Initial storage: {0}".format(my_reservoir.tank.storage))
print(
    "Initial service reservoir storage: {0}".format(
        my_fwtw.service_reservoir_tank.storage
    )
)

# Call function to trigger pulls
my_fwtw.treat_water()

# Inspect new conditions
print("Remaining reservoir storage: {0}".format(my_reservoir.tank.storage))
print(
    "New service reservoir storage: {0}".format(my_fwtw.service_reservoir_tank.storage)
)

# %% [markdown]
# We see some complaint from the `my_fwtw` about sludge (which are also explaining the small losses and why the new service reservoir volume is not quite 2), because it is anticipated to be connected to a sewer, but by inspecting the reservoir volumes we see that the `FWTW` has correctly pulled from the `Reservoir`.
#
# We can verify in a similar way that `my_demand` is able to pull from `my_reservoir`.

# %%
# Inspect initial conditions
print("Initial storage: {0}".format(my_reservoir.tank.storage))
print("Water supplied to demand: {0}".format(my_demand.total_received))

# Call function to trigger pulls
my_demand.create_demand()

# Inspect new conditions
print("Remaining reservoir storage: {0}".format(my_reservoir.tank.storage))
print("Water supplied to demand: {0}".format(my_demand.total_received))

# %% [markdown]
# Again, a complaint that `my_demand` had nowhere to send its sewage, but we can see that it has successfully pulled
# water from `my_reservoir`. Now we will update `my_reservoir` so that it denies pulls unless they have the tag `'FWTW'`.

# %% [markdown]
# ### 2. Update reservoir handlers
# This is a reasonably simple procedure, as we illustrated [above](#illustration).

# %%
# Inspect original handlers
print("Original set handler: {0}".format(my_reservoir.pull_set_handler))
print("Original check handler: {0}".format(my_reservoir.pull_check_handler))

# Copy existing behaviour to only be active for the FWTW tag
my_reservoir.pull_set_handler["FWTW"] = my_reservoir.pull_set_handler["default"]
my_reservoir.pull_check_handler["FWTW"] = my_reservoir.pull_check_handler["default"]

# Overwrite default behaviour to denial
my_reservoir.pull_set_handler["default"] = my_reservoir.pull_set_deny
my_reservoir.pull_check_handler["default"] = my_reservoir.pull_check_deny

# Inspect new handlers
print("Overwritten set handler: {0}".format(my_reservoir.pull_set_handler))
print("Overwritten set handler: {0}".format(my_reservoir.pull_check_handler))

# %% [markdown]
# It seems that we can simply overwrite the handlers in this case, although when you are developing
# new behaviour and overwriting functions you should always check that the new memory addresses of
# the functions seem correct!
#
# Let's verify this behaviour by ensuring that `my_demand` cannot pull from the reservoir
#
# But first we must call the `end_timestep` function for the `my_demand` object. You can find more
# information in the [API](https://barneydobson.github.io/wsi/reference-other/#wsimod.nodes.demand.Demand),
# though in short, the previous call of `create_demand` had already satisfied the water demand for
# that timestep - thus, if we called it again, it would not request any more water.
# %%
# End timestep for demand so that it will request more water
my_demand.end_timestep()

# Inspect initial conditions
print("Initial storage: {0}".format(my_reservoir.tank.storage))
print("Water supplied to demand: {0}".format(my_demand.total_received))

# Call function to trigger pulls
my_demand.create_demand()

# Inspect new conditions
print("Remaining reservoir storage: {0}".format(my_reservoir.tank.storage))
print("Water supplied to demand: {0}".format(my_demand.total_received))

# %% [markdown]
# Fantastic - now we see that `my_demand` is not able to pull from `my_reservoir`, triggering a bunch of warning
# messages that occur when trying to pull from a node with denial behaviour.
#
# However, we also find that now `my_fwtw` cannot pull from `my_reservoir`!
#
# As with `my_demand`, `my_fwtw` can only treat a fixed amount of water each timestep (the
# `treatment_throughput_capacity` parameter), additionally, it will only aim to treat enough
# water to satisfy its service reservoirs. Thus, we must empty the service reservoirs and end the
# timestep for `my_fwtw`.
# %%
# Empty FWTW service reservoirs and end timestep
my_fwtw.service_reservoir_tank.storage["volume"] = 0
my_fwtw.end_timestep()

# Inspect initial conditions
print("Initial storage: {0}".format(my_reservoir.tank.storage))
print(
    "Initial service reservoir storage: {0}".format(
        my_fwtw.service_reservoir_tank.storage
    )
)

# Call function to trigger pulls
my_fwtw.treat_water()

# Inspect new conditions
print("Remaining reservoir storage: {0}".format(my_reservoir.tank.storage))
print(
    "New service reservoir storage: {0}".format(my_fwtw.service_reservoir_tank.storage)
)


# %% [markdown]
# As we have explained above, this is because when `my_fwtw` makes a pull, it sends the `'default'` tag by default, not the `FWTW` tag.

# %% [markdown]
# ### 3. Update `my_fwtw` to pull with `'FWTW'` tag
# Now we need to ensure that `my_fwtw` includes the `'FWTW'` tag when it pulls from the reservoir.
# By inspecting the documentation, we see that `FWTW` pulls water in the
# [`treat_water`](https://barneydobson.github.io/wsi/reference-wtw/#wsimod.nodes.wtw.FWTW.treat_water)
# function using the
# [`pull_distributed`](https://barneydobson.github.io/wsi/reference-nodes/#wsimod.nodes.nodes.Node.pull_distributed)
# function.
#
# Thus, we could either overwrite the `treat_water` function or the `pull_distributed` function.
#
# If we choose the first option, we will essentially have to rewrite the whole function, but ensure that
# `pull_distributed` is called with the tag `'FWTW'`.
#
# If we chose the second option, we can just use a decorator to ensure that every time the `pull_distributed`
# function is called, it is called with the tag `'FWTW'`. Since this seems simpler, we will choose this option.


# %%
def wrap(func):
    """

    Args:
        func:

    Returns:

    """

    def pull_distributed_wrapper(x):
        """

        Args:
            x:

        Returns:

        """
        return func(x, tag="FWTW")

    return pull_distributed_wrapper


my_fwtw.pull_distributed = wrap(my_fwtw.pull_distributed)

# %% [markdown]
# Explaining decorators is outside the scope of this tutorial, though you can
# find more information at: https://www.thecodeship.com/patterns/guide-to-python-function-decorators/
#
# In short what is happening, is we are overwriting the `pull_distributed`
# function so that it is called by a new function with the tag `'FWTW'`, and
# this new function is stored in the `pull_distributed` property of `my_fwtw`.

# %%
# Inspect initial conditions
print("Initial storage: {0}".format(my_reservoir.tank.storage))
print(
    "Initial service reservoir storage: {0}".format(
        my_fwtw.service_reservoir_tank.storage
    )
)

# Call function to trigger pulls
my_fwtw.treat_water()

# Inspect new conditions
print("Remaining reservoir storage: {0}".format(my_reservoir.tank.storage))
print(
    "New service reservoir storage: {0}".format(my_fwtw.service_reservoir_tank.storage)
)

# %% [markdown]
# Fantastic, we've now customised a handler!

# %% [markdown]
# ## What next?
# Surely you are an expert at WSIMOD by now! Why not check our
# [contribution guidelines](https://github.com/barneydobson/wsi/blob/main/docs/CONTRIBUTING.md)!
