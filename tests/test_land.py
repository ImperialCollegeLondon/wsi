# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from math import exp
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.land import (
    GardenSurface,
    GrowingSurface,
    ImperviousSurface,
    IrrigationSurface,
    Land,
    PerviousSurface,
    Surface,
)
from wsimod.nodes.nodes import Node
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.storage import Reservoir
from wsimod.orchestration.model import to_datetime


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

    def test_surface_read(self):
        constants.set_simple_pollutants()
        node = Node(name="", data_input_dict={("temperature", 1): 15})
        node.t = 1
        node.monthyear = 1

        surface = Surface(data_input_dict={("phosphate", 1): 0.1}, parent=node)

        self.assertEqual(surface.get_data_input("temperature"), 15)
        self.assertEqual(surface.get_data_input_surface("phosphate"), 0.1)

    def test_deposition(self):
        constants.set_simple_pollutants()
        d1 = {"volume": 0.1, "phosphate": 2, "temperature": 5}

        surface = Surface(parent=None, area=5, depth=0.1)
        surface.dry_deposition_to_tank(d1)
        self.assertDictAlmostEqual(d1, surface.storage)

        d2 = {"volume": 0.2, "phosphate": 4, "temperature": 5}
        surface.wet_deposition_to_tank(d1)
        self.assertDictAlmostEqual(d2, surface.storage)

    def test_atmospheric_dep(self):
        constants.set_simple_pollutants()
        node = Node(name="")
        node.monthyear = 1

        inputs = {("nhx-dry", 1): 0.1, ("noy-dry", 1): 0.4, ("srp-dry", 1): 0.2}

        surface = Surface(data_input_dict=inputs, parent=node, area=10)

        d1 = {"ammonia": 1, "nitrate": 4, "phosphate": 2, "volume": 0, "temperature": 0}
        d2 = {"volume": 0, "temperature": 0, "phosphate": 0}
        (r1, r2) = surface.atmospheric_deposition()
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)

    def test_precip_dep(self):
        constants.set_simple_pollutants()
        node = Node(name="")
        node.monthyear = 1

        inputs = {("nhx-wet", 1): 0.1, ("noy-wet", 1): 0.4, ("srp-wet", 1): 0.2}

        surface = Surface(data_input_dict=inputs, parent=node, area=10)

        d1 = {"ammonia": 1, "nitrate": 4, "phosphate": 2, "volume": 0, "temperature": 0}
        d2 = {"volume": 0, "temperature": 0, "phosphate": 0}
        (r1, r2) = surface.precipitation_deposition()
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)

    def test_run_surface(self):
        constants.set_default_pollutants()

        node = Land(name="", data_input_dict={("temperature", 1): 15})
        node.t = 1
        node.monthyear = 1

        inputs = {
            ("nhx-wet", 1): 0.1,
            ("noy-wet", 1): 0.4,
            ("srp-wet", 1): 0.2,
            ("nhx-dry", 1): 0.1,
            ("noy-dry", 1): 0.4,
            ("srp-dry", 1): 0.2,
        }

        decays = {
            "nitrite": {"constant": 0.005, "exponent": 1.005},
            "ammonia": {"constant": 0.05, "exponent": 1.05},
        }

        surface = Surface(data_input_dict=inputs, parent=node, area=10, decays=decays)

        surface.run()
        d1 = surface.empty_vqip()

        self.assertDictAlmostEqual(d1, node.running_outflow_mb)

        d1["phosphate"] = 4
        d1["ammonia"] = 2
        d1["nitrate"] = 8

        self.assertDictAlmostEqual(d1, node.running_inflow_mb)
        self.assertDictAlmostEqual(d1, surface.storage)

        surface.end_timestep()
        d1["ammonia"] = d1["ammonia"] * (1 - 0.05 * 1.05 ** (15 - 20))
        self.assertDictAlmostEqual(d1, surface.storage)

        surface.run()
        d1["phosphate"] = 8
        d1["ammonia"] = 2 + 2 * (1 - 0.05 * 1.05 ** (15 - 20))
        d1["nitrite"] = 2 * 0.05 * 1.05 ** (15 - 20)
        d1["nitrate"] = 16
        self.assertDictAlmostEqual(d1, surface.storage)

        surface.end_timestep()
        surface.run()
        d1["phosphate"] = 12
        d1["nitrate"] = 24 + d1["nitrite"] * (0.005 * 1.005 ** (15 - 20))
        d1["nitrite"] = d1["nitrite"] * (1 - 0.005 * 1.005 ** (15 - 20)) + d1[
            "ammonia"
        ] * (0.05 * 1.05 ** (15 - 20))
        d1["ammonia"] = (
            2
            + 2 * (1 - 0.05 * 1.05 ** (15 - 20))
            + 2 * (1 - 0.05 * 1.05 ** (15 - 20)) ** 2
        )

        self.assertDictAlmostEqual(d1, surface.storage, 16)

    def test_simple_dep(self):
        constants.set_simple_pollutants()
        d1 = {"phosphate": 2, "volume": 0, "temperature": 0}

        surface = Surface(pollutant_load=d1, area=1)

        (in_, out_) = surface.simple_deposition()

        d2 = {"volume": 0, "temperature": 0, "phosphate": 0}
        self.assertDictAlmostEqual(d1, in_)
        self.assertDictAlmostEqual(surface.storage, in_)
        self.assertDictAlmostEqual(d2, out_)

    def test_urban_precip(self):
        constants.set_simple_pollutants()
        inputs = {
            ("precipitation", 1): 0.1,
            ("et0", 1): 0.01,
            ("temperature", 1): 10,
            ("precipitation", 2): 0,
            ("et0", 2): 0.02,
            ("temperature", 2): 15,
        }

        node = Node(name="", data_input_dict=inputs)

        surface = ImperviousSurface(
            parent=node, area=1.5, et0_to_e=0.9, pore_depth=0.015
        )

        node.t = 1

        d1 = {"volume": 0.1 * 1.5, "temperature": 0, "phosphate": 0}
        d2 = {"phosphate": 0, "volume": 0.01 * 1.5 * 0.9, "temperature": 0}
        d3 = {"phosphate": 0, "temperature": 10, "volume": (0.1 - 0.01 * 0.9) * 1.5}
        (r1, r2) = surface.precipitation_evaporation()
        self.assertDictAlmostEqual(d1, r1, 17)
        self.assertDictAlmostEqual(d2, r2, 17)
        self.assertDictAlmostEqual(d3, surface.storage, 17)

        node.t = 2
        d3 = {"volume": 0, "temperature": 0, "phosphate": 0}
        d4 = {"phosphate": 0, "volume": 0.02 * 1.5 * 0.9, "temperature": 0}
        d5 = {
            "phosphate": 0,
            "temperature": 10,
            "volume": (0.1 - (0.01 + 0.02) * 0.9) * 1.5,
        }
        (r1, r2) = surface.precipitation_evaporation()
        self.assertDictAlmostEqual(d3, r1, 17)
        self.assertDictAlmostEqual(d4, r2, 17)
        self.assertDictAlmostEqual(d5, surface.storage, 17)

    def test_urban_push(self):
        constants.set_simple_pollutants()
        inputs = {
            ("precipitation", 1): 0.1,
            ("et0", 1): 0.01,
            ("temperature", 1): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = 1
        sewer = Sewer(name="", capacity=2)
        _ = Arc(in_port=node, out_port=sewer, name="")
        surface = ImperviousSurface(
            parent=node, area=1.5, et0_to_e=0.9, pore_depth=0.015
        )
        _ = surface.precipitation_evaporation()
        _ = surface.push_to_sewers()

        d1 = {"volume": 0.015 * 1.5, "phosphate": 0, "temperature": 10}
        d2 = {
            "volume": (0.1 - 0.01 * 0.9 - 0.015) * 1.5,
            "phosphate": 0,
            "temperature": 10,
        }

        self.assertDictAlmostEqual(d1, surface.storage, 16)
        self.assertDictAlmostEqual(d2, sewer.sewer_tank.storage, 16)

    def test_perv_cmd(self):
        surface = PerviousSurface(
            parent="", depth=0.5, area=1.5, initial_storage=0.5 * 1.5 * 0.25
        )
        self.assertAlmostEqual((1 - 0.25) * 0.5, surface.get_cmd())

    def test_perv_cmd(self):
        surface = PerviousSurface(
            parent="", depth=0.5, area=1.5, initial_storage=0.5 * 1.5 * 0.25
        )
        self.assertAlmostEqual(0.25 * 0.5, surface.get_smc())

    def test_ihacres1(self):
        # Above field capacity
        constants.set_simple_pollutants()
        inputs = {
            ("precipitation", 1): 0.1,
            ("et0", 1): 0.01,
            ("temperature", 1): 10,
        }

        node = Node(name="", data_input_dict=inputs)

        surface = PerviousSurface(
            parent=node,
            depth=0.5,
            area=1.5,
            total_porosity=0.45,
            field_capacity=0.35,
            wilting_point=0.12,
            infiltration_capacity=0.4,
            surface_coefficient=0.04,
            percolation_coefficient=0.6,
            et0_coefficient=0.4,
            ihacres_p=12,
            initial_storage=0.4 * 0.5 * 1.5,
        )

        node.t = 1

        (r1, r2) = surface.ihacres()

        d1 = {"volume": 0.1 * 1.5, "phosphate": 0, "temperature": 0}

        d2 = {"volume": 0.01 * 1.5 * 0.4, "phosphate": 0, "temperature": 0}

        outflow_ = 0.1 * (
            1 - ((0.45 * 0.5 - 0.4 * 0.5) / (0.45 * 0.5 - 0.35 * 0.5)) ** 12
        )

        total_water_passing_through_soil = (0.1 - 0.01 * 0.4 - outflow_ * 0.04) * 1.5

        temperature = (0 * 0.4 * 0.5 * 1.5) + (
            total_water_passing_through_soil * 10
        ) / (total_water_passing_through_soil + 0.4 * 0.5 * 1.5)

        d3 = {
            "volume": outflow_ * (1 - 0.04) * 0.6 * 1.5,
            "phosphate": 0,
            "temperature": temperature,
        }

        d4 = {
            "volume": outflow_ * (1 - 0.04) * (1 - 0.6) * 1.5,
            "phosphate": 0,
            "temperature": temperature,
        }

        d5 = {
            "volume": (0.1 - outflow_ - 0.01 * 0.4 + 0.4 * 0.5) * 1.5,
            "phosphate": 0,
            "temperature": temperature,
        }

        d6 = {"volume": outflow_ * 0.04 * 1.5, "phosphate": 0, "temperature": 10}

        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
        self.assertDictAlmostEqual(d3, surface.percolation, 15)
        self.assertDictAlmostEqual(d4, surface.subsurface_flow, 15)
        self.assertDictAlmostEqual(d5, surface.storage, 15)
        self.assertDictAlmostEqual(d6, surface.infiltration_excess)

    def test_ihacres2(self):
        # Below wilting point
        constants.set_simple_pollutants()
        inputs = {
            ("precipitation", 1): 0,
            ("et0", 1): 0.01,
            ("temperature", 1): 10,
        }

        node = Node(name="", data_input_dict=inputs)

        surface = PerviousSurface(
            parent=node,
            depth=0.5,
            area=1.5,
            total_porosity=0.45,
            field_capacity=0.35,
            wilting_point=0.12,
            infiltration_capacity=0.4,
            surface_coefficient=0.04,
            percolation_coefficient=0.6,
            et0_coefficient=0.4,
            ihacres_p=12,
            initial_storage=0.11 * 0.5 * 1.5,
        )

        node.t = 1

        (r1, r2) = surface.ihacres()

        evaporation_ = (
            0.01
            * 0.4
            * exp(2 * (1 - (0.45 * 0.5 - 0.11 * 0.5) / (0.45 * 0.5 - 0.12 * 0.5)))
            * 1.5
        )
        d1 = {"volume": 0, "phosphate": 0, "temperature": 0}

        d2 = {"volume": evaporation_, "phosphate": 0, "temperature": 0}

        d3 = {"volume": 0, "phosphate": 0, "temperature": 0}

        d4 = {
            "volume": 0.11 * 0.5 * 1.5 - evaporation_,
            "phosphate": 0,
            "temperature": 0,
        }

        d5 = {"volume": 0, "phosphate": 0, "temperature": 10}

        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
        self.assertDictAlmostEqual(d3, surface.percolation, 15)
        self.assertDictAlmostEqual(d3, surface.subsurface_flow)
        self.assertDictAlmostEqual(d4, surface.storage, 15)
        self.assertDictAlmostEqual(d5, surface.infiltration_excess)

    def test_ihacres3(self):
        # Infiltration excess
        constants.set_simple_pollutants()
        inputs = {
            ("precipitation", 1): 0.1,
            ("et0", 1): 0.01,
            ("temperature", 1): 10,
        }

        node = Node(name="", data_input_dict=inputs)

        surface = PerviousSurface(
            parent=node,
            depth=0.5,
            area=1.5,
            total_porosity=0.45,
            field_capacity=0.35,
            wilting_point=0.12,
            infiltration_capacity=0.05,
            surface_coefficient=0.04,
            percolation_coefficient=0.6,
            et0_coefficient=0.4,
            ihacres_p=12,
            initial_storage=0.4 * 0.5 * 1.5,
        )

        node.t = 1

        (r1, r2) = surface.ihacres()

        d1 = {"volume": 0.1 * 1.5, "phosphate": 0, "temperature": 0}

        d2 = {"volume": 0.01 * 1.5 * 0.4, "phosphate": 0, "temperature": 0}

        outflow_ = 0.05 * (
            1 - ((0.45 * 0.5 - 0.4 * 0.5) / (0.45 * 0.5 - 0.35 * 0.5)) ** 12
        )

        total_water_passing_through_soil = (0.05 - 0.01 * 0.4 - outflow_ * 0.04) * 1.5

        temperature = (0 * 0.4 * 0.5 * 1.5) + (
            total_water_passing_through_soil * 10
        ) / (total_water_passing_through_soil + 0.4 * 0.5 * 1.5)

        d3 = {
            "volume": outflow_ * (1 - 0.04) * 0.6 * 1.5,
            "phosphate": 0,
            "temperature": temperature,
        }

        d4 = {
            "volume": outflow_ * (1 - 0.04) * (1 - 0.6) * 1.5,
            "phosphate": 0,
            "temperature": temperature,
        }

        d5 = {
            "volume": (0.05 - outflow_ - 0.01 * 0.4 + 0.4 * 0.5) * 1.5,
            "phosphate": 0,
            "temperature": temperature,
        }

        d6 = {
            "volume": outflow_ * 0.04 * 1.5 + 0.05 * 1.5,
            "phosphate": 0,
            "temperature": 10,
        }

        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d2, r2)
        self.assertDictAlmostEqual(d3, surface.percolation, 15)
        self.assertDictAlmostEqual(d4, surface.subsurface_flow, 15)
        self.assertDictAlmostEqual(d5, surface.storage, 15)
        self.assertDictAlmostEqual(d6, surface.infiltration_excess)

    def test_perv_route(self):
        constants.set_simple_pollutants()
        land = Land(
            name="",
        )

        d1 = {"volume": 2.5, "temperature": 10, "phosphate": 0.3}

        d2 = {"volume": 2, "temperature": 12, "phosphate": 0.1}

        d3 = {"volume": 5, "temperature": 11, "phosphate": 0.2}

        d4 = {"volume": 0, "temperature": 0, "phosphate": 0}
        surface = PerviousSurface(parent=land, depth=0.5, area=1.5)
        surface.infiltration_excess = d1
        surface.subsurface_flow = d2
        surface.percolation = d3

        (r1, r2) = surface.route()
        self.assertDictAlmostEqual(d4, r1)
        self.assertDictAlmostEqual(d4, r2)
        self.assertDictAlmostEqual(d1, land.surface_runoff.storage)
        self.assertDictAlmostEqual(d2, land.subsurface_runoff.storage)
        self.assertDictAlmostEqual(d3, land.percolation.storage)

    def test_soil_temp(self):
        # Above field capacity
        constants.set_simple_pollutants()
        inputs = {
            ("temperature", 1): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = 1
        surface = PerviousSurface(
            parent=node,
            depth=0.5,
            area=1.5,
            initial_storage={"volume": 7, "temperature": 3, "phosphate": 0.2},
        )

        surface.soil_temp_w_prev = 0.2
        surface.soil_temp_w_air = 0.3
        surface.soil_temp_w_deep = 0.4
        surface.soil_temp_deep = 5

        d1 = {"volume": 0, "temperature": 0, "phosphate": 0}

        d2 = {
            "volume": 7,
            "temperature": (5 * 0.4 + 0.2 * 3 + 0.3 * 10) / (0.2 + 0.3 + 0.4),
            "phosphate": 0.2,
        }

        (r1, r2) = surface.calculate_soil_temperature()
        self.assertDictAlmostEqual(d1, r1)
        self.assertDictAlmostEqual(d1, r2)
        self.assertDictAlmostEqual(d2, surface.storage, 14)

    def create_growing_surface(self):
        """

        Returns:

        """
        constants.set_default_pollutants()
        node = Node(name="")
        initial_vol = node.empty_vqip()
        initial_vol["phosphate"] = 11
        initial_vol["nitrate"] = 2.5
        initial_vol["nitrite"] = 1.5
        initial_vol["ammonia"] = 0.1
        initial_vol["org-nitrogen"] = 0.2
        initial_vol["org-phosphorus"] = 3
        initial_vol["volume"] = 0.32
        initial_vol["temperature"] = 11

        initial_soil = {
            "phosphate": 1.2,
            "ammonia": 0.2,
            "nitrate": 0.3,
            "nitrite": 0.4,
            "org-nitrogen": 2,
            "org-phosphorus": 4,
        }

        crop_factor_stages = [0.0, 0.0, 0.3, 0.3, 1.2, 1.2, 0.325, 0.0, 0.0]
        crop_factor_stage_dates = [0, 90, 91, 121, 161, 213, 244, 245, 366]
        sowing_day = 91
        harvest_day = 244
        ET_depletion_factor = 0.55

        surface = GrowingSurface(
            rooting_depth=0.5,
            area=1.5,
            initial_storage=initial_vol,
            initial_soil_storage=initial_soil,
            crop_factor_stages=crop_factor_stages,
            crop_factor_stage_dates=crop_factor_stage_dates,
            sowing_day=sowing_day,
            harvest_day=harvest_day,
            ET_depletion_factor=ET_depletion_factor,
            wilting_point=0.1,
            field_capacity=0.2,
        )
        return surface, initial_vol, initial_soil

    def test_grow_init(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()

        d1 = {
            "N": ivol["nitrate"] + ivol["nitrite"] + ivol["ammonia"],
            "P": ivol["phosphate"],
        }
        self.assertDictAlmostEqual(
            surface.nutrient_pool.dissolved_inorganic_pool.storage, d1
        )

        d2 = {"N": ivol["org-nitrogen"], "P": ivol["org-phosphorus"]}
        self.assertDictAlmostEqual(
            surface.nutrient_pool.dissolved_organic_pool.storage, d2
        )

        d3 = {
            "N": isoil["nitrate"] + isoil["nitrite"] + isoil["ammonia"],
            "P": isoil["phosphate"],
        }
        self.assertDictAlmostEqual(
            surface.nutrient_pool.adsorbed_inorganic_pool.storage, d3, 15
        )

        d4 = {"N": isoil["org-nitrogen"], "P": isoil["org-phosphorus"]}
        self.assertDictAlmostEqual(surface.nutrient_pool.fast_pool.storage, d4)

    def test_grow_pull(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()

        d1 = surface.empty_vqip()
        for key, amount in ivol.items():
            d1[key] = amount * 0.25 / 0.32
        d1["temperature"] = ivol["temperature"]
        n1 = {
            "N": (ivol["nitrate"] + ivol["nitrite"] + ivol["ammonia"])
            * (1 - 0.25 / 0.32),
            "P": ivol["phosphate"] * (1 - 0.25 / 0.32),
        }
        n2 = {
            "N": ivol["org-nitrogen"] * (1 - 0.25 / 0.32),
            "P": ivol["org-phosphorus"] * (1 - 0.25 / 0.32),
        }
        n3 = {
            "N": (isoil["nitrate"] + isoil["nitrite"] + isoil["ammonia"]),
            "P": isoil["phosphate"],
        }
        n4 = {"N": isoil["org-nitrogen"], "P": isoil["org-phosphorus"]}
        reply = surface.pull_storage({"volume": 0.25})
        self.assertDictAlmostEqual(d1, reply, 15)
        self.assertDictAlmostEqual(
            surface.nutrient_pool.dissolved_inorganic_pool.storage, n1, 15
        )
        self.assertDictAlmostEqual(
            surface.nutrient_pool.dissolved_organic_pool.storage, n2, 15
        )
        self.assertDictAlmostEqual(
            surface.nutrient_pool.adsorbed_inorganic_pool.storage, n3, 15
        )
        self.assertDictAlmostEqual(surface.nutrient_pool.fast_pool.storage, n4, 15)

    def test_crop_cover(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        date = to_datetime("2000-05-01")
        node = Node(name="")
        node.t = date
        surface.parent = node
        surface.days_after_sow = date.dayofyear - surface.sowing_day
        _ = surface.calc_crop_cover()
        self.assertEqual(0.3, surface.crop_factor)
        self.assertEqual(0.3, surface.et0_coefficient)

        # These two numbers from the interpolation between
        # doy-harvest_sow_calendar and crop/ground_cover_stages
        self.assertEqual(0.17647058823529413, surface.crop_cover)
        self.assertEqual(0.058823529411764705, surface.ground_cover)

    def test_adjust_vqip(self):
        constants.set_default_pollutants()
        surface = GrowingSurface()
        vqip = surface.empty_vqip()
        vqip["nitrate"] = 0.5
        vqip["ammonia"] = 0.75
        vqip["org-nitrogen"] = 1.25
        vqip["phosphate"] = 1.2
        vqip["org-phosphorus"] = 0.3
        dep_ = {"N": 5, "P": 3}
        in_ = {"N": 3, "P": 2}

        d1 = surface.empty_vqip()
        d1["nitrate"] = 0.5 * 3 / 5
        d1["ammonia"] = 0.75 * 3 / 5
        d1["org-nitrogen"] = 1.25 * 3 / 5
        d1["phosphate"] = 1.2 * 2 / 3
        d1["org-phosphorus"] = 0.3 * 2 / 3

        r1 = surface.adjust_vqip_to_liquid(vqip, dep_, in_)
        self.assertDictAlmostEqual(d1, r1, 15)

    def test_dry_grow_dep(self):
        constants.set_default_pollutants()
        surface = GrowingSurface()
        vqip = surface.empty_vqip()
        vqip["nitrate"] = 0.5
        vqip["ammonia"] = 0.75
        vqip["phosphate"] = 1.2
        vqip_ = surface.dry_deposition_to_tank(vqip)

        d1 = surface.empty_vqip()
        d1["nitrate"] = 0.45
        d1["ammonia"] = 0.675
        d1["phosphate"] = 0
        self.assertDictAlmostEqual(d1, vqip_)
        n1 = {"N": 0, "P": 1.2}
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.adsorbed_inorganic_pool.storage
        )

        n2 = {"N": (0.5 + 0.75) * surface.nutrient_pool.fraction_dry_n_to_fast, "P": 0}
        self.assertDictAlmostEqual(n2, surface.nutrient_pool.fast_pool.storage)

        n3 = {
            "N": (0.5 + 0.75)
            * surface.nutrient_pool.fraction_dry_n_to_dissolved_inorganic,
            "P": 0,
        }
        self.assertDictAlmostEqual(
            n3, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

    def test_wet_grow_dep(self):
        constants.set_default_pollutants()
        surface = GrowingSurface()
        vqip = surface.empty_vqip()
        vqip["nitrate"] = 0.5
        vqip["ammonia"] = 0.75
        vqip["phosphate"] = 1.2
        vqip_ = surface.wet_deposition_to_tank(vqip)

        d1 = surface.empty_vqip()
        d1["nitrate"] = 0.5
        d1["ammonia"] = 0.75
        d1["phosphate"] = 1.2
        self.assertDictAlmostEqual(d1, vqip_)

        n1 = {"N": (0.5 + 0.75), "P": 1.2}
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

    def test_fertiliser(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        input_data = {
            ("nhx-fertiliser", 1): 5,
            ("noy-fertiliser", 1): 2,
            ("srp-fertiliser", 1): 3,
        }
        surface.data_input_dict = input_data
        node = Node(name="")
        node.monthyear = 1
        surface.parent = node

        (r1, r2) = surface.fertiliser()

        d1 = surface.empty_vqip()

        self.assertDictAlmostEqual(d1, r2)

        d1["phosphate"] = 3 * 1.5
        d1["nitrate"] = 2 * 1.5
        d1["ammonia"] = 5 * 1.5
        self.assertDictAlmostEqual(d1, r1)

        n1 = {"N": 4.1 + (2 + 5) * 1.5, "P": 11 + 3 * 1.5}
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

    def test_manure(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        input_data = {("nhx-manure", 1): 5, ("noy-manure", 1): 2, ("srp-manure", 1): 3}
        surface.data_input_dict = input_data
        node = Node(name="")
        node.monthyear = 1
        surface.parent = node

        (r1, r2) = surface.manure()

        d1 = surface.empty_vqip()

        self.assertDictAlmostEqual(d1, r2)

        d1["phosphate"] = (
            3 * 1.5 * surface.nutrient_pool.fraction_manure_to_dissolved_inorganic["P"]
        )
        d1["nitrate"] = (
            2 * 1.5 * surface.nutrient_pool.fraction_manure_to_dissolved_inorganic["N"]
        )
        d1["ammonia"] = (
            5 * 1.5 * surface.nutrient_pool.fraction_manure_to_dissolved_inorganic["N"]
        )
        self.assertDictAlmostEqual(d1, r1)

        n1 = {
            "N": 4.1
            + (2 + 5)
            * 1.5
            * surface.nutrient_pool.fraction_manure_to_dissolved_inorganic["N"],
            "P": 11
            + 3
            * 1.5
            * surface.nutrient_pool.fraction_manure_to_dissolved_inorganic["P"],
        }
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

        n2 = {
            "N": 2 + (2 + 5) * 1.5 * surface.nutrient_pool.fraction_manure_to_fast["N"],
            "P": 4 + 3 * 1.5 * surface.nutrient_pool.fraction_manure_to_fast["P"],
        }
        self.assertDictAlmostEqual(n2, surface.nutrient_pool.fast_pool.storage)

    def calc_temp_dep(self):
        """"""
        constants.set_simple_pollutants()
        surface = GrowingSurface(
            initial_storage={"volume": 0, "phosphate": 0, "temperature": -1}
        )
        surface.calc_temperature_dependence_factor()
        self.assertEqual(0, surface.nutrient_pool.temperature_dependence_factor)

        surface.storage["temperature"] = 2.5
        surface.calc_temperature_dependence_factor()
        self.assertEqual(2.5 / 5, surface.nutrient_pool.temperature_dependence_factor)

        surface.storage["temperature"] = 7.5
        surface.calc_temperature_dependence_factor()
        self.assertEqual(
            2 ** ((7.5 - 20) / 10), surface.nutrient_pool.temperature_dependence_factor
        )

    def calc_mois_dep(self):
        """"""
        constants.set_simple_pollutants()
        surface = GrowingSurface(
            initial_storage={"volume": 0.05, "phosphate": 0, "temperature": 0},
            rooting_depth=1,
            area=1,
            wilting_point=0.1,
            field_capacity=0.2,
        )
        surface.calc_soil_moisture_dependence_factor()
        self.assertEqual(0, surface.nutrient_pool.soil_moisture_dependence_factor)

        surface.storage["volume"] = 0.15
        surface.calc_soil_moisture_dependence_factor()
        v1 = ((0.2 - 0.15) / (surface.thetaupp * 1)) ** surface.thetapow
        v1 = (1 - surface.satact) * v1 + surface.satact
        v2 = ((0.15 - 0.1) / (surface.thetalow * 1)) ** surface.thetapow

        v = min(1, v1, v2)
        self.assertEqual(v, surface.nutrient_pool.soil_moisture_dependence_factor)

        surface.storage["volume"] = 0.25
        surface.calc_soil_moisture_dependence_factor()
        self.assertEqual(
            surface.satact, surface.nutrient_pool.soil_moisture_dependence_factor
        )

    def test_soil_pool(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        surface.calc_temperature_dependence_factor()
        surface.calc_soil_moisture_dependence_factor()

        nut_p = surface.nutrient_pool
        cf = nut_p.temperature_dependence_factor * nut_p.soil_moisture_dependence_factor
        (r1, r2) = surface.soil_pool_transformation()

        fast_ = {"N": isoil["org-nitrogen"], "P": isoil["org-phosphorus"]}  # original
        dissolved_inorganic_ = {
            "N": ivol["nitrate"] + ivol["nitrite"] + ivol["ammonia"],
            "P": ivol["phosphate"],
        }

        miner = {
            "N": nut_p.minfpar["N"] * fast_["N"] * cf,
            "P": nut_p.minfpar["P"] * fast_["P"] * cf,
        }

        fast_ = {"N": fast_["N"] - miner["N"], "P": fast_["P"] - miner["P"]}
        dissolved_inorganic_ = {
            "N": dissolved_inorganic_["N"] + miner["N"],
            "P": dissolved_inorganic_["P"] + miner["P"],
        }

        disso = {
            "N": nut_p.disfpar["N"] * fast_["N"] * cf,
            "P": nut_p.disfpar["P"] * fast_["P"] * cf,
        }

        fast_ = {"N": fast_["N"] - disso["N"], "P": fast_["P"] - disso["P"]}

        immob = {
            "N": nut_p.immobdpar["N"] * dissolved_inorganic_["N"] * cf,
            "P": nut_p.immobdpar["P"] * dissolved_inorganic_["P"] * cf,
        }

        d1 = surface.empty_vqip()
        d2 = surface.empty_vqip()
        if miner["P"] - immob["P"] > 0:
            d1["phosphate"] = miner["P"] - immob["P"]
        else:
            d2["phosphate"] = immob["P"] - miner["P"]
        if miner["N"] - immob["N"] > 0:
            d1["nitrate"] = (
                (miner["N"] - immob["N"])
                * ivol["nitrate"]
                / (ivol["nitrate"] + ivol["ammonia"])
            )
            d1["ammonia"] = (
                (miner["N"] - immob["N"])
                * ivol["ammonia"]
                / (ivol["nitrate"] + ivol["ammonia"])
            )
        else:
            d2["nitrate"] = (
                (immob["N"] - miner["N"])
                * ivol["nitrate"]
                / (ivol["nitrate"] + ivol["ammonia"])
            )
            d2["ammonia"] = (
                (immob["N"] - miner["N"])
                * ivol["ammonia"]
                / (ivol["nitrate"] + ivol["ammonia"])
            )
        d1["org-phosphorus"] = disso["P"]
        d1["org-nitrogen"] = disso["N"]

        self.assertDictAlmostEqual(d1, r1, 15)
        self.assertDictAlmostEqual(d2, r2, 15)

    def test_crop_uptake(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        date = to_datetime("2000-05-01")
        node = Node(name="")
        node.t = date
        surface.parent = node
        surface.days_after_sow = date.dayofyear - surface.sowing_day
        _ = surface.calc_crop_cover()

        (r1, r2) = surface.calc_crop_uptake()

        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(r1, d1)
        d1["nitrate"] = 4.7281041425055e-05
        d1["phosphate"] = 6.5668113090354e-06
        self.assertDictAlmostEqual(d1, r2)

        d2 = surface.copy_vqip(ivol)
        d2["nitrate"] -= d1["nitrate"]
        d2["phosphate"] -= d1["phosphate"]
        self.assertDictAlmostEqual(d2, surface.storage)

        n1 = {
            "N": ivol["nitrate"] + ivol["ammonia"] + ivol["nitrite"] - d1["nitrate"],
            "P": ivol["phosphate"] - d1["phosphate"],
        }
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

    def test_erosion1(self):
        # High rain
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()

        date = to_datetime("2000-05-01")
        inputs = {
            ("precipitation", date): 1.5,
            ("et0", date): 0.01,
            ("temperature", date): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = date
        surface.parent = node
        _ = surface.ihacres()
        (r1, r2) = surface.erosion()
        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(d1, r2)
        d1["phosphate"] = 0.0019497135091285024
        d1["solids"] = 1.0560948174446056
        self.assertDictAlmostEqual(d1, r1)

    def test_erosion2(self):
        # Med rain
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()

        date = to_datetime("2000-05-01")
        inputs = {
            ("precipitation", date): 0.1,
            ("et0", date): 0.01,
            ("temperature", date): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = date
        surface.parent = node
        _ = surface.ihacres()
        (r1, r2) = surface.erosion()
        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(d1, r2)
        d1["phosphate"] = 1.0244298083948e-06
        d1["solids"] = 0.0005548994795471758
        self.assertDictAlmostEqual(d1, r1)

    def test_erosion3(self):
        # low rain
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()

        date = to_datetime("2000-05-01")
        inputs = {
            ("precipitation", date): 0.005,
            ("et0", date): 0.01,
            ("temperature", date): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = date
        surface.parent = node
        _ = surface.ihacres()
        (r1, r2) = surface.erosion()
        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(d1, r2)
        d1["phosphate"] = 8.3285749289e-09
        d1["solids"] = 1.7605117735786e-06
        self.assertDictAlmostEqual(d1, r1)

    def test_denitrification(self):
        # low rain
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        surface.calc_temperature_dependence_factor()
        (r1, r2) = surface.denitrification()
        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(d1, r1)
        d1["nitrate"] = 0.03295446191742672
        self.assertDictAlmostEqual(d1, r2)

    def test_desorption(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()
        surface.nutrient_pool.adsorbed_inorganic_pool.storage["P"] = 1e6
        (r1, r2) = surface.adsorption()
        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(d1, r2)
        d1["phosphate"] = 29534.602916697728
        self.assertDictAlmostEqual(d1, r1)
        n1 = {"N": 0.9, "P": 970465.3970833023}
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.adsorbed_inorganic_pool.storage
        )
        n2 = {"N": 4.1, "P": 29545.602916697728}
        self.assertDictAlmostEqual(
            n2, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

    def test_adsorption(self):
        constants.set_default_pollutants()
        surface, ivol, isoil = self.create_growing_surface()

        input_data = {
            ("nhx-fertiliser", 1): 0,
            ("noy-fertiliser", 1): 0,
            ("srp-fertiliser", 1): 1000,
        }
        surface.data_input_dict = input_data
        node = Node(name="")
        node.monthyear = 1
        surface.parent = node

        surface.fertiliser()

        (r1, r2) = surface.adsorption()
        d1 = surface.empty_vqip()
        self.assertDictAlmostEqual(d1, r1)
        d1["phosphate"] = 1.5761692429741743
        self.assertDictAlmostEqual(d1, r2)
        n1 = {"N": 0.9, "P": 2.7761692429741744}
        self.assertDictAlmostEqual(
            n1, surface.nutrient_pool.adsorbed_inorganic_pool.storage
        )
        n2 = {"N": 4.1, "P": 1509.4238307570258}
        self.assertDictAlmostEqual(
            n2, surface.nutrient_pool.dissolved_inorganic_pool.storage
        )

    def test_irrigate(self):
        constants.set_default_pollutants()

        date = to_datetime("2000-05-01")
        inputs = {
            ("precipitation", date): 0.005,
            ("et0", date): 0.01,
            ("temperature", date): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = date

        initial_vol = node.empty_vqip()
        initial_vol["phosphate"] = 11
        initial_vol["nitrate"] = 2.5
        initial_vol["nitrite"] = 1.5
        initial_vol["ammonia"] = 0.1
        initial_vol["org-nitrogen"] = 0.2
        initial_vol["org-phosphorus"] = 3
        initial_vol["volume"] = 0.3
        initial_vol["temperature"] = 11

        initial_soil = {
            "phosphate": 1.2,
            "ammonia": 0.2,
            "nitrate": 0.3,
            "nitrite": 0.4,
            "org-nitrogen": 2,
            "org-phosphorus": 4,
        }

        crop_factor_stages = [0.0, 0.0, 0.3, 0.3, 1.2, 1.2, 0.325, 0.0, 0.0]
        crop_factor_stage_dates = [0, 90, 91, 121, 161, 213, 244, 245, 366]
        sowing_day = 91
        harvest_day = 244
        ET_depletion_factor = 0.55

        surface = IrrigationSurface(
            rooting_depth=0.5,
            area=1.5,
            initial_storage=initial_vol,
            initial_soil_storage=initial_soil,
            crop_factor_stages=crop_factor_stages,
            crop_factor_stage_dates=crop_factor_stage_dates,
            sowing_day=sowing_day,
            harvest_day=harvest_day,
            ET_depletion_factor=ET_depletion_factor,
            wilting_point=0.1,
            field_capacity=0.2,
            total_porosity=0.4,
            irrigation_coefficient=0.8,
            parent=node,
        )
        surface.days_after_sow = date.dayofyear - surface.sowing_day
        _ = surface.ihacres()

        reservoir = Reservoir(name="", capacity=50, initial_storage=40)
        arc = Arc(in_port=reservoir, out_port=node, name="")
        surface.irrigate()
        self.assertEqual(0.006, arc.flow_in)

    def test_garden(self):
        constants.set_simple_pollutants()

        date = to_datetime("2000-05-01")
        inputs = {
            ("precipitation", date): 0.0025,
            ("et0", date): 0.01,
            ("temperature", date): 10,
        }

        node = Node(name="", data_input_dict=inputs)
        node.t = date

        surface = GardenSurface(
            rooting_depth=0.5,
            area=1.5,
            wilting_point=0.1,
            field_capacity=0.2,
            initial_storage=0.2 * 0.5 * 1.5,
            parent=node,
        )

        _ = surface.ihacres()

        reply = surface.calculate_irrigation_demand()
        d1 = {"phosphate": 0, "temperature": 0, "volume": 0.0075 * 1.5}
        self.assertDictAlmostEqual(d1, reply)

        d2 = {
            "phosphate": 0,
            "temperature": 0,
            "volume": 0.2 * 0.5 * 1.5 - 0.0075 * 1.5,
        }
        self.assertDictAlmostEqual(d2, surface.storage, 16)

        reply = surface.receive_irrigation_demand(d1)
        self.assertDictAlmostEqual(surface.empty_vqip(), reply)

        d3 = {"phosphate": 0, "temperature": 0, "volume": 0.2 * 0.5 * 1.5}
        self.assertDictAlmostEqual(d3, surface.storage, 16)


if __name__ == "__main__":
    unittest.main()
