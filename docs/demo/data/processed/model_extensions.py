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