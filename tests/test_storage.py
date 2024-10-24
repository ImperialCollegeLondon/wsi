# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
import warnings
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.storage import (
    Groundwater,
    QueueGroundwater,
    Reservoir,
    River,
    RiverReservoir,
    Storage,
)
from wsimod.nodes.waste import Waste


class MyTestClass(TestCase):
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

    def test_push_storage(self):
        constants.set_simple_pollutants()

        storage = Storage(
            name="",
            capacity=10,
            initial_storage={"volume": 4, "phosphate": 0.2, "temperature": 12},
        )

        d1 = {"volume": 6, "phosphate": 0.2 * 6 / 4, "temperature": 12}
        reply = storage.push_check()
        self.assertDictAlmostEqual(d1, reply)

        d2 = {"volume": 2, "phosphate": 0.2 * 2 / 4, "temperature": 12}
        reply = storage.push_check({"volume": 2})
        self.assertDictAlmostEqual(d2, reply)

        d3 = {"volume": 8, "phosphate": 0.25, "temperature": 13}
        reply = storage.push_set(d3)

        d4 = {"volume": 2, "phosphate": 0.25 * 2 / 8, "temperature": 13}
        self.assertDictAlmostEqual(d4, reply)

        d5 = {
            "volume": 10,
            "phosphate": 0.25 * 6 / 8 + 0.2,
            "temperature": (13 * 6 + 12 * 4) / 10,
        }
        self.assertDictAlmostEqual(d5, storage.tank.storage)

    def test_distribute(self):
        constants.set_simple_pollutants()
        d1 = {"volume": 4, "phosphate": 0.2, "temperature": 12}
        storage = Storage(name="", capacity=10, initial_storage=d1)
        waste = Waste(name="")
        arc1 = Arc(in_port=storage, out_port=waste, name="")

        storage.distribute()
        self.assertDictAlmostEqual(d1, arc1.vqip_in)
        d2 = {"volume": 0, "phosphate": 0, "temperature": 12}
        self.assertDictAlmostEqual(d2, storage.tank.storage)

    def test_groundwater_distribute(self):
        constants.set_simple_pollutants()
        d1 = {"volume": 4, "phosphate": 0.2, "temperature": 12}
        groundwater = Groundwater(
            name="", capacity=10, initial_storage=d1, residence_time=3
        )
        waste = Waste(name="")
        arc1 = Arc(in_port=groundwater, out_port=waste, name="")

        groundwater.distribute()
        d2 = {"volume": 4 / 3, "phosphate": 0.2 / 3, "temperature": 12}
        self.assertDictAlmostEqual(d2, arc1.vqip_in, 15)
        d2 = {"volume": 4 * 2 / 3, "phosphate": 0.2 * 2 / 3, "temperature": 12}
        self.assertDictAlmostEqual(d2, groundwater.tank.storage, 14)

    def test_groundwater_infiltrate(self):
        constants.set_simple_pollutants()
        d1 = {"volume": 4, "phosphate": 0.2, "temperature": 12}
        groundwater = Groundwater(
            name="",
            capacity=10,
            initial_storage=d1,
            infiltration_threshold=0.2,
            infiltration_pct=0.1,
        )
        sewer = Sewer(name="", capacity=5)
        arc1 = Arc(in_port=groundwater, out_port=sewer, name="")

        groundwater.infiltrate()
        nv = ((4 - (10 * 0.2)) * 0.1) ** 0.5
        d2 = {"volume": nv, "temperature": 12, "phosphate": 0.2 * nv / 4}
        self.assertDictAlmostEqual(d2, arc1.vqip_in)

    def test_qgroundwater_push(self):
        constants.set_simple_pollutants()
        groundwater = QueueGroundwater(name="", capacity=10, timearea={0: 0.2, 1: 0.8})
        d1 = {"volume": 4, "phosphate": 0.2, "temperature": 12}
        _ = groundwater.push_set_timearea(d1)
        self.assertDictAlmostEqual(d1, groundwater.tank.storage, 14)

        d2 = {"volume": 4 * 0.2, "phosphate": 0.2 * 0.2, "temperature": 12}
        self.assertDictAlmostEqual(d2, groundwater.tank.active_storage, 14)

        d3 = {"volume": 4 * 0.8, "phosphate": 0.2 * 0.8, "temperature": 12}
        self.assertDictAlmostEqual(d3, groundwater.tank.internal_arc.queue[1], 14)

        groundwater.end_timestep()
        self.assertDictAlmostEqual(d1, groundwater.tank.active_storage, 14)

    def test_qgroundwater_push(self):
        constants.set_simple_pollutants()
        groundwater = QueueGroundwater(name="", capacity=10, timearea={0: 0.2, 1: 0.8})

        waste = Waste(name="")
        arc1 = Arc(in_port=groundwater, out_port=waste, name="")

        d1 = {"volume": 4, "phosphate": 0.2, "temperature": 12}
        _ = groundwater.push_set_timearea(d1)

        groundwater.distribute()

        d2 = {"volume": 4 * 0.2, "phosphate": 0.2 * 0.2, "temperature": 12}
        self.assertDictAlmostEqual(d2, arc1.vqip_in, 14)

        d3 = {"volume": 4 * 0.8, "phosphate": 0.2 * 0.8, "temperature": 12}
        self.assertDictAlmostEqual(d3, groundwater.tank.storage, 14)

    def test_qgroundwater_pull(self):
        constants.set_simple_pollutants()
        groundwater = QueueGroundwater(name="", capacity=10, timearea={0: 0.2, 1: 0.8})

        waste = Waste(name="")
        Arc(in_port=groundwater, out_port=waste, name="")

        d1 = {"volume": 4, "phosphate": 0.2, "temperature": 12}
        _ = groundwater.push_set_timearea(d1)

        d2 = {"volume": 4 * 0.2, "phosphate": 0.2 * 0.2, "temperature": 12}
        self.assertDictAlmostEqual(d2, groundwater.pull_check_active(), 14)

        d2 = {"volume": 3, "phosphate": 0.2 * 3 / 4, "temperature": 12}
        reply = groundwater.pull_set_active({"volume": 3})
        self.assertDictAlmostEqual(d2, reply, 14)

        d3 = {
            "volume": 4 * 0.2 * (1 - 3 / 4),
            "phosphate": 0.2 * 0.2 * (1 - 3 / 4),
            "temperature": 12,
        }
        self.assertDictAlmostEqual(d3, groundwater.tank.active_storage, 14)

        d4 = {
            "volume": 4 * 0.8 * (1 - 3 / 4),
            "phosphate": 0.2 * 0.8 * (1 - 3 / 4),
            "temperature": 12,
        }
        self.assertDictAlmostEqual(d4, groundwater.tank.internal_arc.queue[1], 14)

    def test_river_pull(self):
        constants.set_simple_pollutants()
        river = River(
            name="",
            length=200,
            width=20,
            velocity=0.2 * 86400,
            damp=0.1,
            mrf=10,
            initial_storage={"volume": 30, "phosphate": 0.2, "temperature": 23},
        )
        d1 = {
            "volume": 19.988412514484356,
            "phosphate": 0.1332560834298957,
            "temperature": 23,
        }
        self.assertDictAlmostEqual(d1, river.pull_check_river())

        d2 = {"volume": 2.0, "phosphate": 0.2 * 2 / 30, "temperature": 23}
        self.assertDictAlmostEqual(d2, river.pull_check_river({"volume": 2}))

        reply = river.pull_set_river({"volume": 25})
        self.assertDictAlmostEqual(d1, reply)

    def test_river_depth(self):
        constants.set_simple_pollutants()
        river = River(
            name="",
            length=200,
            width=20,
            velocity=0.2 * 86400,
            damp=0.1,
            mrf=10,
            initial_storage={"volume": 30, "phosphate": 0.2, "temperature": 23},
        )
        river.update_depth()
        self.assertEqual(0.0075, river.current_depth)

    # TODO test river biochemical processes once they have been functionalised

    def test_reservoir(self):
        reservoir1 = Reservoir(
            name="",
            capacity=35,
            initial_storage={"volume": 30, "phosphate": 0.2, "temperature": 23},
        )
        d1 = {"volume": 3, "phosphate": 0.1, "temperature": 10}
        reservoir2 = Reservoir(name="", capacity=5, initial_storage=d1)

        arc1 = Arc(in_port=reservoir2, out_port=reservoir1, name="")

        reservoir1.make_abstractions()

        self.assertDictAlmostEqual(d1, arc1.vqip_in)

        d2 = {"volume": 33, "phosphate": 0.3, "temperature": (30 * 23 + 10 * 3) / 33}
        self.assertDictAlmostEqual(d2, reservoir1.tank.storage, 15)

    def test_riverreservoir_push(self):
        reservoir = RiverReservoir(
            name="",
            capacity=35,
            initial_storage={"volume": 30, "phosphate": 0.2, "temperature": 23},
            environmental_flow=5,
        )
        waste = Waste(name="")
        arc1 = Arc(in_port=reservoir, out_port=waste, arc="", capacity=20)

        reply = reservoir.push_check()
        d1 = {"volume": 25, "phosphate": 0.2 / 30 * 25, "temperature": 23}
        self.assertDictAlmostEqual(d1, reply, 15)

        reply = reservoir.push_set({"volume": 35, "phosphate": 0.5, "temperature": 20})
        d2 = {
            "volume": 10,
            "phosphate": (0.5 + 0.2) * 10 / 65,
            "temperature": (23 * 30 + 20 * 35) / 65,
        }
        self.assertDictAlmostEqual(d2, reply, 15)

        d3 = {
            "volume": 20,
            "phosphate": (0.5 + 0.2) * 20 / 65,
            "temperature": (23 * 30 + 20 * 35) / 65,
        }
        self.assertDictAlmostEqual(d3, arc1.vqip_in, 15)

    def test_riverreservoir_environmental(self):
        reservoir = RiverReservoir(
            name="",
            capacity=35,
            initial_storage={"volume": 30, "phosphate": 0.2, "temperature": 23},
            environmental_flow=15,
        )
        waste = Waste(name="")
        arc1 = Arc(in_port=reservoir, out_port=waste, arc="", capacity=20)

        reservoir.push_set({"volume": 10, "phosphate": 0.5, "temperature": 20})

        reservoir.satisfy_environmental()
        self.assertEqual(15, reservoir.total_environmental_satisfied)

        d1 = {
            "volume": 15,
            "phosphate": (0.5 + 0.2) * 15 / 40,
            "temperature": (20 * 10 + 30 * 23) / 40,
        }
        self.assertDictAlmostEqual(d1, arc1.vqip_in, 15)

        d2 = {
            "volume": 25,
            "phosphate": (0.5 + 0.2) * 25 / 40,
            "temperature": (20 * 10 + 30 * 23) / 40,
        }
        self.assertDictAlmostEqual(d2, reservoir.tank.storage, 15)

    def test_storage_overrides(self):
        constants.set_default_pollutants()
        storage = Storage(
            name="", decays={"phosphate": {"constant": 1.005, "exponent": 1.005}}
        )
        storage.apply_overrides(
            {
                "capacity": 1.43,
                "area": 2.36,
                "datum": 0.32,
                "decays": {"nitrite": {"constant": 10.005, "exponent": 1.105}},
            }
        )
        self.assertEqual(storage.capacity, 1.43)
        self.assertEqual(storage.tank.capacity, 1.43)
        self.assertEqual(storage.area, 2.36)
        self.assertEqual(storage.tank.area, 2.36)
        self.assertEqual(storage.datum, 0.32)
        self.assertEqual(storage.tank.datum, 0.32)
        self.assertDictEqual(
            storage.decays,
            {
                "phosphate": {"constant": 1.005, "exponent": 1.005},
                "nitrite": {"constant": 10.005, "exponent": 1.105},
            },
        )
        self.assertDictEqual(
            storage.tank.decays,
            {
                "phosphate": {"constant": 1.005, "exponent": 1.005},
                "nitrite": {"constant": 10.005, "exponent": 1.105},
            },
        )

    def test_groundwater_overrides(self):
        groundwater = Groundwater(
            name="", decays={"phosphate": {"constant": 1.005, "exponent": 1.005}}
        )
        groundwater.apply_overrides(
            {
                "residence_time": 27.3,
                "infiltration_threshold": 200,
                "infiltration_pct": 0.667,
                "capacity": 1.43,
                "area": 2.36,
                "datum": 0.32,
                "decays": {"nitrite": {"constant": 10.005, "exponent": 1.105}},
            }
        )
        self.assertEqual(groundwater.residence_time, 27.3)
        self.assertEqual(groundwater.infiltration_threshold, 200)
        self.assertEqual(groundwater.infiltration_pct, 0.667)
        self.assertEqual(groundwater.capacity, 1.43)
        self.assertEqual(groundwater.tank.capacity, 1.43)
        self.assertEqual(groundwater.area, 2.36)
        self.assertEqual(groundwater.tank.area, 2.36)
        self.assertEqual(groundwater.datum, 0.32)
        self.assertEqual(groundwater.tank.datum, 0.32)
        self.assertDictEqual(
            groundwater.decays,
            {
                "phosphate": {"constant": 1.005, "exponent": 1.005},
                "nitrite": {"constant": 10.005, "exponent": 1.105},
            },
        )
        self.assertDictEqual(
            groundwater.tank.decays,
            {
                "phosphate": {"constant": 1.005, "exponent": 1.005},
                "nitrite": {"constant": 10.005, "exponent": 1.105},
            },
        )

    def test_river_overrides(self):
        river = River(name="")
        overrides = {
            "length": 27.3,
            "width": 200,
            "velocity": 0.667,
            "damp": 1.43,
            "mrf": 2.36,
            "uptake_PNratio": 0.32,
            "bulk_density": 5.32,
            "denpar_w": 0.432,
            "T_wdays": 23.5,
            "halfsatINwater": 3.269,
            "hsatTP": 2.431,
            "limpppar": 6.473,
            "prodNpar": 7.821,
            "prodPpar": 8.231,
            "muptNpar": 6.213,
            "muptPpar": 7.021,
            "max_temp_lag": 3.213,
            "max_phosphorus_lag": 78.321,
        }
        overrides_to_check = overrides.copy()
        river.apply_overrides(overrides)
        for k, v in overrides_to_check.items():
            if k == "area":
                v = 27.3 * 200
                self.assertEqual(river.tank.area, v)
            if k == "capacity":
                v = constants.UNBOUNDED_CAPACITY
                self.assertEqual(river.tank.capacity, v)
            self.assertEqual(getattr(river, k), v)
        # test runtimeerrors
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            river.apply_overrides({"area": 75.2})
            assert "specifying area is depreciated" in str(w[0])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            river.apply_overrides({"capacity": 123})
            assert "specifying capacity is depreciated" in str(w[0])

    def test_riverreservoir_overrides(self):
        riverreservoir = RiverReservoir(name="")
        riverreservoir.apply_overrides({"environmental_flow": 154})
        self.assertEqual(riverreservoir.environmental_flow, 154)


if __name__ == "__main__":
    unittest.main()
