# -*- coding: utf-8 -*-
"""
Created on Mon Jul  4 16:01:48 2022

@author: bdobson
"""
import wsimod
from wsimod.arcs import arcs
import dill as pickle
from tqdm import tqdm
from wsimod.nodes.land import ImperviousSurface
from wsimod.core import constants, WSIObj
from wsimod.nodes import QueueTank, Tank
from pandas import to_datetime
import sys
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

        self.nodes_type = [x.__name__ for x in all_subclasses(wsimod.Node)] + ['Node']
        self.nodes_type = set(getattr(wsimod,x)(name='').__class__.__name__ for x in self.nodes_type).union(['Foul'])
        self.nodes_type = {x : {} for x in self.nodes_type}
        
    def add_nodes(self, nodelist):
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

            self.nodes_type[type_][name] = getattr(wsimod,node_type)(**dict(data))
            self.nodes[name] = self.nodes_type[type_][name]
            self.nodelist = [x for x in self.nodes.values()]
        
    def add_arcs(self, arclist):
        for arc in arclist:
            name = arc['name']
            type_ = arc['type_']
            del arc['type_']
            arc['in_port'] = self.nodes[arc['in_port']]
            arc['out_port'] = self.nodes[arc['out_port']]
            self.arcs[name] = getattr(arcs,type_)(**dict(arc))

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

    
            
    def run(self, 
            dates = None,
            settings = None,
            record_arcs = None,
            verbose = True,
            record_all = False):
        
        if record_arcs is None:
            record_arcs = self.arcs.keys()

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
            #Create demand (gets pushed to sewers)
            for node in self.nodes_type['Demand'].values():
                node.create_demand()
            
            #Create runoff (impervious gets pushed to sewers, pervious to groundwater)
            for node in self.nodes_type['Land'].values():
                node.run()
                
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
            
            #river
            for node in self.nodes_type['River'].values():
                node.distribute()
            
            
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
                    pass
                    # print("system mass balance error for " + v + " of " + str(sys_in[v] - sys_ds[v] - sys_out[v]))
            
            #Store results
            for arc in record_arcs:
                arc = self.arcs[arc]
                flows.append({'arc' : arc.name,
                              'flow' : arc.vqip_out['volume'],
                              'time' : date})
                for pol in constants.POLLUTANTS:
                    flows[-1][pol] = arc.vqip_out[pol]
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
                                              'crop_factor' : surface.crop_factor})
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