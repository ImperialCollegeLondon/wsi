# %% [markdown]
# # Customise a RiverReservoir node (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in [docs/demo/scripts](https://github.com/barneydobson/wsi/blob/main/docs/demo/scripts/customise_riverreservoir.py)
#
# 1. [Introduction](#introduction)
#
# 2. [Climate inputs](#climate-inputs)
#
# 3. [Environmental flows](#environmental-flows)
#
# 4. [Infiltration](#infiltration)
#
# 5. [What next](#what-next)
#

# %% [markdown]
# ## Introduction
# In this tutorial we will demonstrate how to customise a
# [`RiverReservoir`](https://barneydobson.github.io/wsi/reference-storage/#wsimod.nodes.storage.RiverReservoir)
# node. This is a run-of-river reservoir, but only a minimal implementation
# is provided, which does not capture many of the processes that WSIMOD users
# are likely to require.
#
# Rather than customise the `RiverReservoir` node, we would prefer to equip
# users with the ability to customise WSIMOD behaviour to accommodate the
# almost infinite range of possibilities of how would you like a node to behave.
#
# Thus in this guide, we will customise a `RiverReservoir` node to include the following
# processes:
#  - Precipitation/evapotranspiration from the reservoir surface. This is an example of
#  assigning input data to a node.
#  - Ensure that environmental flows are satisfied. This is an example of calling an
#  additional function during the orchestration of a node.
#  - Infiltration to attached groundwater nodes. This is an example of adding new behaviour
#  to a node

# %%
# Import packages
from pprint import pprint as print

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.storage import Groundwater, RiverReservoir
from wsimod.nodes.waste import Waste
from wsimod.orchestration.model import Model, to_datetime

# Set simple pollutants
constants.set_simple_pollutants()
# %% [markdown]
# We will create a simple model that includes a reservoir, a groundwater, and an outlet.
# %%
# Create nodes
my_reservoir = RiverReservoir(
    name="my_reservoir", capacity=10, area=5, initial_storage=6, environmental_flow=1
)

my_groundwater = Groundwater(
    name="my_groundwater", capacity=100, area=10, initial_storage=50
)

my_outlet = Waste(name="my_outlet")

# %% [markdown]
# We provide arcs for reservoir outflow (i.e., the environmental flow), the infiltration which we
# will later include, and a baseflow of groundwater.

# %%
# Create arcs
infiltration_arc = Arc(
    name="infiltration", in_port=my_reservoir, out_port=my_groundwater
)

environmental_arc = Arc(name="environmental", in_port=my_reservoir, out_port=my_outlet)

baseflow_arc = Arc(name="baseflow", in_port=my_groundwater, out_port=my_outlet)

# %%
# Create and populate model
my_model = Model()

my_model.add_instantiated_nodes([my_reservoir, my_groundwater, my_outlet])

my_model.add_instantiated_arcs([infiltration_arc, environmental_arc, baseflow_arc])

# Assign a date to run model for
date = to_datetime("2000-01-01")

# %%
# Run model
results = my_model.run(dates=[date])

# Inspect flows
flow = results[0]
print(flow)

stores = results[1]
print(stores)

# %% [markdown]
# We can see here that the only process that has happened is some groundwater baseflow.
# Neither the climate forcing, nor environmental flow, nor infiltration occur by default,
# despite that we have included arcs to connect them. This is because in the case of
# climate flow and infiltration, the behaviour is not yet defined. While, for environmental
# flows, we can see that a [`satisfy_environmental`](https://barneydobson.github.io/wsi/reference-storage/#wsimod.nodes.storage.RiverReservoir.satisfy_environmental)
# function is provided in the API - however it is not called in the default model orchestration.
#
# Thus, we will customise our node to address all of these points.
# %% [markdown]
# ## Climate inputs

# %% [markdown]
# ### Define inputs
# We need to define some precipitation/evapotranspiration climate data to
# force the reservoir with, and then store that information.

