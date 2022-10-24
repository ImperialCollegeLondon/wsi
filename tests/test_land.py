# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 10:35:51 2022

@author: Barney
"""

import pytest
# import pytest
import unittest
from unittest import TestCase

from wsimod.core import constants
from wsimod.nodes.nodes import Node, Tank, ResidenceTank, DecayTank, QueueTank, DecayQueueTank
from wsimod.nodes.waste import Waste
from wsimod.nodes.land import Surface, PerviousSurface, ImperviousSurface, GrowingSurface, GardenSurface, Land
from wsimod.nodes.sewer import Sewer
from wsimod.arcs.arcs import Arc
from math import exp

    

class MyTestClass(TestCase):
    
    def assertDictAlmostEqual(self, d1, d2, accuracy = 19):
        for d in [d1, d2]:
            for key, item in d.items():
                d[key] = round(item, accuracy)
        self.assertDictEqual(d1, d2)
    
    def test_surface_read(self):
        constants.set_simple_pollutants()
        node = Node(name = '',
                    data_input_dict = {('temperature', 1) : 15})
        node.t = 1
        node.monthyear = 1

        surface = Surface(data_input_dict = {('phosphate', 1) : 0.1}, 
                            parent = node)
        
        self.assertEqual(surface.get_data_input('temperature'), 15)
        self.assertEqual(surface.get_data_input_surface('phosphate'), 0.1)
    
    def test_deposition(self):
        constants.set_simple_pollutants()
        d1 = {'volume' : 0.1,
              'phosphate' : 2,
              'temperature' : 5}
        
        surface = Surface(parent = None,
                          area = 5,
                          depth = 0.1)
        surface.dry_deposition_to_tank(d1)
        self.assertDictAlmostEqual(d1, surface.storage)
        
        d2 = {'volume' : 0.2,
              'phosphate' : 4,
              'temperature' : 5}
        surface.wet_deposition_to_tank(d1)
        self.assertDictAlmostEqual(d2, surface.storage)
    
    def test_atmospheric_dep(self):
        constants.set_simple_pollutants()
        node = Node(name = '')
        node.monthyear = 1
        
        inputs = {('nhx-dry', 1) : 0.1,
                  ('noy-dry', 1) : 0.4,
                  ('srp-dry', 1) : 0.2}

        surface = Surface(data_input_dict = inputs, 
                            parent = node,
                            area = 10)
        
        d1 = {'ammonia' : 1,
             'nitrate' : 4,
             'phosphate' : 2,
             'volume' : 0,
             'temperature' : 0}
        d2 = {'volume' : 0,
              'temperature' : 0,
              'phosphate' : 0}
        (r1, r2) = surface.atmospheric_deposition()
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
        
    def test_precip_dep(self):
        constants.set_simple_pollutants()
        node = Node(name = '')
        node.monthyear = 1
        
        inputs = {('nhx-wet', 1) : 0.1,
                  ('noy-wet', 1) : 0.4,
                  ('srp-wet', 1) : 0.2}
    
        surface = Surface(data_input_dict = inputs, 
                            parent = node,
                            area = 10)
        
        d1 = {'ammonia' : 1,
             'nitrate' : 4,
             'phosphate' : 2,
             'volume' : 0,
             'temperature' : 0}
        d2 = {'volume' : 0,
              'temperature' : 0,
              'phosphate' : 0}
        (r1, r2) = surface.precipitation_deposition()
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
    
    def test_run_surface(self):
        constants.set_default_pollutants()
        
        node = Land(name = '',
                    data_input_dict = {('temperature', 1) : 15})
        node.t = 1
        node.monthyear = 1
        
        inputs = {('nhx-wet', 1) : 0.1,
                  ('noy-wet', 1) : 0.4,
                  ('srp-wet', 1) : 0.2,
                  ('nhx-dry', 1) : 0.1,
                  ('noy-dry', 1) : 0.4,
                  ('srp-dry', 1) : 0.2}
        
        decays = {'nitrite' : {'constant' : 0.005,
                               'exponent' : 1.005},
                  'ammonia' : {'constant' : 0.05,
                               'exponent' : 1.05}}    
    
        surface = Surface(data_input_dict = inputs, 
                            parent = node,
                            area = 10,
                            decays = decays)
        
        surface.run()
        d1 = surface.empty_vqip()
        
        self.assertDictAlmostEqual(d1, node.running_outflow_mb)
        
        d1['phosphate'] = 4
        d1['ammonia'] = 2
        d1['nitrate'] = 8
        
        self.assertDictAlmostEqual(d1, node.running_inflow_mb)
        self.assertDictAlmostEqual(d1, surface.storage)
        
        surface.end_timestep()
        d1['ammonia'] = d1['ammonia'] * (1 - 0.05 * 1.05 ** (15-20))
        self.assertDictAlmostEqual(d1, surface.storage)
        
        surface.run()
        d1['phosphate'] = 8
        d1['ammonia'] = 2 + 2 * (1 - 0.05 * 1.05 ** (15-20))
        d1['nitrite'] = 2 * 0.05 * 1.05 ** (15-20)
        d1['nitrate'] = 16
        self.assertDictAlmostEqual(d1, surface.storage)
        
        surface.end_timestep()
        surface.run()
        d1['phosphate'] = 12
        d1['nitrate'] = 24 + d1['nitrite'] * (0.005 * 1.005 ** (15-20))
        d1['nitrite'] = d1['nitrite'] * (1 - 0.005 * 1.005 ** (15-20)) + d1['ammonia'] * (0.05 * 1.05 ** (15-20))
        d1['ammonia'] = 2 + 2 * (1 - 0.05 * 1.05 ** (15-20)) + 2 * (1 - 0.05 * 1.05 ** (15-20)) ** 2
        
        
        self.assertDictAlmostEqual(d1, surface.storage,16)
    
    def test_urban_dep(self):
        constants.set_simple_pollutants()
        d1 = {'phosphate' : 2,
                'volume' : 0,
                'temperature' : 0}

        surface = ImperviousSurface(pollutant_load = d1,
                                    area = 1)
       
        (in_, out_) = surface.urban_deposition()
        
        
        d2 = {'volume' : 0,
              'temperature' : 0,
              'phosphate' : 0}
        self.assertDictAlmostEqual(d1, in_)
        self.assertDictAlmostEqual(surface.storage, in_)
        self.assertDictAlmostEqual(d2, out_)
        
    def test_urban_precip(self):
        constants.set_simple_pollutants()
        inputs = {('precipitation', 1) : 0.1,
                  ('et0',1) : 0.01,
                  ('temperature',1) : 10,
                  ('precipitation' , 2) : 0,
                  ('et0',2) : 0.02,
                  ('temperature',2) : 15}
        
        node = Node(name = '',
                    data_input_dict = inputs)
          
        surface = ImperviousSurface(parent = node,
                                    area = 1.5,
                                    et0_to_e = 0.9,
                                    pore_depth = 0.015)
        
        
        node.t = 1

        d1 = {'volume' : 0.1*1.5,
              'temperature' : 0,
              'phosphate' : 0}
        d2 = {'phosphate' : 0,
             'volume' : 0.01*1.5*0.9,
             'temperature' : 0}
        d3 = {'phosphate' : 0,
              'temperature' : 10,
              'volume' : (0.1 - 0.01*0.9) * 1.5}
        (r1, r2) = surface.precipitation_evaporation()
        self.assertDictAlmostEqual(d1, r1,17)
        self.assertDictAlmostEqual(d2, r2,17)
        self.assertDictAlmostEqual(d3, surface.storage,17)
        
        node.t = 2
        d3 = {'volume' : 0,
              'temperature' : 0,
              'phosphate' : 0}
        d4 = {'phosphate' : 0,
             'volume' : 0.02*1.5*0.9,
             'temperature' : 0}
        d5 = {'phosphate' : 0,
              'temperature' : 10,
              'volume' : (0.1 - (0.01 + 0.02)*0.9) * 1.5}
        (r1, r2) = surface.precipitation_evaporation()
        self.assertDictAlmostEqual(d3, r1,17)
        self.assertDictAlmostEqual(d4, r2,17)
        self.assertDictAlmostEqual(d5, surface.storage,17)
    
    def test_urban_push(self):
        constants.set_simple_pollutants()
        inputs = {('precipitation', 1) : 0.1,
                  ('et0',1) : 0.01,
                  ('temperature',1) : 10,
                  }
        
        node = Node(name = '',
                    data_input_dict = inputs)
        node.t = 1
        sewer = Sewer(name = '',
                      capacity = 2)
        _ = Arc(in_port = node, out_port = sewer, name = '')
        surface = ImperviousSurface(parent = node,
                                    area = 1.5,
                                    et0_to_e = 0.9,
                                    pore_depth = 0.015)
        _ = surface.precipitation_evaporation()
        _ = surface.push_to_sewers()
        
        d1 = {'volume' : 0.015 * 1.5,
              'phosphate' : 0,
              'temperature' : 10}
        d2 = {'volume' : (0.1 - 0.01*0.9 - 0.015) * 1.5,
              'phosphate' : 0,
              'temperature' : 10}
        
        self.assertDictAlmostEqual(d1, surface.storage,16)
        self.assertDictAlmostEqual(d2, sewer.sewer_tank.storage,16)
    
    def test_perv_cmd(self):
        surface = PerviousSurface(parent = '',
                                  depth = 0.5,
                                  area = 1.5,
                                  initial_storage = 0.5*1.5*0.25
                                  )
        self.assertAlmostEqual((1 - 0.25)*0.5, surface.get_cmd())
    
    def test_perv_cmd(self):
        surface = PerviousSurface(parent = '',
                                  depth = 0.5,
                                  area = 1.5,
                                  initial_storage = 0.5*1.5*0.25
                                  )
        self.assertAlmostEqual(0.25*0.5, surface.get_smc())
        
    def test_ihacres1(self):
        #Above field capacity
        constants.set_simple_pollutants()
        inputs = {('precipitation', 1) : 0.1,
                  ('et0',1) : 0.01,
                  ('temperature',1) : 10,
                 }
        
        node = Node(name = '',
                    data_input_dict = inputs)
        
        surface = PerviousSurface(parent = node,
                                    depth = 0.5,
                                    area = 1.5,
                                    field_capacity = 0.35,
                                    wilting_point = 0.12,
                                    infiltration_capacity = 0.4,
                                    surface_coefficient = 0.04,
                                    percolation_coefficient = 0.6,
                                    et0_coefficient = 0.4,
                                    ihacres_p = 12,
                                    initial_storage = 0.4 * 0.5 * 1.5
                                    )
        
        node.t = 1
        
        (r1, r2) = surface.ihacres()
        
        d1 = {'volume' : 0.1 * 1.5,
              'phosphate' : 0,
              'temperature' : 0}
        
        d2 = {'volume' : 0.01 * 1.5 * 0.4,
              'phosphate' : 0,
              'temperature' : 0}
        
        outflow_ = 0.1 * (1 - ((0.5 - 0.4*0.5) / (0.5 - 0.35*0.5))**12)
        
        total_water_passing_through_soil = (0.1 - 0.01*0.4 - outflow_ * 0.04)*1.5
        
        temperature = (0 * 0.4 * 0.5 * 1.5) + (total_water_passing_through_soil * 10) / (total_water_passing_through_soil + 0.4 * 0.5 * 1.5)
        
        d3 = {'volume' : outflow_ * (1 - 0.04) * 0.6 * 1.5,
              'phosphate' : 0,
              'temperature' : temperature}
        
        d4 = {'volume' : outflow_ * (1 - 0.04) * (1 - 0.6) * 1.5,
              'phosphate' : 0,
              'temperature' : temperature}
        
        d5 = {'volume' : (0.1 - outflow_ - 0.01*0.4 + 0.4*0.5) * 1.5,
              'phosphate' : 0,
              'temperature' : temperature}
        
        d6 = {'volume' : outflow_ * 0.04 * 1.5,
              'phosphate' : 0,
              'temperature' : 10}
        
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
        self.assertDictAlmostEqual(d3, surface.percolation, 15)
        self.assertDictAlmostEqual(d4, surface.subsurface_flow)
        self.assertDictAlmostEqual(d5, surface.storage,15)
        self.assertDictAlmostEqual(d6, surface.infiltration_excess)
    
    def test_ihacres2(self):
        #Below wilting point
        constants.set_simple_pollutants()
        inputs = {('precipitation', 1) : 0,
                  ('et0',1) : 0.01,
                  ('temperature',1) : 10,
                 }
        
        node = Node(name = '',
                    data_input_dict = inputs)
        
        surface = PerviousSurface(parent = node,
                                    depth = 0.5,
                                    area = 1.5,
                                    field_capacity = 0.35,
                                    wilting_point = 0.12,
                                    infiltration_capacity = 0.4,
                                    surface_coefficient = 0.04,
                                    percolation_coefficient = 0.6,
                                    et0_coefficient = 0.4,
                                    ihacres_p = 12,
                                    initial_storage = 0.11 * 0.5 * 1.5
                                    )
        
        node.t = 1
        
        (r1, r2) = surface.ihacres()
        
        evaporation_ = 0.01 * 0.4 * exp(2 * (1 - (0.5-0.11*0.5) / (0.5 - 0.12*0.5))) * 1.5
        d1 = {'volume' : 0,
              'phosphate' : 0,
              'temperature' : 0}
        
        d2 = {'volume' : evaporation_,
              'phosphate' : 0,
              'temperature' : 0}
        
        d3 = {'volume' : 0,
              'phosphate' : 0,
              'temperature' : 0}
        
        d4 = {'volume' : 0.11*0.5*1.5 - evaporation_,
              'phosphate' : 0,
              'temperature' : 0}
        
        d5 = {'volume' : 0,
              'phosphate' : 0,
              'temperature' : 10}
     
        
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
        self.assertDictAlmostEqual(d3, surface.percolation, 15)
        self.assertDictAlmostEqual(d3, surface.subsurface_flow)
        self.assertDictAlmostEqual(d4, surface.storage,15)
        self.assertDictAlmostEqual(d5, surface.infiltration_excess)
    
    def test_perv_route(self):
        constants.set_simple_pollutants()
        land = Land(name = '',
                    )
        
        d1 = {'volume' : 2.5,
              'temperature' : 10,
              'phosphate' : 0.3}
        
        d2 = {'volume' : 2,
              'temperature' : 12,
              'phosphate' : 0.1}
        
        d3 = {'volume' : 5,
              'temperature' : 11,
              'phosphate' : 0.2}
        
        d4 = {'volume' : 0,
              'temperature' : 0,
              'phosphate' : 0}
        surface = PerviousSurface(parent = land,
                                    depth = 0.5,
                                    area = 1.5)
        surface.infiltration_excess = d1
        surface.subsurface_flow = d2
        surface.percolation = d3
        
        (r1, r2) = surface.route()
        self.assertDictAlmostEqual(d4, r1)
        self.assertDictAlmostEqual(d4, r2)
        self.assertDictAlmostEqual(d1, land.surface_runoff.storage)
        self.assertDictAlmostEqual(d2, land.subsurface_runoff.storage)
        self.assertDictAlmostEqual(d3, land.percolation.storage)
    
    def test_soil_temp(self):
        #Above field capacity
        constants.set_simple_pollutants()
        inputs = {('temperature',1) : 10,
                 }
        
        node = Node(name = '',
                    data_input_dict = inputs)    
        node.t = 1
        surface = PerviousSurface(parent = node,
                                    depth = 0.5,
                                    area = 1.5,
                                    initial_storage = {'volume' : 7,
                                                       'temperature' : 3,
                                                       'phosphate' : 0.2})
        
        surface.soil_temp_w_prev = 0.2
        surface.soil_temp_w_air = 0.3
        surface.soil_temp_w_deep = 0.4
        surface.soil_temp_deep = 5
        
        d1 = {'volume' : 0,
              'temperature' : 0,
              'phosphate' : 0}
        
        d2 = {'volume' : 7,
              'temperature' : (5 * 0.4 + 0.2 * 3 + 0.3 * 10) / (0.2 + 0.3 + 0.4),
              'phosphate' : 0.2}
        
        (r1, r2) = surface.calculate_soil_temperature()
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d1, r2)
        self.assertDictAlmostEqual(d2, surface.storage, 14)
    
    def create_growing_surface(self):
        constants.set_default_pollutants()
        node = Node(name = '')
        initial_vol = node.empty_vqip()
        initial_vol['phosphate']= 11
        initial_vol['nitrate']= 2.5
        initial_vol['nitrite']= 1.5
        initial_vol['ammonia']= 0.1
        initial_vol['org-nitrogen']= 0.2
        initial_vol['org-phosphorus']= 3
        initial_vol['volume']= 0.32
        
        initial_soil = {'phosphate' : 1.2,
                        'ammonia' : 0.2,
                        'nitrate' : 0.3,
                        'nitrite' : 0.4,
                        'org-nitrogen' : 2,
                        'org-phosphorus' : 4}
        
        surface = GrowingSurface(rooting_depth = 0.5,
                                 area = 1.5,
                                 initial_storage = initial_vol,
                                 initial_soil_storage = initial_soil)
        return surface, initial_vol, initial_soil
    
    def test_grow_init(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        
        d1 = {'N' : ivol['nitrate'] + ivol['nitrite'] + ivol['ammonia'],
              'P' : ivol['phosphate']}
        self.assertDictAlmostEqual(surface.nutrient_pool.dissolved_inorganic_pool.storage, 
                                   d1)
        
        d2 = {'N' : ivol['org-nitrogen'],
              'P' : ivol['org-phosphorus']}
        self.assertDictAlmostEqual(surface.nutrient_pool.dissolved_organic_pool.storage, 
                                   d2)
        
        d3 = {'N' : isoil['nitrate'] + isoil['nitrite'] + isoil['ammonia'],
              'P' : isoil['phosphate']}
        self.assertDictAlmostEqual(surface.nutrient_pool.adsorbed_inorganic_pool.storage, 
                                   d3,
                                   15)
        
        d4 = {'N' : isoil['org-nitrogen'],
              'P' : isoil['org-phosphorus']}
        self.assertDictAlmostEqual(surface.nutrient_pool.fast_pool.storage, 
                                   d4)
    
    def test_grow_pull(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        
        d1 = surface.empty_vqip()
        for key, amount in ivol.items():
            d1[key] = amount * 0.25 / 0.32
            
        reply = surface.pull_storage({'volume' : 0.25})
        self.assertDictAlmostEqual(d1, reply, 15)
if __name__ == "__main__":
    unittest.main()
    