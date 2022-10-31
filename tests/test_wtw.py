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
from wsimod.nodes.wtw import WTW, WWTW, FWTW
from wsimod.nodes.nodes import Node
from wsimod.nodes.sewer import Sewer
from wsimod.arcs.arcs import Arc
from pandas import to_datetime

    
constants.set_simple_pollutants()

class MyTestClass(TestCase):
    
    def assertDictAlmostEqual(self, d1, d2, accuracy = 19):
        for d in [d1, d2]:
            for key, item in d.items():
                d[key] = round(item, accuracy)
        self.assertDictEqual(d1, d2)
    
    def test_excess(self):
        

        wtw = WTW(name='',
                  treatment_throughput_capacity = 10,
                  )
        wtw.current_input['volume'] = 8
        self.assertEqual(2, wtw.get_excess_throughput())
        
    def test_treat(self):
        pass
if __name__ == "__main__":
    unittest.main()
    