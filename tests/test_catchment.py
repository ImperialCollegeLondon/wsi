# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.catchment import Catchment
from wsimod.nodes.waste import Waste


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

    def test_get_flow(self):
        catchment = Catchment(
            name="",
            data_input_dict={
                ("flow", 1): 10,
                ("phosphate", 1): 0.4,
                ("temperature", 1): 10,
            },
        )
        catchment.t = 1
        vq = catchment.get_flow()
        d1 = {"volume": 10, "phosphate": 0.4 * 10, "temperature": 10}
        self.assertDictAlmostEqual(d1, vq)

    def test_get_avail(self):
        catchment = Catchment(
            name="",
            data_input_dict={
                ("flow", 1): 10,
                ("phosphate", 1): 0.4,
                ("temperature", 1): 10,
            },
        )
        waste = Waste(name="")
        arc1 = Arc(in_port=catchment, out_port=waste, name="")
        arc1.vqip_in = {"volume": 2}
        catchment.t = 1
        vq = catchment.get_avail()
        d1 = {"volume": 10 - 2, "phosphate": 0.4 * 8, "temperature": 10}
        self.assertDictAlmostEqual(d1, vq)

    def test_route(self):
        catchment = Catchment(
            name="",
            data_input_dict={
                ("flow", 1): 10,
                ("phosphate", 1): 0.4,
                ("temperature", 1): 10,
            },
        )
        catchment.t = 1

        waste = Waste(name="")
        arc1 = Arc(in_port=catchment, out_port=waste, name="")

        catchment.get_flow()
        d1 = {"volume": 10, "phosphate": 0.4 * 10, "temperature": 10}

        catchment.route()

        self.assertDictAlmostEqual(d1, arc1.vqip_out)

    def test_pull(self):
        catchment = Catchment(
            name="",
            data_input_dict={
                ("flow", 1): 10,
                ("phosphate", 1): 0.4,
                ("temperature", 1): 10,
            },
        )
        waste = Waste(name="")
        arc1 = Arc(in_port=catchment, out_port=waste, name="")
        arc1.vqip_in["volume"] = 2
        catchment.t = 1
        vq1 = catchment.pull_check_abstraction()
        d1 = {"volume": 10 - 2, "phosphate": 0.4 * 8, "temperature": 10}
        self.assertDictAlmostEqual(d1, vq1)

        vq2 = catchment.pull_check_abstraction({"volume": 3})
        d2 = {"volume": 3, "phosphate": 0.4 * 3, "temperature": 10}
        self.assertDictAlmostEqual(d2, vq2)

        vq2 = catchment.pull_set_abstraction({"volume": 3})
        self.assertDictAlmostEqual(d2, vq2)


if __name__ == "__main__":
    unittest.main()
