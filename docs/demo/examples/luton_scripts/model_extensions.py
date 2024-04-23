# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 10:50:55 2023

@author: bdobson
"""
from wsimod.core import constants
# import sys
# import os
# from tqdm import tqdm
# from math import log10
# from wsimod.nodes.land import ImperviousSurface
# from wsimod.nodes.nodes import QueueTank, Tank, ResidenceTank

def extensions(model):
    
    # decorate land->gw
    model.nodes['1823-land'].run = wrapper_land_gw(model.nodes['1823-land'])
    # model.nodes['1823-land'].surfaces[-1].push_to_sewers = wrapper_impervioussurface_sewer(model.nodes['1823-land'].surfaces[-1])
    
    model.nodes['1823-land'].surfaces[-1].atmospheric_deposition = adjust_atmospheric_deposition(model.nodes['1823-land'].surfaces[-1])
    model.nodes['1823-land'].surfaces[-1].precipitation_deposition = adjust_precipitation_deposition(model.nodes['1823-land'].surfaces[-1])
    model.nodes['1823-land'].surfaces[-1].inflows[0] = model.nodes['1823-land'].surfaces[-1].atmospheric_deposition
    model.nodes['1823-land'].surfaces[-1].inflows[1] = model.nodes['1823-land'].surfaces[-1].precipitation_deposition
    
    # Change model.run because new function has been introduced by the new node
    model.river_discharge_order = ['1823-river']
    
    # decorate fix head
    for node in ['6aead97c-0040-4e31-889d-01f628faf990',
                'fb3a7adf-ae40-4a9f-ad3f-55b3e4d5c6b7',
                '7e0cc125-fe7a-445b-af6b-bf55ac4065f9',
                'e07ddbc6-7158-4a47-b987-eb2b934dd257',
                'e4b324b5-60f9-48c2-9d64-d89d22a5305e',
                '88c7e69b-e4b3-4483-a438-0d6f9046cdee',
                'a057761f-e18e-4cad-84d4-9458edc182ef',
                '2b5397b7-a129-40a6-873d-cb2a0dd7d5b8'
                ]:
        model.nodes[node].end_timestep = end_timestep(model.nodes[node])
    
    # wq parameters for wwtw
    for wwtw, new_constants, variable, date in zip(['luton_stw-wwtw', 'luton_stw-wwtw', 'luton_stw-wwtw'],
                                                     [2.6, 1.5, 0.3],
                                                     ['phosphate', 'phosphate', 'phosphate'],
                                                     ['2000-01-01', '2001-01-01', '2005-01-01']):
        node = model.nodes[wwtw]
        node.end_timestep = wrapper_wwtw(node.end_timestep, node, variable, new_constants, date)

# set fixed head for 'ex-head' node
def end_timestep(self):
    self.mass_balance_in = [lambda: self.empty_vqip()]
    self.mass_balance_out = [lambda: self.empty_vqip()]
    self.mass_balance_ds = [lambda: self.empty_vqip()]
    def inner_function():
        """Update tank states & self.h
        """
        self.h = self.get_data_input('head')
        self.tank.storage['volume'] = (self.h - self.datum) * self.area * self.s
        self.tank.end_timestep()
        self.h = self.tank.get_head()
    return inner_function


def wrapper_land_gw(self):
    def run(#self
            ):
       """Call the run function in all surfaces, update surface/subsurface/
       percolation tanks, discharge to rivers/groundwater.
       """
       # Run all surfaces
       for surface in self.surfaces:
           surface.run()

       # Apply residence time to percolation
       percolation = self.percolation.pull_outflow()

       # Distribute percolation
       reply = self.push_distributed(percolation, of_type=["Groundwater_h"])

       if reply["volume"] > constants.FLOAT_ACCURACY:
           # Update percolation 'tank'
           _ = self.percolation.push_storage(reply, force=True)

       # Apply residence time to subsurface/surface runoff
       surface_runoff = self.surface_runoff.pull_outflow()
       subsurface_runoff = self.subsurface_runoff.pull_outflow()

       # Total runoff
       total_runoff = self.sum_vqip(surface_runoff, subsurface_runoff)
       if total_runoff["volume"] > 0:
           # Send to rivers (or nodes, which are assumed to be junctions)
           reply = self.push_distributed(total_runoff, of_type=["River_h", "Node"])

           # Redistribute total_runoff not sent
           if reply["volume"] > 0:
               reply_surface = self.v_change_vqip(
                   reply,
                   reply["volume"] * surface_runoff["volume"] / total_runoff["volume"],
               )
               reply_subsurface = self.v_change_vqip(
                   reply,
                   reply["volume"]
                   * subsurface_runoff["volume"]
                   / total_runoff["volume"],
               )

               # Update surface/subsurface runoff 'tanks'
               if reply_surface["volume"] > 0:
                   self.surface_runoff.push_storage(reply_surface, force=True)
               if reply_subsurface["volume"] > 0:
                   self.subsurface_runoff.push_storage(reply_subsurface, force=True)
    return run

def adjust_atmospheric_deposition(surface, ratio = 0.05):
    def atmospheric_deposition():
        """Inflow function to cause dry atmospheric deposition to occur, updating the 
        surface tank

        Returns:
            (tuple): A tuple containing a VQIP amount for model inputs and outputs 
                for mass balance checking. 
        """
        #TODO double check units in preprocessing - is weight of N or weight of NHX/noy?

        #Read data and scale
        nhx = surface.get_data_input_surface('nhx-dry') * surface.area * ratio
        noy = surface.get_data_input_surface('noy-dry') * surface.area * ratio
        srp = surface.get_data_input_surface('srp-dry') * surface.area * ratio

        #Assign pollutants
        vqip = surface.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = noy
        vqip['phosphate'] = srp

        #Update tank
        in_ = surface.dry_deposition_to_tank(vqip)

        #Return mass balance
        return (in_, surface.empty_vqip())
    return atmospheric_deposition

def adjust_precipitation_deposition(surface, ratio = 0.05):
    def precipitation_deposition():
        """Inflow function to cause wet precipitation deposition to occur, updating 
        the surface tank

        Returns:
            (tuple): A tuple containing a VQIP amount for model inputs and outputs 
                for mass balance checking. 
        """
        #TODO double check units - is weight of N or weight of NHX/noy?

        #Read data and scale
        nhx = surface.get_data_input_surface('nhx-wet') * surface.area * ratio
        noy = surface.get_data_input_surface('noy-wet') * surface.area * ratio
        srp = surface.get_data_input_surface('srp-wet') * surface.area * ratio

        #Assign pollutants
        vqip = surface.empty_vqip()
        vqip['ammonia'] = nhx
        vqip['nitrate'] = noy
        vqip['phosphate'] = srp

        #Update tank
        in_ = surface.wet_deposition_to_tank(vqip)

        #Return mass balance
        return (in_, surface.empty_vqip())
    return precipitation_deposition

def wrapper_wwtw(f, node,variable, value, date):
    def new_end_timestep():
        f()
        if str(node.t) == date:
            node.process_parameters[variable]['constant'] = value
    return new_end_timestep
