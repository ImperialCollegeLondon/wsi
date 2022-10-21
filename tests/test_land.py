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
from wsimod.arcs.arcs import Arc


    

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
if __name__ == "__main__":
    unittest.main()
    