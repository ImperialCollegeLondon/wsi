# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 10:50:55 2023

@author: bdobson
"""
from wsimod.core import constants
import sys
import os
from tqdm import tqdm
from math import log10
from wsimod.nodes.land import ImperviousSurface
from wsimod.nodes.nodes import QueueTank, Tank, ResidenceTank

def extensions(model):
    # Apply customations
    model.nodes['my_groundwater'].residence_time *= 2
    
    # Add dcorator to a reservoir
    model.nodes['my_reservoir'].net_evaporation = model.nodes['my_reservoir'].empty_vqip()
    model.nodes['my_reservoir'].mass_balance_out.append(lambda self=model.nodes['my_reservoir']: self.net_evaporation)
    model.nodes['my_reservoir'].net_precipitation = model.nodes['my_reservoir'].empty_vqip()
    model.nodes['my_reservoir'].mass_balance_in.append(lambda self=model.nodes['my_reservoir']: self.net_precipitation)

    model.nodes['my_reservoir'].make_abstractions = wrapper_reservoir(model.nodes['my_reservoir'], model.nodes['my_reservoir'].make_abstractions)
    
    # Change model.run because new function has been introduced by the new node
    model.run = wrapper_run(model)
    
def wrapper_reservoir(node, func):
    def reservoir_functions_wrapper():
        # Initialise mass balance VQIPs
        vqip_out = node.empty_vqip()
        vqip_in = node.empty_vqip()
        
        # Calculate net change
        net_in = node.get_data_input('precipitation') - node.get_data_input('et0')
        net_in *= node.tank.area
        
        if net_in > 0:
            # Add precipitation
            vqip_in = node.v_change_vqip(node.empty_vqip(), net_in)
            _ = node.tank.push_storage(vqip_in, force = True)
            
        else:
            # Remove evaporation
            evap = node.tank.evaporate(-net_in)
            vqip_out = node.v_change_vqip(vqip_out, evap)
        
        # Store in mass balance states
        node.net_evaporation = vqip_out
        node.net_precipitation = vqip_in
        
        node.satisfy_environmental()
        # Call whatever else was going happen
        return func()
    return reservoir_functions_wrapper

def wrapper_run(self):
    def run(#self, 
            dates = None,
            settings = None,
            record_arcs = None,
            record_tanks = None,
            verbose = True,
            record_all = True,
            other_attr = {}):
        """Run the model object with the default orchestration
    
        Args:
            dates (list, optional): Dates to simulate. Defaults to None, which
                simulates all dates that the model has data for.
            settings (dict, optional): Dict to specify what results are stored,
                not currently used. Defaults to None.
            record_arcs (list, optional): List of arcs to store result for. 
                Defaults to None.
            record_tanks (list, optional): List of nodes with water stores to 
                store results for. Defaults to None.
            verbose (bool, optional): Prints updates on simulation if true. 
                Defaults to True.
            record_all (bool, optional): Specifies to store all results.
                Defaults to True.
            other_attr (dict, optional): Dict to store additional attributes of 
                specified nodes/arcs. Example: 
                {'arc.name1': ['arc.attribute1'],
                 'arc.name2': ['arc.attribute1', 'arc.attribute2'],
                 'node.name1': ['node.attribute1'],
                 'node.name2': ['node.attribute1', 'node.attribute2']}
                Defaults to None.
    
        Returns:
            flows: simulated flows in a list of dicts
            tanks: simulated tanks storages in a list of dicts
            node_mb: mass balance differences in a list of dicts (not currently used)
            surfaces: simulated surface storages of land nodes in a list of dicts
            requested_attr: timeseries of attributes of specified nodes/arcs requested by the users
        """
        
        if record_arcs is None:
            record_arcs = self.arcs.keys()
            
        if record_tanks is None:
            record_tanks = []
        
        if settings is None:
            settings = self.default_settings()
            
        def blockPrint():
            stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            return stdout
        def enablePrint(stdout):
            sys.stdout = stdout
        if not verbose:
            stdout = blockPrint() 
        if dates is None:
            dates = self.dates
        
        flows = []
        tanks = []
        node_mb = []
        surfaces = []
        for date in tqdm(dates, disable = (not verbose)):
        # for date in dates:
            for node in self.nodelist:
                node.t = date
                node.monthyear = date.to_period('M')
            
            #Run FWTW
            for node in self.nodes_type['FWTW'].values():
                node.treat_water()
            
            #Create demand (gets pushed to sewers)
            for node in self.nodes_type['Demand'].values():
                node.create_demand()
            
            #Create runoff (impervious gets pushed to sewers, pervious to groundwater)
            for node in self.nodes_type['Land'].values():
                node.run()
            
            #Infiltrate GW
            for node in self.nodes_type['Groundwater'].values():
                node.infiltrate()
            for node in self.nodes_type['Groundwater_h'].values():
                node.infiltrate()
            
            #Discharge sewers (pushed to other sewers or WWTW)
            for node in self.nodes_type['Sewer'].values():
                node.make_discharge()
                
            #Foul second so that it can discharge any misconnection
            for node in self.nodes_type['Foul'].values():
                node.make_discharge()
           
            #Discharge WWTW
            for node in self.nodes_type['WWTW'].values():
                node.calculate_discharge()
            
            #Discharge GW
            for node in self.nodes_type['Groundwater'].values():
                node.distribute()
            
            for node in self.nodes_type['Groundwater_h'].values():
                node.distribute_gw_gw()
            for node in self.nodes_type['Groundwater_h'].values():
                node.distribute_gw_rw()
            
            #river
            # for node in self.nodes_type['Lake'].values():
            #     node.calculate_discharge()
            for node in self.nodes_type['River'].values():
                node.calculate_discharge()
            
            #Abstract
            for node in self.nodes_type['Reservoir'].values():
                node.make_abstractions()
            
            for node in self.nodes_type['Land'].values():
                node.apply_irrigation()
    
            for node in self.nodes_type['WWTW'].values():    
                node.make_discharge()
            
            #Catchment routing
            for node in self.nodes_type['Catchment'].values():
                node.route()
            
            #river
            # for node in self.nodes_type['Lake'].values():
            #     node.distribute()
            for node_name in self.river_discharge_order:
                self.nodes[node_name].distribute()
            
            
            #mass balance checking
            #nodes/system
            sys_in = self.empty_vqip()
            sys_out = self.empty_vqip()
            sys_ds = self.empty_vqip()
            
            #arcs
            for arc in self.arcs.values():            
                in_, ds_, out_ = arc.arc_mass_balance()
                for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                    sys_in[v] += in_[v]
                    sys_out[v] += out_[v]
                    sys_ds[v] += ds_[v]
            for node in self.nodelist:
                # print(node.name)
                in_, ds_, out_ = node.node_mass_balance()
                
                # temp = {'name' : node.name,
                #         'time' : date}
                # for lab, dict_ in zip(['in','ds','out'], [in_, ds_, out_]):
                #     for key, value in dict_.items():
                #         temp[(lab, key)] = value
                # node_mb.append(temp)
                
                for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                    sys_in[v] += in_[v]
                    sys_out[v] += out_[v]
                    sys_ds[v] += ds_[v]
        
            for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                
                #Find the largest value of in_, out_, ds_
                largest = max(sys_in[v], sys_in[v], sys_in[v])
    
                if largest > constants.FLOAT_ACCURACY:
                    #Convert perform comparison in a magnitude to match the largest value
                    magnitude = 10**int(log10(largest))
                    in_10 = sys_in[v] / magnitude
                    out_10 = sys_in[v] / magnitude
                    ds_10 = sys_in[v] / magnitude
                else:
                    in_10 = sys_in[v]
                    ds_10 = sys_in[v]
                    out_10 = sys_in[v]
                
                if (in_10 - ds_10 - out_10) > constants.FLOAT_ACCURACY:
                    print("system mass balance error for " + v + " of " + str(sys_in[v] - sys_ds[v] - sys_out[v]))
            
            #Store results
            for arc in record_arcs:
                arc = self.arcs[arc]
                flows.append({'arc' : arc.name,
                              'flow' : arc.vqip_out['volume'],
                              'time' : date})
                for pol in constants.POLLUTANTS:
                    flows[-1][pol] = arc.vqip_out[pol]
            
            for node in record_tanks:
                node = self.nodes[node]
                tanks.append({'node' : node.name,
                              'storage' : node.tank.storage['volume'],
                              'time' : date})
            if record_all:
                for node in self.nodes.values():
                    for prop_ in dir(node):
                        prop = node.__getattribute__(prop_)
                        if prop.__class__ in [QueueTank, Tank, ResidenceTank]:
                            tanks.append({'node' : node.name,
                                          'time' : date,
                                          'storage' : prop.storage['volume'],
                                          'prop' : prop_})
                            for pol in constants.POLLUTANTS:
                                tanks[-1][pol] = prop.storage[pol]
                                    
                for name, node in self.nodes_type['Land'].items():
                    for surface in node.surfaces:
                        if not isinstance(surface,ImperviousSurface):
                            surfaces.append({'node' : name,
                                              'surface' : surface.surface,
                                              'percolation' : surface.percolation['volume'],
                                              'subsurface_r' : surface.subsurface_flow['volume'],
                                              'surface_r' : surface.infiltration_excess['volume'],
                                              'storage' : surface.storage['volume'],
                                              'evaporation' : surface.evaporation['volume'],
                                              'precipitation' : surface.precipitation['volume'],
                                              'tank_recharge' : surface.tank_recharge,
                                              'capacity' : surface.capacity,
                                              'time' : date,
                                              'et0_coef' : surface.et0_coefficient,
                                              # 'crop_factor' : surface.crop_factor
                                              })
                            for pol in constants.POLLUTANTS:
                                surfaces[-1][pol] = surface.storage[pol]
                        else:
                            surfaces.append({'node' : name,
                                              'surface' : surface.surface,
                                              'storage' : surface.storage['volume'],
                                              'evaporation' : surface.evaporation['volume'],
                                              'precipitation' : surface.precipitation['volume'],
                                              'capacity' : surface.capacity,
                                              'time' : date})
                            for pol in constants.POLLUTANTS:
                                surfaces[-1][pol] = surface.storage[pol]
            
            for node in self.nodes.values():
                node.end_timestep()
            
            for arc in self.arcs.values():
                arc.end_timestep()
        if not verbose:
            enablePrint(stdout)
        return flows, tanks, node_mb, surfaces
    return run