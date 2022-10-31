# %% [markdown]
# # Customise a node (.py)
# Note - this script can also be opened in interactive Python if you wanted to
# play around. On the GitHub it is in docs/demo/scripts/customise_a_node.py
#
# 1. [Introduction](#Introduction)
#
# 2. [Create baseline](#Create-baseline)
#
# 3. [Customise node](#Customise-node)
#
# 4. [Inspect results](#Inspect-results)
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
# We copy all of the model creation code from the oxford demo into a single 
# function below, you will want to ignore this and skip to [create baselin](#Create-baseline)
# %%
def create_oxford_model(data_folder):
    from wsimod.nodes.wtw import WWTW, FWTW
    from wsimod.nodes.waste import Waste
    from wsimod.nodes.storage import Groundwater, Reservoir
    from wsimod.nodes.catchment import Catchment
    from wsimod.nodes.demand import ResidentialDemand
    from wsimod.nodes.land import Land
    from wsimod.nodes.sewer import Sewer
    from wsimod.nodes.nodes import Node
    from wsimod.orchestration.model import Model
    from wsimod.arcs.arcs import Arc
    from wsimod.core import constants
    import os
    import pandas as pd
    input_fid = os.path.join(data_folder, "processed", "timeseries_data.csv")
    input_data = pd.read_csv(input_fid)
    input_data.loc[input_data.variable == 'flow', 'value'] *= constants.M3_S_TO_M3_DT
    input_data.loc[input_data.variable == 'precipitation', 'value'] *= constants.MM_TO_M
    input_data.date = pd.to_datetime(input_data.date)
    data_input_dict = input_data.set_index(['variable','date']).value.to_dict()
    data_input_dict = input_data.groupby('site').apply(lambda x: x.set_index(['variable','date']).value.to_dict()).to_dict()
    dates = input_data.date.unique()
    dates.sort()
    dates = [pd.Timestamp(x) for x in dates]
    constants.POLLUTANTS = input_data.variable.unique().tolist()
    constants.POLLUTANTS.remove('flow')
    constants.POLLUTANTS.remove('precipitation')
    constants.POLLUTANTS.remove('et0')
    constants.NON_ADDITIVE_POLLUTANTS = ['temperature']
    constants.ADDITIVE_POLLUTANTS = list(set(constants.POLLUTANTS).difference(constants.NON_ADDITIVE_POLLUTANTS))
    constants.FLOAT_ACCURACY = 1E-8
    thames_above_abingdon = Waste(name = 'thames_above_abingdon')
    farmoor_abstraction = Node(name = 'farmoor_abstraction')
    evenlode_thames = Node(name = 'evenlode_thames')
    cherwell_ray = Node(name = 'cherwell_ray')
    cherwell_thames = Node(name = 'cherwell_thames')
    thames_mixer = Node(name = 'thames_mixer')
    evenlode = Catchment(name = 'evenlode',
                         data_input_dict = data_input_dict['evenlode'])
    thames = Catchment(name = 'thames',
                       data_input_dict = data_input_dict['thames'])
    ray = Catchment(name = 'ray',
                    data_input_dict = data_input_dict['ray'])
    cherwell = Catchment(name = 'cherwell',
                         data_input_dict = data_input_dict['cherwell'])
    oxford_fwtw = FWTW(service_reservoir_storage_capacity = 1e5,
                      service_reservoir_storage_area = 2e4,
                      service_reservoir_initial_storage = 0.9e5,
                      treatment_throughput_capacity = 4.5e4,
                      name = 'oxford_fwtw')
    land_inputs = data_input_dict['oxford_land']
    pollutant_deposition = {'boron' : 100e-10,
                                  'calcium' : 70e-7,
                                  'chloride' : 60e-10,
                                  'fluoride' : 0.2e-7,
                                  'magnesium' : 6e-7,
                                  'nitrate' : 2e-9,
                                  'nitrogen' : 4e-7,
                                  'potassium' : 7e-7,
                                  'silicon' : 7e-9,
                                  'sodium' : 30e-9,
                                  'sulphate' : 70e-7}
    surface = [{'type_' : 'PerviousSurface',
              'area' : 2e7,
              'pollutant_load' : pollutant_deposition,
               'surface' : 'rural',
               'field_capacity' : 0.3,
               'depth' : 0.5,
               'initial_storage' : 2e7 * 0.4 * 0.5},
               {'type_' : 'ImperviousSurface',
               'area' : 1e7,
               'pollutant_load' : pollutant_deposition,
                'surface' : 'urban',
                'initial_storage' : 5e6}]
    oxford_land = Land(surfaces = surface,
                       name = 'oxford_land',
                       data_input_dict = land_inputs
                       )
    oxford = ResidentialDemand(name = 'oxford',
                               population = 2e5,
                               per_capita = 0.15,
                               pollutant_load =  
                               {'boron' : 500 * constants.UG_L_TO_KG_M3 * 0.15,
                                 'calcium' : 150 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'chloride' : 180 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'fluoride' : 0.4 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'magnesium' : 30 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'nitrate' : 60 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'nitrogen' : 50 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'potassium' : 30 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'silicon' : 20 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'sodium' : 200 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'sulphate' : 250 * constants.MG_L_TO_KG_M3 * 0.15,
                                 'temperature' : 14},
                               data_input_dict = land_inputs
                              )
    farmoor = Reservoir(name = 'farmoor',
                        capacity = 1e7,
                        initial_storage = 1e7,
                        area = 1.5e6,
                        datum = 62)
    distribution = Node(name = 'oxford_distribution')
    oxford_wwtw = WWTW(stormwater_storage_capacity = 2e4,
                      stormwater_storage_area = 2e4,
                      treatment_throughput_capacity = 5e4,
                      name = 'oxford_wwtw')
    combined_sewer = Sewer(capacity = 4e6,
                           pipe_timearea = {0 : 0.8,
                                            1 : 0.15,
                                            2 : 0.05
                                            },
                           name = 'combined_sewer'
                           )
    gw = Groundwater(capacity = 3.2e9,
                     area = 3.2e8,
                     name = 'gw',
                     residence_time = 20
                     )
    nodelist = [thames_above_abingdon,
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
                thames_mixer]
    fwtw_to_distribution = Arc(in_port = oxford_fwtw,
                               out_port = distribution,
                               name = 'fwtw_to_distribution')
    abstraction_to_farmoor = Arc(in_port = farmoor_abstraction,
                        out_port = farmoor,
                        name = 'abstraction_to_farmoor',
                        capacity = 5e4)
    sewer_to_wwtw = Arc(in_port = combined_sewer,
                        out_port = oxford_wwtw,
                        preference = 1e10,
                        name = 'sewer_to_wwtw')
    sewer_overflow = Arc(in_port = combined_sewer,
                         out_port = thames_mixer,
                         preference = 1e-10,
                         name = 'sewer_overflow')
    evenlode_to_thames = Arc(in_port = evenlode,
                        out_port = evenlode_thames,
                        name = 'evenlode_to_thames')
    
    thames_to_thames = Arc(in_port = thames,
                        out_port = evenlode_thames,
                        name = 'thames_to_thames')
    
    ray_to_cherwell = Arc(in_port = ray,
                        out_port = cherwell_ray,
                        name = 'ray_to_cherwell')
    
    cherwell_to_cherwell = Arc(in_port = cherwell,
                        out_port = cherwell_ray,
                        name = 'cherwell_to_cherwell')
    
    thames_to_farmoor = Arc(in_port = evenlode_thames,
                        out_port = farmoor_abstraction,
                        name = 'thames_to_farmoor')
    
    farmoor_to_mixer = Arc(in_port = farmoor_abstraction,
                        out_port = thames_mixer,
                        name = 'farmoor_to_mixer')
    
    cherwell_to_mixer = Arc(in_port = cherwell_ray,
                        out_port = thames_mixer,
                        name = 'cherwell_to_mixer')
    
    wwtw_to_mixer = Arc(in_port = oxford_wwtw,
                        out_port = thames_mixer,
                        name = 'wwtw_to_mixer')
    
    mixer_to_waste = Arc(in_port = thames_mixer,
                        out_port = thames_above_abingdon,
                        name = 'mixer_to_waste')
    
    distribution_to_demand = Arc(in_port = distribution,
                                 out_port = oxford,
                                 name = 'distribution_to_demand')
    
    reservoir_to_fwtw = Arc(in_port = farmoor,
                               out_port = oxford_fwtw,
                               name = 'reservoir_to_fwtw')
    
    fwtw_to_sewer = Arc(in_port = oxford_fwtw,
                        out_port = combined_sewer,
                        name = 'fwtw_to_sewer')
    
    demand_to_sewer = Arc(in_port = oxford,
                        out_port = combined_sewer,
                        name = 'demand_to_sewer')
    
    land_to_sewer = Arc(in_port = oxford_land,
                        out_port = combined_sewer,
                        name = 'land_to_sewer')
    
    land_to_gw = Arc(in_port = oxford_land,
                        out_port = gw,
                        name = 'land_to_gw')
    
    garden_to_gw = Arc(in_port = oxford,
                        out_port = gw,
                        name = 'garden_to_gw')
    
    gw_to_mixer = Arc(in_port = gw,
                        out_port = thames_mixer,
                        name = 'gw_to_mixer')
    arclist = [evenlode_to_thames,
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
                gw_to_mixer]
    my_model = Model()
    my_model.add_instantiated_nodes(nodelist)
    my_model.add_instantiated_arcs(arclist)
    my_model.dates = dates
    return my_model