# %%
# Create climate data
climate_data = {("precipitation", date): 0.01, ("et0", date): 0.005}

# Give reservoir node access to it
my_reservoir.data_input_dict = climate_data

# %% [markdown]
# ### Mass balance
# The first thing we should always consider is how our change will impact mass
# balance checking, since there is nothing more annoying than our model throwing
# a bunch of mass balance errors.
#
# To do this we will create two state variables `net_evaporation` and
# `net_precipitation` that belong to the `my_reservoir` node. Every object in
# WSIMOD has three lists related to mass balance checking: `mass_balance_in`,
# `mass_balance_out`, and `mass_balance_ds`. You can read more about it in the [API](https://barneydobson.github.io/wsi/reference-core/#wsimod.core.core.WSIObj.mass_balance)
# but in short, any changes we make need to be appended as functions to these
# lists.
#
# Thus, we store these state variables in a `lambda` call in the lists. Note that
# we have given the `self = my_reservoir` argument in the `lamdba` call to ensure
# that the function gets stored in the node's memory, rather than hard coded to
# this point in the script.
# %%
# Add mass balance terms
my_reservoir.net_evaporation = my_reservoir.empty_vqip()
my_reservoir.mass_balance_out.append(lambda self=my_reservoir: self.net_evaporation)

my_reservoir.net_precipitation = my_reservoir.empty_vqip()
my_reservoir.mass_balance_in.append(lambda self=my_reservoir: self.net_precipitation)


# %% [markdown]
# ### Add new behaviour
# Now we need to add the processes by which evaporation/precipitation happens to
# the surface of the reservoir. Our first task is to figure out how this behaviour might be called during orchestration. If we inspect the source code
# in the [`Model`](https://barneydobson.github.io/wsi/reference-model/#wsimod.orchestration.model.Model.run)
# object, we will see what functions are called during orchestration (i.e., the
# `run` function of the `Model`). We can see that the only function called for
# `Reservoir` objects is the `make_abstractions` function. Thus, the simplest way
# for us to add new behaviour to a `Reservoir` is to 'decorate' this function.
#
# Note that this is only the right solution if we are happy that these functions
# take place at this point of orchestration. For example, we might be happy for
# the climate processes to occur at any point in the timestep, but if we view the
# order of operations, we might be less sure that infiltration occurs after
# groundwater has been distributed. For the purpose of this demo though, we will
# assume that we are happy for all of our new reservoir behaviour to take place
# at the same time within a timestep.
#
# As mentioned, we must decorate our `make_abstractions` function. To do this we
# provide a wrapper for the new behaviour that also calls the original function.
# Then we overwrite the memory address of the original function in the object to
# perform this new wrapped function. Decorators can be a bit to get your head around, you can read more about them at: https://www.thecodeship.com/patterns/guide-to-python-function-decorators/.
#
# The equations that we need to add for this are reasonably self-explanatory, and
# take place inside the `reservoir_functions_wrapper`.
# %%
# Decorate reservoir to include climate processes
def wrapper(node, func):
    """

    Args:
        node:
        func:

    Returns:

    """

    def reservoir_functions_wrapper():
        """

        Returns:

        """
        # Initialise mass balance VQIPs
        vqip_out = node.empty_vqip()
        vqip_in = node.empty_vqip()

        # Calculate net change
        net_in = node.get_data_input("precipitation") - node.get_data_input("et0")
        net_in *= node.tank.area

        if net_in > 0:
            # Add precipitation
            vqip_in = node.v_change_vqip(node.empty_vqip(), net_in)
            _ = node.tank.push_storage(vqip_in, force=True)

        else:
            # Remove evaporation
            evap = node.tank.evaporate(-net_in)
            vqip_out = node.v_change_vqip(vqip_out, evap)

        # Store in mass balance states
        my_reservoir.net_evaporation = vqip_out
        my_reservoir.net_precipitation = vqip_in

        # Call whatever else was going happen
        return func()

    return reservoir_functions_wrapper


