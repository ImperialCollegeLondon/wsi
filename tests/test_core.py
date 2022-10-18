# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 10:35:51 2022

@author: Barney
"""

import pytest
import unittest
from unittest import TestCase

from wsimod.core import constants
from wsimod.core.core import WSIObj, DecayObj

constants.set_simple_pollutants()

class MyTestClass(TestCase):
    def test_empty(self):
        
        obj = WSIObj()
        self.assertDictEqual({'volume' : 0,
                              'phosphate' : 0,
                              'temperature' : 0}, 
                             obj.empty_vqip())
    
    def test_copy(self):
        
        obj = WSIObj()
        d = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        self.assertDictEqual(d, 
                             obj.copy_vqip(d))
    
    def test_blend(self):
        obj = WSIObj()
        d1 = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        d2 = {'volume' : 5,
            'phosphate' : 0.00005,
            'temperature' : 10}
        blend = {'volume' : 15,
                'phosphate' : 0.00125/15,
                'temperature' : 40/3}
        self.assertDictEqual(blend, obj.blend_vqip(d1, d2))
    
    def test_sum(self):
        obj = WSIObj()
        d1 = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        d2 = {'volume' : 5,
            'phosphate' : 0.00005,
            'temperature' : 10}
        blend = {'volume' : 15,
                'phosphate' : 0.0001 + 0.00005,
                'temperature' : 40/3}
        self.assertDictEqual(blend, obj.sum_vqip(d1, d2))
    
    def test_to_total(self):
        obj = WSIObj()
        d = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        tot = {'volume' : 10,
                'phosphate' : 0.001,
                'temperature' : 15}
        self.assertDictEqual(tot, 
                             obj.concentration_to_total(d))
    
    def test_to_concentration(self):
        obj = WSIObj()
        d = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        tot = {'volume' : 10,
                'phosphate' : 0.00001,
                'temperature' : 15}
        self.assertDictEqual(tot, 
                             obj.total_to_concentration(d))
    
    def test_extract(self):
        obj = WSIObj()
        d1 = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        d2 = {'volume' : 5,
            'phosphate' : 0.00005,
            'temperature' : 10}
        ext = {'volume' : 5,
                'phosphate' : 0.0001 - 0.00005,
                'temperature' : 15}
        self.assertDictEqual(ext, 
                             obj.extract_vqip(d1, d2))
        
if __name__ == "__main__":
    unittest.main()