# %% [markdown]
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

# %% [markdown]
# The model can be automatically created using the data_folder
# %%
data_folder= os.path.join(os.path.abspath(''),
                               "docs","demo","data")

# data_folder = os.path.join(os.path.split(os.path.abspath(''))[0],"data") #Use this path if opening in jupyter

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
f, axs = plt.subplots(3,1,figsize=(6,6))
baseline_flows.groupby('arc').get_group('farmoor_to_mixer').set_index('time')[['flow']].plot(ax=axs[0], title = 'River flow downstream of abstractions')
axs[0].set_yscale('symlog')
axs[0].set_ylim([10e3,10e7])
baseline_flows.groupby('arc').get_group('abstraction_to_farmoor').set_index('time')[['flow']].plot(ax=axs[1], title = 'Abstraction')
axs[1].legend()

baseline_tanks.groupby('node').get_group('farmoor').set_index('time')[['storage']].plot(ax=axs[2], title ='Reservoir storage')
axs[2].legend()
f.tight_layout()


# %% [markdown]
# ## Customise node
# To protect the river from abstractions during low flows, we can customise the
# abstraction node to implement a MRF.
#
# Our new node will want to behave exactly the same as the old node, but with
# different behaviour when another node is pulling water from it. Thus we will 
# define new functions to accommodate this.
#
# The first function we will define is a 'pull_check' - that is, how should the 
# node respond when another node queries how much water could be pulled from it.
# 
# The only new line in comparison to that defined in the 
# [default node](./../../../reference-nodes/#wsimod.nodes.nodes.Node) is where
# we 'Apply MRF'. We introduce two new variables, one for the minimum required
# flow (mrf), and one for the mrf already satisfied. 
# %%
def pull_check_mrf(node,vqip = None):
    #Respond to a pull check to the node
    
    #Work out how much water is available upstream
    reply = node.pull_check_basic()
    
    #Apply MRF
    reply['volume'] = max(reply['volume'] - (node.mrf - node.mrf_satisfied_this_timestep), 0)
    
    #If the pulled amount has been specified, pick the minimum of the available and that
    if vqip is not None:
        reply['volume'] = min(reply['volume'], vqip['volume'])
    
    #Return avaiable
    return reply

