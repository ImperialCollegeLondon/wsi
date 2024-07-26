# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.demand import Demand, ResidentialDemand
from wsimod.nodes.land import Land
from wsimod.nodes.waste import Waste
from wsimod.orchestration.model import to_datetime


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

    def test_get_demand(self):
        demand = Demand(
            name="",
            constant_demand=10,
            pollutant_load={"phosphate": 0.1, "temperature": 12},
        )

        reply = demand.get_demand()
        d1 = {"volume": 10, "phosphate": 0.1, "temperature": 12}
        self.assertDictAlmostEqual(d1, reply["default"])

    def test_create_demand(self):
        demand = Demand(
            name="",
            constant_demand=10,
            pollutant_load={"phosphate": 0.1, "temperature": 12},
        )

        waste = Waste(name="")
        arc1 = Arc(in_port=demand, out_port=waste, name="")
        demand.create_demand()
        d1 = {"volume": 10, "phosphate": 0.1, "temperature": 12}
        self.assertDictAlmostEqual(d1, arc1.vqip_out)
        self.assertDictAlmostEqual(d1, demand.total_demand)

        d2 = {"volume": 0, "phosphate": 0, "temperature": 0}
        self.assertDictAlmostEqual(d2, demand.total_received)

    def test_house_demand(self):
        demand = ResidentialDemand(
            name="",
            pollutant_load={"phosphate": 0.1},
            data_input_dict={("temperature", 1): 10},
            population=5,
            per_capita=0.12,
            constant_weighting=0.4,
            constant_temp=8,
        )
        demand.t = 1
        reply = demand.get_house_demand()
        d1 = {
            "phosphate": 5 * 0.1,
            "volume": 5 * 0.12,
            "temperature": 10 * 0.6 + 8 * 0.4,
        }

        self.assertDictAlmostEqual(d1, reply)

    def test_excess_to_garden(self):
        demand = ResidentialDemand(name="", gardening_efficiency=0.3)

        self.assertEqual(0.36, demand.excess_to_garden_demand(1.2))

    def test_garden_demand(self):
        date = to_datetime("2000-05-01")
        demand = ResidentialDemand(name="", gardening_efficiency=0.4)
        demand.t = date

        land = Land(
            name="",
            surfaces=[
                {
                    "type_": "GardenSurface",
                    "area": 1,
                    "rooting_depth": 1,
                    "field_capacity": 0.3,
                    "wilting_point": 0.1,
                    "initial_storage": 0.2,
                }
            ],
            data_input_dict={
                ("temperature", date): 15,
                ("precipitation", date): 0,
                ("et0", date): 0.03,
            },
        )
        land.t = date
        Arc(in_port=demand, out_port=land, name="")
        land.run()
        reply = demand.get_garden_demand()

        d1 = {"volume": 0.03 * 0.4, "temperature": 0, "phosphate": 0}
        self.assertDictAlmostEqual(d1, reply)

    def test_demand_overrides(self):
        demand = Demand(
            name="",
            constant_demand=10,
            pollutant_load={"phosphate": 0.1, "temperature": 12},
        )
        demand.apply_overrides(
            {"constant_demand": 20, "pollutant_load": {"phosphate": 0.5}}
        )
        self.assertEqual(demand.constant_demand, 20)
        self.assertDictEqual(
            demand.pollutant_load, {"phosphate": 0.5, "temperature": 12}
        )

    def test_residentialdemand_overrides(self):
        demand = ResidentialDemand(
            name="",
            gardening_efficiency=0.4,
            pollutant_load={"phosphate": 0.1, "temperature": 12},
        )
        demand.apply_overrides(
            {
                "gardening_efficiency": 0.5,
                "population": 153.2,
                "per_capita": 32.4,
                "constant_weighting": 47.5,
                "constant_temp": 0.71,
                "constant_demand": 20,
                "pollutant_load": {"phosphate": 0.5},
            }
        )
        self.assertEqual(demand.gardening_efficiency, 0.5)
        self.assertEqual(demand.population, 153.2)
        self.assertEqual(demand.per_capita, 32.4)
        self.assertEqual(demand.constant_weighting, 47.5)
        self.assertEqual(demand.constant_temp, 0.71)

        self.assertEqual(demand.constant_demand, 20)
        self.assertDictEqual(
            demand.pollutant_load, {"phosphate": 0.5, "temperature": 12}
        )


if __name__ == "__main__":
    unittest.main()
