# -*- coding: utf-8 -*-
"""
Created on Mon Jul  4 16:01:48 2022

@author: bdobson
"""
from wsimod import nodes
from wsimod.arcs import arcs as arcs_mod
import dill as pickle
from tqdm import tqdm
from wsimod.nodes.land import ImperviousSurface
from wsimod.core import constants
from wsimod.core.core import WSIObj
from wsimod.nodes.nodes import QueueTank, Tank, Node
from pandas import to_datetime
from wsimod.preprocessing import england_data_formatting as ef
import geopandas as gpd
import pandas as pd
import sys, inspect
import os
class Model(WSIObj):
    def __init__(self):
        super().__init__()
        self.arcs = {}
        # self.arcs_type = {} #not sure that this would be necessary
        self.nodes = {}
        self.nodes_type = {}

        
        def all_subclasses(cls):
            return set(cls.__subclasses__()).union(
                [s for c in cls.__subclasses__() for s in all_subclasses(c)])
        self.nodes_type = [x.__name__ for x in all_subclasses(Node)] + ['Node']
        self.nodes_type = set(getattr(nodes,x)(name='').__class__.__name__ for x in self.nodes_type).union(['Foul'])
        self.nodes_type = {x : {} for x in self.nodes_type}
        
    def add_nodes(self, nodelist):
        def all_subclasses(cls):
            return set(cls.__subclasses__()).union(
                [s for c in cls.__subclasses__() for s in all_subclasses(c)])
        
 
        for data in nodelist:
            name = data['name']
            type_ = data['type_']
            if 'node_type_override' in data.keys():
                node_type = data['node_type_override']
                del data['node_type_override']
            else:
                node_type = type_
            if 'foul' in name:
                #Absolute hack to enable foul sewers to be treated separate from storm
                type_ = 'Foul'
            if 'geometry' in data.keys():
                del data['geometry']
            del data['type_']
            self.nodes_type[type_][name] = getattr(nodes,node_type)(**dict(data))
            self.nodes[name] = self.nodes_type[type_][name]
            self.nodelist = [x for x in self.nodes.values()]
    
    def add_instantiated_nodes(self, nodelist):
        self.nodelist = nodelist
        self.nodes = {x.name : x for x in nodelist}
        for x in nodelist:
            self.nodes_type[x.__class__.__name__][x.name] = x
    
    def add_arcs(self, arclist):
        river_arcs = {}
        for arc in arclist:
            name = arc['name']
            type_ = arc['type_']
            del arc['type_']
            arc['in_port'] = self.nodes[arc['in_port']]
            arc['out_port'] = self.nodes[arc['out_port']]
            self.arcs[name] = getattr(arcs_mod,type_)(**dict(arc))
            
            if arc['in_port'].__class__.__name__ in ['River', 'Node', 'Waste']:
                if arc['out_port'].__class__.__name__ in ['River', 'Node', 'Waste']:
                    river_arcs[name] = self.arcs[name]
                
        upstreamness = {x : 0 for x in self.nodes_type['Waste'].keys()}
        
        upstreamness = self.assign_upstream(river_arcs, upstreamness)
        
        self.river_discharge_order = []
        for node in sorted(upstreamness.items(), key=lambda item: item[1],reverse=True):
            if node[0] in self.nodes_type['River'].keys():
                self.river_discharge_order.append(node[0])
    
    def add_instantiated_arcs(self, arclist):
        self.arclist = arclist
        self.arcs = {x.name : x for x in arclist}
        river_arcs = {}
        for arc in arclist:
            if arc.in_port.__class__.__name__ in ['River', 'Node', 'Waste']:
                if arc.out_port.__class__.__name__ in ['River', 'Node', 'Waste']:
                    river_arcs[arc.name] = arc
        upstreamness = {x : 0 for x in self.nodes_type['Waste'].keys()}
        
        upstreamness = self.assign_upstream(river_arcs, upstreamness)
        
        self.river_discharge_order = []
        for node in sorted(upstreamness.items(), key=lambda item: item[1],reverse=True):
            if node[0] in self.nodes_type['River'].keys():
                self.river_discharge_order.append(node[0])
        
    def assign_upstream(self, arcs, upstreamness):
        upstreamness_ = upstreamness.copy()
        in_nodes = [x.in_port.name for x in arcs.values() if x.out_port.name in upstreamness.keys()]
        ind = max(list(upstreamness_.values())) + 1
        in_nodes = list(set(in_nodes).difference(upstreamness.keys()))
        for node in in_nodes:
            upstreamness[node] = ind
        if upstreamness == upstreamness_:
            return upstreamness
        else:
            upstreamness = self.assign_upstream(arcs,upstreamness)
            return upstreamness
    

    def save(self, fid):
        #Note - dodgy if you are still editing the model! Only use for running the model
        file = open(fid, 'wb')
        pickle.dump(self, file)
        return file.close()
    
    def debug_node_mb(self):
        for node in self.nodelist:
            _ = node.node_mass_balance()
    
    def default_settings(self):
        return {'arcs' : {'flows' : True,
                          'pollutants' : True},
                'tanks' : {'storages' : True,
                            'pollutants' : True},
                'mass_balance' : False}
    
    def change_runoff_coefficient(self, relative_change, nodes = None):
        #Multiplies impervious area by relative change and adjusts grassland accordingly
        if nodes == None:
            nodes = self.nodes_type['Land'].values()
        
        for node in nodes:
            surface_dict = {x.surface : x for x in node.surfaces}
            if 'Impervious' in surface_dict.keys():
                impervious_area = surface_dict['Impervious'].area
                grass_area = surface_dict['Grass'].area
                
                new_impervious_area = impervious_area * relative_change
                new_grass_area = grass_area + (impervious_area - new_impervious_area)
                if new_grass_area < 0:
                    print('not enough grass')
                    break
                surface_dict['Impervious'].area = new_impervious_area
                surface_dict['Impervious'].capacity *= relative_change
                
                surface_dict['Grass'].area = new_grass_area
                surface_dict['Grass'].capacity *= (new_grass_area / grass_area)
                for pol in constants.ADDITIVE_POLLUTANTS + ['volume']:
                    surface_dict['Grass'].storage[pol] *= (new_grass_area / grass_area)
                for pool in surface_dict['Grass'].nutrient_pool.pools:
                    for nutrient in pool.storage.keys():
                        pool.storage[nutrient] *= (new_grass_area / grass_area)

    def make_default(self,
                     model_dir,
                     parameter_dir,
                     dates = [],
                     x = None,
                     verbose = True,
                     node_name = 'node_name',
                     wwtw_id = 'uwwName',
                     catchment_id = 'wfdid',
                     ):
        def load(fid):
            file = open(fid,'rb')
            object_file = pickle.load(file)
            file.close()
            return object_file
        
        #TODO parameters should maybe be copied to the model folder (though now it's being used by water resources...)
        
        
        if verbose:
            print('loading geospatial data')
        subs = gpd.read_file(os.path.join(model_dir, "subcatchments.geojson"))
        population_nodes = gpd.read_file(os.path.join(model_dir, "foul_population_nodes.geojson"))
        river_nodes = gpd.read_file(os.path.join(model_dir, "river_nodes.geojson"))
        wwtw = gpd.read_file(os.path.join(model_dir, "wwtw.geojson")).set_index(wwtw_id).geometry
        ww_discharge = gpd.read_file(os.path.join(model_dir, "ww_discharge.geojson"))
        catchment_outlets = gpd.read_file(os.path.join(model_dir, "catchment_outlets.geojson")).set_index('start_wfdid')
        
        if verbose:
            print('loading surfaces')
        impervious_surfaces = pd.read_parquet(os.path.join(model_dir, "surfaces", "impervious_surfaces.gzip"))
        growing_surfaces = pd.read_parquet(os.path.join(model_dir, "surfaces", "growing_surfaces.gzip"))
        
        if verbose:
            print('loading inputs')
        input_data = load(os.path.join(model_dir, "input_data.pkl"))
        surface_input_data = load(os.path.join(model_dir, "surface_input_data.pkl"))

        if verbose:
            print('loading parameters')
        pollutant_params = pd.read_csv(os.path.join(parameter_dir, "default_pollutant_params.csv"))
        model_parameters_ = pd.read_csv(os.path.join(parameter_dir, "default_model_parameters.csv"))
        # model_ub = model_parameters_.set_index('parameter').ub.to_dict()
        # model_lb = model_parameters_.set_index('parameter').lb.to_dict()
        model_parameters = model_parameters_.set_index('parameter').value.to_dict()
        
        #Assign x
        if x is not None:
            for par, (idx, row) in zip(x, model_parameters_.set_index('parameter').dropna(subset=['calibrate']).iterrows()):
                model_parameters[idx] = par * (row.ub - row.lb) + row.lb        
        
        model_parameters['wilting_point'] = min(model_parameters['wilting_point'], model_parameters['field_capacity'])
        constants.FLOAT_ACCURACY = 1e-8
        constants.POLLUTANTS = ['temperature']
        constants.ADDITIVE_POLLUTANTS = []
        constants.NON_ADDITIVE_POLLUTANTS = ['temperature']
        #TODO these need to be reloaded if simulated with true and then false?    
        if verbose:
            print('Create model')
        nodelist, arclist = ef.format_node_arc(subs,
                                                population_nodes,
                                                river_nodes,
                                                wwtw,
                                                ww_discharge,
                                                catchment_outlets,
                                                
                                                impervious_surfaces,
                                                growing_surfaces,
                                                
                                                input_data,
                                                surface_input_data,
                                                
                                                pollutant_params,
                                                model_parameters,
                                                
                                                node_name,
                                                wwtw_id,
                                                catchment_id,
                                                )
        
        model = Model()
        model.add_nodes(nodelist)
        model.add_arcs(arclist)
        model.dates = dates
        return model
    
    def run(self, 
            dates = None,
            settings = None,
            record_arcs = None,
            record_tanks = None,
            verbose = True,
            record_all = True):
        
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
            
            #Discharge sewers (pushed to other sewers or WWTW)
            for node in self.nodes_type['Sewer'].values():
                node.make_discharge()
                
            #Foul second so that it can discharge any misconnection
            for node in self.nodes_type['Foul'].values():
                node.make_discharge()
           
            #Discharge WWTW
            for node in self.nodes_type['WWTW'].values():
                node.calculate_discharge()
                
            for node in self.nodes_type['WWTW'].values():    
                node.make_discharge()
            
            #Discharge GW
            for node in self.nodes_type['Groundwater'].values():
                node.distribute()
            
            #Abstract
            for node in self.nodes_type['Reservoir'].values():
                node.make_abstractions()
            
            #Catchment routing
            for node in self.nodes_type['Catchment'].values():
                node.route()
            
            #river
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
                if (sys_in[v] - sys_ds[v] - sys_out[v]) > constants.FLOAT_ACCURACY:
                    # pass
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
                for node in self.nodes_type['Groundwater'].values():
                    tanks.append({'node' : node.name,
                                  'storage' : node.tank.storage['volume'],
                                  'time' : date})
    
                for node in self.nodes.values():
                    for prop in dir(node):
                        prop = node.__getattribute__(prop)
                        if (prop.__class__ == Tank) | (prop.__class__ == QueueTank):
                            tanks.append({'node' : node.name,
                                          'time' : date,
                                          'storage' : prop.storage['volume']})
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
    
    def reinit(self):
        for node in self.nodes.values():
            node.end_timestep()
        
        for arc in self.arcs.values():
            arc.end_timestep()