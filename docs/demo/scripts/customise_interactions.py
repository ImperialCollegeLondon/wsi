# %% [markdown]
# # Customise interactions (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/customise_interactions.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Illustration](#illustration)
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
# An example of custom handlers can be found in the 
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
# dictionaries. If you do not want to define behaviour for a certain kind of interaction, 
# e.g., maybe you can never pull from this type of node, then you can use, e.g.,
# the `pull_set_deny` and `pull_check_deny` functions for the `default` tag.
#
# It is important to note that unless a tag is specified in the request, the `default`
# tag is used. 
# %% [markdown]
# ## Illustration
# We can the behaviour of handlers by creating a simple model.

# %%
# Import packages
from wsimod.nodes import Node
from wsimod.nodes import Distribution
from wsimod.arcs.arcs import Arc
from wsimod.core import constants

# Set simple pollutants (i.e., temperature and phosphate only)
constants.set_simple_pollutants()

# Create objects
my_node = Node(name = 'my_node')
my_dist = Distribution(name = 'my_dist')
my_arc = Arc(name = 'my_arc', 
             in_port = my_node, 
             out_port = my_dist)

# Inspect push_check_handler for distribution
print(my_dist.push_check_handler)

# %% [markdown]
# We have created a `Node` that is connected to a `Distribution`, and we can see by inspecting its `push_check_handler`
# that the `Distribution` object has a denial behaviour for push checks (i.e., it says it cannot be pushed to). We can 
# verify this by sending a `push_check`.

# %%
reply = my_arc.send_push_check({'volume' : 10, 'phosphate' : 1, 'temperature' : 10})
print(reply)


# %% [markdown]
# The `Distribution` node replied that it can accept 0 water. 
#
# But we might try and customise the `my_dist` object so that it calls some function before carrying on with its default push check.

# %%
def custom_handler_function(x):
    print('I reached a custom handler')
    return my_dist.push_check_handler['default'](x)

my_dist.push_check_handler['Node'] = custom_handler_function
print(my_dist.push_check_handler)

# %% [markdown]
# We have added a new custom function for the `Node` tag! It includes a print statement so we should be able to see if it is triggered. Note, this is an example of how custom handlers **do not** work!

# %%
reply = my_arc.send_push_check({'volume' : 10, 'phosphate' : 1, 'temperature' : 10})
print(reply)

# %% [markdown]
# Even though `my_arc` starts at a `Node` object, the custom handler wasn't used. That is because, as explained earlier, if the tag is not specified, the `default` tag will always be used, no matter what node type the push check is originating from. Let us instead specify a tag. Note, this is an example of how custom handlers **do** work!

# %%
reply = my_arc.send_push_check({'volume' : 10, 'phosphate' : 1, 'temperature' : 10}, tag = 'Node')
print(reply)

# %% [markdown]
# Great - we have successfully customised a handler and used it properly.

# %% [markdown]
# ## More realistic example
# A typical kind of behaviour we might be keen to introduce through handlers would be customising how the `Reservoir` object
# responds to pulls. By default, any node can pull from a reservoir:

# %%
from wsimod.nodes.storage import Reservoir
my_reservoir = Reservoir(name = 'my_reservoir',
                         capacity = 10,
                         initial_storage = 9)
print(my_reservoir.pull_set_handler)

# %% [markdown]
# We see in the `pull_set_handler` that all pull requests are channeled through the `default` tag function, which presumably
# updates the reservoir storage. Let's just verify that:

# %%
print('Initial storage: {0}'.format(my_reservoir.tank.storage))
reply = my_reservoir.pull_set_handler['default']({'volume' : 1})
print('Amount pulled: {0}'.format(reply))
print('Remaining storage: {0}'.format(my_reservoir.tank.storage))

# %% [markdown]
# Behaviour as expected, but this might be a problem. Especially if this reservoir is intended only as a raw water supply, 
# we may want to customise its handlers such that only the `FWTW` object can pull from it.
#
# Well if we want to do this we will have to take some steps to implement this:
#  1. Create a simple model to test this behaviour.
#  2. Update the reservoir's `pull_set_handler` and `pull_check_handler`.
#  3. Ensure that the `FWTW` pulls from a `Reservoir` with the '`FWTW`' tag.

# %% [markdown]
# ### 1. Create a test model
# We will create two nodes that pull water, a [`FWTW`](https://barneydobson.github.io/wsi/reference-wtw/#wsimod.nodes.wtw.FWTW) 
# and a [`Demand`](https://barneydobson.github.io/wsi/reference-other/#wsimod.nodes.demand.Demand). And link them both to
# `my_reservoir`. Under the default behaviour of a `Reservoir`, both of these nodes can pull from a Reservoir, but we may decide
# that the water is not clean enough to go straight to `Demand`, and thus wish to customise.

# %%
# We will use the previous reservoir

# Create a FWTW
from wsimod.nodes.wtw import FWTW
my_fwtw = FWTW(name='my_fwtw',
               service_reservoir_storage_capacity = 2,
               )

# Create another object to pull from the reservoir, e.g., a demand node
from wsimod.nodes.demand import Demand
my_demand = Demand(name = 'my_demand',
                   constant_demand = 2)

# Link both objects to the reservoir
reservoir_to_fwtw = Arc(name = 'reservoir_to_fwtw',
                        in_port = my_reservoir,
                        out_port = my_fwtw)
reservoir_to_demand = Arc(name = 'reservoir_to_fwtw',
                          in_port = my_reservoir,
                          out_port = my_demand)

# %% [markdown]
# By inspecting their documentation, we see that the 
# [`create_demand`](https://barneydobson.github.io/wsi/reference-other/#wsimod.nodes.demand.Demand.create_demand) 
# function pulls water for a `Demand` node, while the
# [`treat_water`](https://barneydobson.github.io/wsi/reference-wtw/#wsimod.nodes.wtw.FWTW.treat_water)
# does so for a `FWTW` node.

# %%
print('Initial storage: {0}'.format(my_reservoir.tank.storage))
print('Initial service reservoir storage: {0}'.format(my_fwtw.service_reservoir_tank.storage))
my_fwtw.treat_water()
print('New service reservoir storage: {0}'.format(my_reservoir.tank.storage))
print('New service reservoir storage: {0}'.format(my_fwtw.service_reservoir_tank.storage))

# %% [markdown]
# We see some complaint from the `my_fwtw` about sludge, because it is anticipated to be connected to a sewer, but by inspecting the reservoir volumes we see that the `FWTW` has correctly pulled from the `Reservoir`.
#
# s from the two nodes, because their intended behaviour is that they are connected to sewers, 
# but importantly we see that they have both pulled water from `my_reservoir`. `my_fwtw` aims to fill its service
# reservoirs, which have a capacity of 2 and were initialised empty

# %%
