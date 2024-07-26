# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.sewer import Sewer
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

    def test_push_sewer(self):
        sewer = Sewer(name="", capacity=10, pipe_time=1)

        d1 = {"volume": 4, "phosphate": 2, "temperature": 10}

        d2 = {"volume": 10, "phosphate": 0, "temperature": 0}
        reply = sewer.push_check_sewer()
        self.assertDictAlmostEqual(d2, reply)

        d2["volume"] = 4
        reply = sewer.push_check_sewer(d1)
        self.assertDictAlmostEqual(d2, reply)

        d2["volume"] = 0
        d2["temperature"] = 10  # Related to TODO in nodes.py/QueueTank/push_storage

        reply = sewer.push_set_sewer(d1)
        self.assertDictAlmostEqual(d2, reply)
        self.assertDictAlmostEqual(d1, sewer.sewer_tank.storage)
        self.assertDictAlmostEqual(d1, sewer.sewer_tank.internal_arc.queue[1])

        d2["temperature"] = 0
        self.assertDictAlmostEqual(d2, sewer.sewer_tank.active_storage)

        sewer.end_timestep()
        self.assertDictAlmostEqual(d1, sewer.sewer_tank.active_storage)

    def test_push_land(self):
        sewer = Sewer(name="", capacity=10, pipe_timearea={0: 0.3, 1: 0.7})
        d1 = {"volume": 4, "phosphate": 2, "temperature": 10}
        sewer.push_set_land(d1)

        self.assertDictAlmostEqual(d1, sewer.sewer_tank.storage)

        d2 = {"volume": 4 * 0.3, "phosphate": 2 * 0.3, "temperature": 10}

        d3 = {"volume": 4 * 0.7, "phosphate": 2 * 0.7, "temperature": 10}
        self.assertDictAlmostEqual(d2, sewer.sewer_tank.active_storage)
        self.assertDictAlmostEqual(d3, sewer.sewer_tank.internal_arc.queue[1])

        sewer.end_timestep()
        self.assertDictAlmostEqual(d1, sewer.sewer_tank.active_storage)

    def test_make_discharge(self):
        sewer = Sewer(name="", capacity=10, pipe_timearea={0: 0.3, 1: 0.7})
        waste = Waste(name="")
        arc1 = Arc(in_port=sewer, out_port=waste, capacity=2)
        d1 = {"volume": 9, "phosphate": 2, "temperature": 10}
        sewer.push_set_land(d1)

        sewer.make_discharge()

        d2 = {"volume": 2, "phosphate": 2 * 2 / 9, "temperature": 10}
        self.assertDictAlmostEqual(d2, arc1.vqip_in, 15)

        d3 = {"volume": 7, "phosphate": 7 * 2 / 9, "temperature": 10}
        self.assertDictAlmostEqual(d3, sewer.sewer_tank.storage, 15)

    def test_sewer_overrides(self):
        sewer = Sewer(name="", capacity=10, pipe_timearea={0: 0.3, 1: 0.7})
        sewer.apply_overrides(
            {
                "capacity": 3,
                "chamber_area": 2,
                "chamber_floor": 3.5,
                "pipe_time": 8.4,
                "pipe_timearea": {0: 0.5, 1: 0.5},
            }
        )
        self.assertEqual(sewer.capacity, 3)
        self.assertEqual(sewer.sewer_tank.capacity, 3)
        self.assertEqual(sewer.chamber_area, 2)
        self.assertEqual(sewer.sewer_tank.area, 2)
        self.assertEqual(sewer.chamber_floor, 3.5)
        self.assertEqual(sewer.sewer_tank.datum, 3.5)
        self.assertEqual(sewer.pipe_time, 8.4)
        self.assertEqual(sewer.pipe_timearea, {0: 0.5, 1: 0.5})


if __name__ == "__main__":
    unittest.main()