# %% [markdown]
# We must also define what will happen during a 'pull set' - that is, how should
# the node respond when another node requests water to pull from it.
#
# The default function for a node to do this is 'pull_distributed', which pulls
# water from upstream nodes. We still call pull_distributed, however we 
# increase the amount we request via it by the amount of MRF yet to satisfy. 
# Any water which satsifies the MRF goes towards mrf_satisfied_this_timestep, 
# then the rest is available in the 'reply', for use in the pull request.
# Finally, we route the water that was used to satisfy the mrf downstream so 
# that it cannot be used again this timestep.
# %%
def pull_set_mrf(node, vqip):
    #Respond to a pull request to the node
    
    #Copy the request for boring reasons
    request = node.copy_vqip(vqip)
    
    #Increase the request by the amount of MRF not yet satisfied
    request['volume'] += (node.mrf - node.mrf_satisfied_this_timestep)
    
    #Pull the new updated request from upstream nodes
    reply = node.pull_distributed(request)
    
    #First satisfy the MRF
    reply_to_mrf = min((node.mrf - node.mrf_satisfied_this_timestep), reply['volume'])
    node.mrf_satisfied_this_timestep += reply_to_mrf
    
    reply_to_mrf = node.v_change_vqip(reply, reply_to_mrf)
    
    #Update reply (less the amount for MRF)
    reply = node.extract_vqip(reply, reply_to_mrf)
    
    #Then route that water downstream so it is not available
    mrf_route_reply = node.push_distributed(reply_to_mrf, of_type = ['Node'])
    if mrf_route_reply['volume'] > constants.FLOAT_ACCURACY:
        print('warning MRF not able to push')
        
    #Return pulled amount
    return reply
