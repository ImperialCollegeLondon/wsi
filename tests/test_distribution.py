# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.distribution import Distribution, UnlimitedDistribution
from wsimod.nodes.storage import Groundwater


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

    def test_unlimited(self):
        distribution = UnlimitedDistribution(name="")

        d1 = {"volume": 1000, "phosphate": 0, "temperature": 0}
        reply = distribution.pull_set_unlimited(d1)

        self.assertDictAlmostEqual(d1, reply)
        self.assertDictAlmostEqual(d1, distribution.supplied)

        reply = distribution.pull_set_unlimited(d1)

        d1["volume"] = 2000
        self.assertDictAlmostEqual(d1, distribution.supplied)

    def test_leakage(self):
        distribution = Distribution(leakage=0.2, name="d1")

        udistribution = UnlimitedDistribution(name="u1")

        GW = Groundwater(name="g1", capacity=10)

        arc1 = Arc(name="a1", in_port=udistribution, out_port=distribution)

        arc2 = Arc(name="a2", in_port=distribution, out_port=GW)

        reply = distribution.pull_check({"volume": 5})
        v1 = 5
        self.assertEqual(v1, reply["volume"])

        reply = distribution.pull_set({"volume": 5})
        v2 = v1 / (1 - 0.2)
        self.assertEqual(v2, arc1.vqip_in["volume"])
        self.assertEqual(v2 * 0.2, arc2.vqip_in["volume"])

    def test_distribution_overrides(self):
        distribution = Distribution(name="", leakage=0.2)
        distribution.apply_overrides({"leakage": 0})
        self.assertEqual(distribution.leakage, 0)


if __name__ == "__main__":
    unittest.main()
