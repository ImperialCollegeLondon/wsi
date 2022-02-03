# -*- coding: utf-8 -*-
"""
Created on Mon Nov 22 13:43:49 2021

@author: bdobson
"""
from wsimod.core import WSIObj, constants
from wsimod.nodes.nodes import Tank, QueueTank

from tqdm import tqdm
import pandas as pd

class Model(WSIObj):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def reinit(self):
        for arc in self.arclist:
            arc.reinit()
            
        for node in self.nodelist:
            node.reinit()
        
    def run(self):
        
        #Initiailse results lists   
        flows = []
        tanks = []
        node_mb = []

        #Loop over timesteps
        for date in tqdm(self.dates):
            
            #Tell every node what timestep it is
            for node in self.nodelist:
                node.t = date

            """Orchestration
            """
            #Treat water
            for node in self.nodes['fwtw']:
                node.treat_water()
            
            #Create demand (gets pushed to sewers)
            for node in self.nodes['demand']:
                node.create_demand()
 
            #Create runoff (impervious gets pushed to sewers, pervious to groundwater)
            for node in self.nodes['land']:
                node.create_runoff()
 
            #Discharge sewers (pushed to other sewers or WWTW)   
            for node in self.nodes['sewer']:
                node.make_discharge()
            
            #Discharge GW
            for node in self.nodes['gw']:
                node.distribute()
 
            #Run WWTW model
            for node in self.nodes['wwtw']:
                node.calculate_discharge()
 
            #Make abstractions
            for node in self.nodes['reservoir']:
                node.make_abstractions()
 
            #Discharge WW
            for node in self.nodes['wwtw']:
                node.make_discharge()
 
            #Route catchments
            for node in self.nodes['catchment']:
                node.route()

            
            """Mass balance checks
            """
            sys_in = self.empty_vqip()
            sys_out = self.empty_vqip()
            sys_ds = self.empty_vqip()
            for node in self.nodelist:
                in_, ds_, out_ = node.node_mass_balance()
                
                temp = {'name' : node.name,
                        'time' : date}
                
                for lab, dict_ in zip(['in','ds','out'], [in_, ds_, out_]):
                    for key, value in dict_.items():
                        temp[(lab, key)] = value
                node_mb.append(temp)
                for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                    sys_in[v] += in_[v]
                    sys_out[v] += out_[v]
                    sys_ds[v] += ds_[v]
            
            for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                if (sys_in[v] - sys_ds[v] - sys_out[v]) > constants.FLOAT_ACCURACY:
                    print("system mass balance error for " + v + " of " + str(sys_in[v] - sys_ds[v] - sys_out[v]))
                    
            """Store results
            """
            for arc in self.arclist:
                flows.append({'arc' : arc.name,
                              'flow' : arc.flow_out,
                              'time' : date})
                for pol in constants.POLLUTANTS:
                    flows[-1][pol] = arc.vqip_out[pol]
                    
            for node in self.nodelist:
                for prop in dir(node):
                    prop = node.__getattribute__(prop)
                    if (prop.__class__ == Tank) | (prop.__class__ == QueueTank):
                        tanks.append({'node' : node.name,
                                      'time' : date,
                                      'storage' : prop.storage['volume']})
                        
            """End timestep
            """
            for node in self.nodelist:
                node.end_timestep()
            
            for arc in self.arclist:
                arc.end_timestep()
            
        #%%
        """Basic validation plots
        """    
        flows = pd.DataFrame(flows, index = None)
        flows.time = pd.to_datetime(flows.time)

        node_mb = pd.DataFrame(node_mb)
        node_mb.time = pd.to_datetime(node_mb.time)

        tanks = pd.DataFrame(tanks)
        tanks.time = pd.to_datetime(tanks.time)
        return flows, node_mb, tanks