# %% [markdown]
# We should also adjust the behaviour of a 'push set' - that is, how should the 
# node respond when another node pushes water to it. We will need to do this 
# because we want water that this node sends downstream on interactions that
# are not to do with pulls to still update the minimum required flow. 
# 
# The default behaviour for a node to do a push set is 'push_distributed', which
# pushes water to downstream nodes. We do this as normal, but then update the 
# mrf_satisfied_this_timestep 
# %%
def push_set_mrf(node, vqip):
    #Respond to a push request to the node
    
    #Push water downstream
    reply = node.push_distributed(vqip)
    total_pushed_downstream = vqip['volume'] - reply['volume']
    
    #Allow this water to contribute to mrf
    node.mrf_satisfied_this_timestep = min(node.mrf, 
                                           node.mrf_satisfied_this_timestep + total_pushed_downstream)
    
    #Return the amount not pushed
    return reply


# %% [markdown]
# We also create a function to reset the mrf_satisfied_this_timestep at the end
# of each timestep
# %%
def end_timestep(node):
    #Update MRF satisfied
    node.mrf_satisfied_this_timestep = 0

# %% [markdown]
# Finally we write a wrapper to assign the predefined functions to the node, 
# and to set the mrf parameter.
# %%
def convert_to_mrf(node,
                   mrf = 5):

    #Initialise MRF variables
    node.mrf = mrf
    node.mrf_satisfied_this_timestep = 0
    
    #Change pull functions to the ones defined above
    node.pull_set_handler['default'] = lambda x : pull_set_mrf(node, x)
    node.pull_check_handler['default'] = lambda x : pull_check_mrf(node, x)
    
    #Change end timestep function to one defined above
    node.end_timestep = lambda : end_timestep(node)

# %% [markdown]
# Now we can create a new model
# %%
customised_model = create_oxford_model(data_folder)

# %% [markdown]
# .. and convert the abstraction node to apply an MRF
# %%
new_mrf = 3 * constants.M3_S_TO_M3_DT
convert_to_mrf(customised_model.nodes['farmoor_abstraction'], mrf = new_mrf)

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

f, axs = plt.subplots(3,1,figsize=(6,6))
plot_flows1 = pd.concat([baseline_flows.groupby('arc').get_group('farmoor_to_mixer').set_index('time').flow.rename('Baseline'),
                        flows_mrf.groupby('arc').get_group('farmoor_to_mixer').set_index('time').flow.rename('Customised')],
                       axis=1)
plot_flows1.plot(ax=axs[0], title = 'River flow downstream of abstractions')
plot_mrf = pd.DataFrame(index = [customised_model.dates[0], 
                                 customised_model.dates[-1]],
                        columns = ['MRF'],
                        data = [new_mrf, new_mrf])
plot_mrf.plot(ax=axs[0],
              color = 'r',
              ls = '--')
axs[0].set_yscale('symlog')
axs[0].set_ylim([10e3,10e7])

plot_flows2 = pd.concat([baseline_flows.groupby('arc').get_group('abstraction_to_farmoor').set_index('time').flow.rename('Baseline'),
                        flows_mrf.groupby('arc').get_group('abstraction_to_farmoor').set_index('time').flow.rename('Customised')],
                       axis=1)
plot_flows2.plot(ax=axs[1], title = 'Abstraction')
axs[1].legend()

plot_tanks = pd.concat([baseline_tanks.groupby('node').get_group('farmoor').set_index('time').storage.rename('Baseline'),
                        tanks_mrf.groupby('node').get_group('farmoor').set_index('time').storage.rename('Customised')],
                       axis=1)
plot_tanks.plot(ax=axs[2], title ='Reservoir storage')
axs[2].legend()
f.tight_layout()
