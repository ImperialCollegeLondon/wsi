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
        pass


if __name__ == "__main__":
    unittest.main()