# Run decorator
my_reservoir.make_abstractions = wrapper(my_reservoir, my_reservoir.make_abstractions)

# %% [markdown]
# OK fantastic, there's no new flows along the arcs, though the baseflow has reduced a bit because it is based on the total groundwater storage which has decreased in our previous example.
#
# Most importantly we see that the reservoir volume has increased by 0.025m3, thus our new functionality seems to work. Next we will include environmental
# flows.

# %%
# Reinspect results
results = my_model.run(dates=[date])

flow = results[0]
print(flow)

stores = results[1]
print(stores)


# %% [markdown]
# ## Environmental flows
# As mentioned, the `RiverReservoir` object already has a parameter
# (`environmental_flow`) and a function (`satisfy_environmental`) to carry out
# releases for environmental flows. So all we need to do is redecorate our
# `make_abstractions` function to call this new function.
# %%
# Decorate reservoir to include environmental flows
def wrapper(node, func):
    """

    Args:
        node:
        func:

    Returns:

    """

    def reservoir_functions_wrapper():
        """

        Returns:

        """
        node.satisfy_environmental()
        return func()

    return reservoir_functions_wrapper


my_reservoir.make_abstractions = wrapper(my_reservoir, my_reservoir.make_abstractions)

# %% [markdown]
# Notice how we were able to just pass the decorated version of the
# `make_abstractions` function, since that version of the function is still
# containing all of the new climate behaviour. In practice, this isn't very transparent and we would make one wrapper that includes all of the new
# functionality that we want to add, but it is fine for the demo.
#
# We now see that the `environmental_flow` of 1 has been satisfied along the arc from the reservoir to the outlet. We also see that the reservoir storage has decreased by this amount but increased by the precipitation amount again, which means our climate functions are still working fine.
#
# We also see an incredibly small amount of flow along the infiltration arc, this is because of how the `push_distributed` function called by `satisfy_environmental` works, which is behaviour for another tutorial, but can be considered negligible for this demo.
# %%
# Reinspect results
results = my_model.run(dates=[date])

flow = results[0]

print(flow)

stores = results[1]
print(stores)

# %% [markdown]
# ## Infiltration
# Our final task is to implement infiltration. We are cool hands at decorating
# now so should feel confident that we simply need to add some new functionality
# within a wrapper and decorate the `make_abstractions` function.
# %%
# Decorate reservoir to include infiltration
my_reservoir.infiltration_rate = 0.002  # [metres per timestep]


def wrapper(node, func):
    """

    Args:
        node:
        func:

    Returns:

    """

    def reservoir_functions_wrapper():
        """

        Returns:

        """
        # Calculate infiltration amount
        infiltration_amount = node.infiltration_rate * node.tank.area

        # Extract from reservoir tank
        infiltration_vqip = node.tank.pull_storage({"volume": infiltration_amount})

        # Distribute to any connected groundwater nodes
        reply = node.push_distributed(infiltration_vqip, of_type="Groundwater")

        # If any was not successfully received, store this back in the reservoir
        node.tank.push_storage(reply, force=True)
        return func()

    return reservoir_functions_wrapper


my_reservoir.make_abstractions = wrapper(my_reservoir, my_reservoir.make_abstractions)
# %% [markdown]
# Sure enough, our infiltration works!
# %%
# Reinspect results
results = my_model.run(dates=[date])

flow = results[0]

print(flow)

stores = results[1]
print(stores)

# %% [markdown]
# ## What next?
# If you found this a little complicated, don't worry, we were doing some quite
# complicated things to our nodes. In general, it is easier to customise the
# interactions between nodes than the nodes themselves. You can find out more
# about this in our
# [`customise_interactions`](https://barneydobson.github.io/wsi/demo/scripts/customise_interactions/)
# guide!
