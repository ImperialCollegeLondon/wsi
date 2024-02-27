# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.core import constants
from wsimod.nodes.wtw import WTW


class MyTestClass(TestCase):
    def setUp(self):
        """"""
        constants.set_simple_pollutants()

    def assertDictAlmostEqual(self, d1, d2, accuracy=19):
        """

        Args:
            d1:
            d2:
            accuracy:
        """
        for d in [d1, d2]:
            for key, item in d.items():
                d[key] = round(item, accuracy)
        self.assertDictEqual(d1, d2)

    def test_excess(self):
        wtw = WTW(
            name="",
            treatment_throughput_capacity=10,
        )
        wtw.current_input["volume"] = 8
        self.assertEqual(2, wtw.get_excess_throughput())

    def test_treat(self):
        constants.set_simple_pollutants()
        wtw = WTW(
            name="",
            treatment_throughput_capacity=10,
        )
        wtw.current_input= {'volume' : 8,
                            'phosphate' : 5,
                            'temperature' : constants.DECAY_REFERENCE_TEMPERATURE}
        wtw.treat_current_input()
        self.assertEqual(8 * wtw.process_parameters['volume']['constant'], 
                         wtw.treated["volume"])
        self.assertEqual(5 * wtw.process_parameters['phosphate']['constant'], 
                         wtw.treated["phosphate"])
        self.assertEqual(8 * wtw.liquor_multiplier['volume'],
                         wtw.liquor['volume'])
        self.assertEqual(5 * wtw.liquor_multiplier['phosphate'],
                         wtw.liquor['phosphate'])
        self.assertEqual(5 - 5 * wtw.process_parameters['phosphate']['constant']\
                         - 5 * wtw.liquor_multiplier['phosphate'],
                         wtw.solids['phosphate'])

    def test_override(self):
        wtw = WTW(
            name="",
            treatment_throughput_capacity=10,
            percent_solids = 0.1,
            liquor_multiplier = {'volume' : 0.05, 'phosphate' : 0.5},
            process_parameters = {'phosphate' : {'constant' : 0.1,
                                                 'exponent' : 1.001}}
        )

        wtw.apply_overrides({'percent_solids' : 0.05})
        self.assertAlmostEqual(wtw.process_parameters['volume']['constant'],
                        0.9)
        self.assertEqual(wtw.percent_solids, 0.05)
        
        wtw.apply_overrides({'percent_solids' : 0.1,
                             'liquor_multiplier' : {'volume' : 0.1}})
        
        self.assertEqual(wtw.process_parameters['volume']['constant'],
                        0.8)
        self.assertEqual(wtw.liquor_multiplier['volume'], 0.1)
        self.assertEqual(wtw.liquor_multiplier['phosphate'], 0.5)
        
        wtw.apply_overrides({'percent_solids' : 0.1,
                             'liquor_multiplier' : {'volume' : 0.1,
                                                    'phosphate' : 0.01}})
        self.assertEqual(wtw.liquor_multiplier['phosphate'], 0.01)

        wtw.apply_overrides({'process_parameters' : {'phosphate' : {'constant' : 0.01}}})
        self.assertEqual(wtw.process_parameters['phosphate']['constant'], 0.01)
        self.assertEqual(wtw.process_parameters['phosphate']['exponent'], 1.001)

        overrides = {'process_parameters' : {'phosphate' : {'exponent' : 1.01}},
                            'liquor_multiplier' : {'phosphate' : 0.1},
                            'percent_solids' : 0.1,
                            'treatment_throughput_capacity' : 20,
                            'name' : 'new_name'}
        wtw.apply_overrides(overrides)
        self.assertSetEqual(set(overrides.keys()), set(['name']))
        self.assertEqual(wtw.treatment_throughput_capacity, 20)
if __name__ == "__main__":
    unittest.main()
