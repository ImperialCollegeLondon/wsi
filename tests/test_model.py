# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""
import os
import pytest
import unittest
import tempfile
import yaml
from unittest import TestCase, mock

from wsimod.arcs.arcs import Arc
from wsimod.nodes.land import Land
from wsimod.nodes.nodes import Node
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.waste import Waste
from wsimod.orchestration.model import Model, to_datetime
import os


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

    def test_add_nodes(self):
        sewer = {"type_": "Sewer", "capacity": 0.04, "name": "my_sewer"}

        surface1 = {
            "type_": "ImperviousSurface",
            "surface": "urban",
            "area": 10,
            "pollutant_load": {"phosphate": 1e-7},
        }

        surface2 = {
            "type_": "PerviousSurface",
            "surface": "rural",
            "area": 100,
            "depth": 0.5,
            "pollutant_load": {"phosphate": 1e-7},
        }

        land = {"type_": "Land", "surfaces": [surface1, surface2], "name": "my_land"}
        my_model = Model()
        my_model.add_nodes([sewer, land])

        self.assertEqual(0.04, my_model.nodes["my_sewer"].sewer_tank.capacity)
        self.assertEqual(10, my_model.nodes["my_land"].get_surface("urban").area)

    def test_add_arcs(self):
        node = {"type_": "Node", "name": "my_node"}

        waste = {"type_": "Waste", "name": "my_waste"}

        surface1 = {
            "type_": "ImperviousSurface",
            "surface": "urban",
            "area": 10,
            "pollutant_load": {"phosphate": 1e-7},
        }

        surface2 = {
            "type_": "PerviousSurface",
            "surface": "rural",
            "area": 100,
            "depth": 0.5,
            "pollutant_load": {"phosphate": 1e-7},
        }

        land = {"type_": "Land", "surfaces": [surface1, surface2], "name": "my_land"}

        arc = {
            "in_port": "my_land",
            "out_port": "my_node",
            "name": "my_arc",
            "type_": "Arc",
            "capacity": 2,
            "preference": 2.5,
        }
        arc2 = {
            "in_port": "my_node",
            "out_port": "my_waste",
            "name": "my_arc2",
            "type_": "Arc",
        }
        my_model = Model()
        my_model.add_nodes([node, waste, land])
        my_model.add_arcs([arc, arc2])
        self.assertEqual(2, my_model.arcs["my_arc"].capacity)
        self.assertEqual(2.5, my_model.arcs["my_arc"].preference)

        self.assertEqual("my_land", my_model.arcs["my_arc"].in_port.name)
        self.assertEqual("my_node", my_model.arcs["my_arc"].out_port.name)

        self.assertEqual(
            0.4 * 0.5 * 100,
            my_model.arcs["my_arc"].in_port.get_surface("rural").capacity,
        )

    def test_add_ins_nodes(self):
        sewer = Sewer(**{"capacity": 0.04, "name": "my_sewer"})

        surface1 = {
            "type_": "ImperviousSurface",
            "surface": "urban",
            "area": 10,
            "pollutant_load": {"phosphate": 1e-7},
        }

        surface2 = {
            "type_": "PerviousSurface",
            "surface": "rural",
            "area": 100,
            "depth": 0.5,
            "pollutant_load": {"phosphate": 1e-7},
        }

        land = Land(**{"surfaces": [surface1, surface2], "name": "my_land"})
        my_model = Model()
        my_model.add_instantiated_nodes([sewer, land])

        self.assertEqual(0.04, my_model.nodes["my_sewer"].sewer_tank.capacity)
        self.assertEqual(10, my_model.nodes["my_land"].get_surface("urban").area)

    def test_add_ins_arcs(self):
        node = Node(**{"name": "my_node"})

        waste = Waste(**{"name": "my_waste"})

        surface1 = {
            "type_": "ImperviousSurface",
            "surface": "urban",
            "area": 10,
            "pollutant_load": {"phosphate": 1e-7},
        }

        surface2 = {
            "type_": "PerviousSurface",
            "surface": "rural",
            "area": 100,
            "depth": 0.5,
            "pollutant_load": {"phosphate": 1e-7},
        }

        land = Land(**{"surfaces": [surface1, surface2], "name": "my_land"})

        arc = Arc(
            **{
                "in_port": land,
                "out_port": node,
                "name": "my_arc",
                "capacity": 2,
                "preference": 2.5,
            }
        )
        arc2 = Arc(
            **{
                "in_port": node,
                "out_port": land,
                "name": "my_arc2",
            }
        )
        my_model = Model()
        my_model.add_instantiated_nodes([node, waste, land])
        my_model.add_instantiated_arcs([arc, arc2])
        self.assertEqual(2, my_model.arcs["my_arc"].capacity)
        self.assertEqual(2.5, my_model.arcs["my_arc"].preference)

        self.assertEqual("my_land", my_model.arcs["my_arc"].in_port.name)
        self.assertEqual("my_node", my_model.arcs["my_arc"].out_port.name)

        self.assertEqual(
            0.4 * 0.5 * 100,
            my_model.arcs["my_arc"].in_port.get_surface("rural").capacity,
        )

    def test_run(self):
        date = to_datetime("2000-01-01")
        dates = [date]
        land_inputs = {
            ("temperature", date): 10,
            ("precipitation", date): 0.01,
            ("et0", date): 0.002,
        }

        sewer = {"type_": "Sewer", "capacity": 0.05, "name": "my_sewer"}

        surface1 = {
            "type_": "ImperviousSurface",
            "surface": "urban",
            "area": 10,
            "pollutant_load": {"phosphate": 1e-7},
        }

        surface2 = {
            "type_": "PerviousSurface",
            "surface": "rural",
            "area": 100,
            "depth": 0.5,
            "pollutant_load": {"phosphate": 1e-7},
        }

        land = {
            "type_": "Land",
            "data_input_dict": land_inputs,
            "surfaces": [surface1, surface2],
            "name": "my_land",
        }

        gw = {
            "type_": "Groundwater",
            "area": 100,
            "capacity": 100,
            "name": "my_groundwater",
        }

        node = {"type_": "Node", "name": "my_river"}

        waste = {"type_": "Waste", "name": "my_outlet"}

        urban_drainage = {
            "type_": "Arc",
            "in_port": "my_land",
            "out_port": "my_sewer",
            "name": "urban_drainage",
        }

        percolation = {
            "type_": "Arc",
            "in_port": "my_land",
            "out_port": "my_groundwater",
            "name": "percolation",
        }

        runoff = {
            "type_": "Arc",
            "in_port": "my_land",
            "out_port": "my_river",
            "name": "runoff",
        }

        storm_outflow = {
            "type_": "Arc",
            "in_port": "my_sewer",
            "out_port": "my_river",
            "name": "storm_outflow",
        }

        baseflow = {
            "type_": "Arc",
            "in_port": "my_groundwater",
            "out_port": "my_river",
            "name": "baseflow",
        }

        catchment_outflow = {
            "type_": "Arc",
            "in_port": "my_river",
            "out_port": "my_outlet",
            "name": "catchment_outflow",
        }

        my_model = Model()
        my_model.dates = dates

        my_model.add_nodes([sewer, land, gw, node, waste])

        my_model.add_arcs(
            [
                urban_drainage,
                percolation,
                runoff,
                storm_outflow,
                baseflow,
                catchment_outflow,
            ]
        )

        flows, _, _, _ = my_model.run()
        self.assertEqual(0.05, flows[-1]["flow"])
        self.assertEqual(
            0.03, my_model.nodes["my_land"].get_surface("urban").storage["volume"]
        )

    def test_customise_orchestration(self):
        my_model = Model()
        my_model.load(
            os.path.join(os.getcwd(), "docs", "demo", "examples"),
            config_name="test_customise_orchestration_example.yaml",
        )
        revised_orchestration = [
            {"Groundwater": "infiltrate"},
            {"Sewer": "make_discharge"},
        ]
        self.assertListEqual(my_model.orchestration, revised_orchestration)

    def test_add_overrides_on_the_fly(self):
        overrides = {
            "nodes": {
                "my_groundwater": {
                    "name": "my_groundwater",
                    "type_": "Groundwater",
                    "infiltration_threshold": 200,
                    "infiltration_pct": 0.667,
                    "capacity": 1.43,
                    "area": 2.36,
                    "datum": 0.32,
                },
                "my_sewer": {
                    "name": "my_sewer",
                    "type_": "Sewer",
                    "pipe_timearea": {0: 0.5, 1: 0.5},
                },
            },
            "arcs": {
                "storm_outflow": {
                    "name": "storm_outflow",
                    "type_": "Arc",
                    "capacity": 0.5,
                }
            },
        }
        my_model = Model()
        my_model.load(
            os.path.join(os.getcwd(), "docs", "demo", "examples"),
            config_name="test_customise_orchestration_example.yaml",
        )
        my_model.add_overrides(overrides)

        self.assertEqual(200, my_model.nodes["my_groundwater"].infiltration_threshold)
        self.assertEqual(0.667, my_model.nodes["my_groundwater"].infiltration_pct)
        self.assertEqual(1.43, my_model.nodes["my_groundwater"].capacity)
        self.assertEqual(2.36, my_model.nodes["my_groundwater"].area)
        self.assertEqual(0.32, my_model.nodes["my_groundwater"].datum)
        self.assertEqual({0: 0.5, 1: 0.5}, my_model.nodes["my_sewer"].pipe_timearea)
        self.assertEqual(0.5, my_model.arcs["storm_outflow"].capacity)
        self.assertEqual(
            {
                "nodes": {"my_groundwater": {}, "my_sewer": {}},
                "arcs": {"storm_outflow": {}},
            },
            overrides,
        )

    def test_add_overrides_config(self):
        with open(
            os.path.join(
                os.getcwd(),
                "docs",
                "demo",
                "examples",
                "test_customise_orchestration_example.yaml",
            ),
            "r",
        ) as file:
            config = yaml.safe_load(file)
        config["overrides"] = {
            "nodes": {
                "my_groundwater": {
                    "name": "my_groundwater",
                    "type_": "Groundwater",
                    "infiltration_threshold": 200,
                    "infiltration_pct": 0.667,
                    "capacity": 1.43,
                    "area": 2.36,
                    "datum": 0.32,
                },
                "my_sewer": {
                    "name": "my_sewer",
                    "type_": "Sewer",
                    "pipe_timearea": {0: 0.5, 1: 0.5},
                },
            },
            "arcs": {
                "storm_outflow": {
                    "name": "storm_outflow",
                    "type_": "Arc",
                    "capacity": 0.5,
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp_path:
            with open(os.path.join(tmp_path, "temp.yaml"), "w") as file:
                yaml.dump(config, file)

            my_model = Model()
            my_model.load(tmp_path, config_name="temp.yaml")

        self.assertEqual(200, my_model.nodes["my_groundwater"].infiltration_threshold)
        self.assertEqual(0.667, my_model.nodes["my_groundwater"].infiltration_pct)
        self.assertEqual(1.43, my_model.nodes["my_groundwater"].capacity)
        self.assertEqual(2.36, my_model.nodes["my_groundwater"].area)
        self.assertEqual(0.32, my_model.nodes["my_groundwater"].datum)
        self.assertEqual({0: 0.5, 1: 0.5}, my_model.nodes["my_sewer"].pipe_timearea)
        self.assertEqual(0.5, my_model.arcs["storm_outflow"].capacity)


class TestLoadExtensionFiles:
    def test_load_extension_files_valid(self, tmp_path_factory):
        from wsimod.orchestration.model import load_extension_files

        with tmp_path_factory.mktemp("extensions") as tempdir:
            valid_file = os.path.join(tempdir, "valid_extension.py")
            with open(valid_file, "w") as f:
                f.write("def test_func(): pass")

            load_extension_files([valid_file])

    def test_load_extension_files_invalid_extension(self, tmp_path_factory):
        from wsimod.orchestration.model import load_extension_files

        with tmp_path_factory.mktemp("extensions") as tempdir:
            invalid_file = os.path.join(tempdir, "invalid_extension.txt")
            with open(invalid_file, "w") as f:
                f.write("This is a text file")

            with pytest.raises(ValueError, match="Only .py files are supported"):
                load_extension_files([invalid_file])

    def test_load_extension_files_nonexistent_file(self):
        from wsimod.orchestration.model import load_extension_files

        with pytest.raises(
            FileNotFoundError, match="File nonexistent_file.py does not exist"
        ):
            load_extension_files(["nonexistent_file.py"])

    def test_load_extension_files_import_error(self, tmp_path_factory):
        from wsimod.orchestration.model import load_extension_files

        with tmp_path_factory.mktemp("extensions") as tempdir:
            valid_file = os.path.join(tempdir, "valid_extension.py")
            with open(valid_file, "w") as f:
                f.write("raise ImportError")

            with pytest.raises(ImportError):
                load_extension_files([valid_file])


if __name__ == "__main__":
    unittest.main()
