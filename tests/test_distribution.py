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
from wsimod.nodes.waste import Waste
from wsimod.nodes.distribution import UnlimitedDistribution
from wsimod.nodes.nodes import Node
from wsimod.nodes.land import Land
from wsimod.arcs.arcs import Arc
from pandas import to_datetime

    

class MyTestClass(TestCase):
    def setUp(self):
        constants.set_simple_pollutants()
    def assertDictAlmostEqual(self, d1, d2, accuracy = 19):
        for d in [d1, d2]:
            for key, item in d.items():
                d[key] = round(item, accuracy)
        self.assertDictEqual(d1, d2)
    
    def test_unlimited(self):
        distribution = UnlimitedDistribution(name='')
        
        d1 = {'volume' : 1000,
              'phosphate' : 0,
              'temperature' : 0}
        reply = distribution.pull_set_unlimited(d1)
        
        self.assertDictAlmostEqual(d1, reply)
        self.assertDictAlmostEqual(d1, distribution.supplied)
        
        reply = distribution.pull_set_unlimited(d1)
        
        d1['volume'] = 2000
        self.assertDictAlmostEqual(d1, distribution.supplied)
        
if __name__ == "__main__":
    unittest.main()
    