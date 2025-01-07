# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.nodes import Node
from wsimod.nodes.storage import Storage
from wsimod.nodes.waste import Waste
import os
import pandas as pd


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

    def get_simple_model1(self):
        """

        Returns:

        """
        node1 = Storage(name="1", capacity=20)
        node2 = Waste(name="2")
        node3 = Node(name="3")
        node4 = Node(name="4")
        node5 = Waste(name="5")

        arc1 = Arc(in_port=node1, out_port=node2, name="arc1")

        arc2 = Arc(in_port=node3, out_port=node1, name="arc2")

        arc3 = Arc(in_port=node4, out_port=node1, name="arc3")

        arc4 = Arc(in_port=node1, out_port=node5, preference=0.5, name="arc4")

        return node1, node2, node3, node4, node5, arc1, arc2, arc3, arc4

    def get_simple_model2(self):
        """

        Returns:

        """
        node1 = Storage(
            name="1",
            capacity=20,
            initial_storage={"volume": 10, "phosphate": 0.5, "temperature": 15},
        )
        node2 = Storage(
            name="2",
            capacity=30,
            initial_storage={"volume": 20, "phosphate": 0.2, "temperature": 12},
        )
        node3 = Node(name="3")

        node4 = Node(name="4")
        arc1 = Arc(in_port=node1, out_port=node3, name="arc1", preference=0.75)

        arc2 = Arc(in_port=node2, out_port=node3, name="arc2", preference=1.25)

        arc3 = Arc(in_port=node4, out_port=node1, name="arc3", preference=0.5)

        arc4 = Arc(in_port=node4, out_port=node2, name="arc4", preference=10)

        return node1, node2, node3, node4, arc1, arc2, arc3, arc4

    def test_inoutmb(self):
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}

        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}

        d3 = {
            "volume": 15,
            "phosphate": 0.00015,
            "temperature": (10 * 15 + 5 * 10) / 15,
        }

        d4 = {"volume": 0, "phosphate": 0, "temperature": 0}

        d5 = {"volume": 15, "phosphate": 0.00015, "temperature": 0}
        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        arc2.send_push_request(d1)
        arc3.send_push_request(d2)

        in_, ds_, out_ = node1.node_mass_balance()

        self.assertDictAlmostEqual(d3, in_)
        self.assertDictAlmostEqual(d5, ds_)
        self.assertDictAlmostEqual(d4, out_)

        node1.distribute()

        in_ = node1.total_in()
        self.assertDictAlmostEqual(d3, in_)

        out_ = node1.total_out()
        self.assertDictAlmostEqual(d3, out_)

    def test_push(self):
        d1 = {"volume": 25, "phosphate": 0.0001, "temperature": 15}

        d2 = {"volume": 5, "phosphate": 0.00002, "temperature": 15}

        d3 = {"volume": 20, "phosphate": 0, "temperature": 0}

        d4 = {"volume": 10, "phosphate": 0.01, "temperature": 10}

        d5 = {"volume": 10, "phosphate": 0, "temperature": 0}
        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        reply = node1.push_check()
        self.assertDictAlmostEqual(d3, reply)

        reply = node1.push_check(d4)
        self.assertDictAlmostEqual(d5, reply)

        reply = node1.push_set(d1)
        self.assertDictAlmostEqual(d2, reply)

    def test_pull(self):
        d1 = {"volume": 15, "phosphate": 0.0001, "temperature": 15}

        d2 = {"volume": 25}

        d3 = {"volume": 10}

        d4 = {"volume": 10, "phosphate": 0.0002 / 3, "temperature": 15}
        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        node1.push_set(d1)

        reply = node1.pull_check()
        self.assertDictAlmostEqual(d1, reply)

        reply = node1.pull_check(d3)
        self.assertDictAlmostEqual(d4, reply)

        reply = node1.pull_set(d2)
        self.assertDictAlmostEqual(d1, reply)

    def test_direction(self):
        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        f, outarcs = node1.get_direction_arcs("push")

        self.assertEqual("send_push_check", f)
        self.assertEqual(set([arc1, arc4]), set(outarcs))

        f, inarcs = node1.get_direction_arcs("pull")

        self.assertEqual("send_pull_check", f)
        self.assertEqual(set([arc3, arc2]), set(inarcs))

    def test_connected(self):
        d1 = {"volume": 15, "phosphate": 0.0001, "temperature": 15}

        connected_ = {
            "avail": 15,
            "priority": 7.5,
            "allocation": {"arc4": 7.5},
            "capacity": {"arc4": 15},
        }

        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        node1.push_set(d1)

        connected = node5.get_connected("pull")

        self.assertDictEqual(connected_, connected)

    def test_handler_push(self):
        d1 = {"volume": 25, "phosphate": 0.0001, "temperature": 15}

        d2 = {"volume": 5, "phosphate": 0.00002, "temperature": 15}

        d3 = {"volume": 20, "phosphate": 0, "temperature": 0}

        d4 = {"volume": 10, "phosphate": 0.01, "temperature": 10}

        d5 = {"volume": 10, "phosphate": 0, "temperature": 0}
        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        reply = node1.query_handler(node1.push_check_handler, None, "default")
        self.assertDictAlmostEqual(d3, reply)

        reply = node1.query_handler(node1.push_check_handler, d4, "default")
        self.assertDictAlmostEqual(d5, reply)

        reply = node1.query_handler(node1.push_set_handler, d1, "default")
        self.assertDictAlmostEqual(d2, reply)

    def test_handler_pull(self):
        d1 = {"volume": 15, "phosphate": 0.0001, "temperature": 15}

        d2 = {"volume": 25}

        d3 = {"volume": 10}

        d4 = {"volume": 10, "phosphate": 0.0002 / 3, "temperature": 15}
        (
            node1,
            node2,
            node3,
            node4,
            node5,
            arc1,
            arc2,
            arc3,
            arc4,
        ) = self.get_simple_model1()

        node1.push_set(d1)

        reply = node1.query_handler(node1.pull_check_handler, None, "default")
        self.assertDictAlmostEqual(d1, reply)

        reply = node1.query_handler(node1.pull_check_handler, d3, "default")
        self.assertDictAlmostEqual(d4, reply)

        reply = node1.query_handler(node1.pull_set_handler, d2, "default")
        self.assertDictAlmostEqual(d1, reply)

    def test_pull_distributed(self):
        d1 = {"volume": 10}

        amount_from_1 = 10 * 10 * 0.75 / (10 * 0.75 + 20 * 1.25)
        amount_from_2 = 10 * 20 * 1.25 / (10 * 0.75 + 20 * 1.25)

        d2 = {
            "volume": 10,
            "phosphate": 0.5 * amount_from_1 / 10 + 0.2 * amount_from_2 / 20,
            "temperature": (15 * amount_from_1 + 12 * amount_from_2) / 10,
        }

        d3 = {
            "volume": amount_from_1,
            "phosphate": 0.5 * amount_from_1 / 10,
            "temperature": 15,
        }

        d4 = {
            "volume": amount_from_2,
            "phosphate": 0.2 * amount_from_2 / 20,
            "temperature": 12,
        }

        node1, node2, node3, node4, arc1, arc2, arc3, arc4 = self.get_simple_model2()

        reply = node3.pull_distributed(d1)
        self.assertDictAlmostEqual(d2, reply)
        self.assertDictAlmostEqual(d3, arc1.vqip_out)
        self.assertDictAlmostEqual(d4, arc2.vqip_out)

    def test_push_distributed(self):
        d1 = {"volume": 15, "phosphate": 0.01, "temperature": 12}

        d2 = {"volume": 0, "phosphate": 0, "temperature": 12}

        d3 = {"volume": 10, "phosphate": 0.01 * 2 / 3, "temperature": 12}

        d4 = {"volume": 5, "phosphate": 0.01 / 3, "temperature": 12}

        node1, node2, node3, node4, arc1, arc2, arc3, arc4 = self.get_simple_model2()
        reply = node4.push_distributed(d1)
        self.assertDictAlmostEqual(d2, reply)

        # Distributing is iterative so these won't be perfect
        self.assertDictAlmostEqual(d3, arc4.vqip_in, 14)
        self.assertDictAlmostEqual(d4, arc3.vqip_in, 14)

    def test_pull_check_basic(self):
        d1 = {"volume": 30, "phosphate": 0.7, "temperature": (15 * 10 + 12 * 20) / 30}

        d2 = {"volume": 10}

        d3 = {
            "volume": 10,
            "phosphate": 0.7 / 3,
            "temperature": (15 * 10 + 12 * 20) / 30,
        }

        node1, node2, node3, node4, arc1, arc2, arc3, arc4 = self.get_simple_model2()

        reply = node3.pull_check_basic()
        self.assertDictAlmostEqual(d1, reply)

        reply = node3.pull_check_basic(d2)
        self.assertDictAlmostEqual(d3, reply)

    def test_push_check_basic(self):
        d1 = {"volume": 20, "phosphate": 0.6, "temperature": 13.5}

        d2 = {"volume": 10, "phosphate": 0.1, "temperature": 17}

        d3 = {"volume": 10, "phosphate": 0.3, "temperature": 13.5}

        node1, node2, node3, node4, arc1, arc2, arc3, arc4 = self.get_simple_model2()
        reply = node4.push_check_basic()

        self.assertDictAlmostEqual(d1, reply)

        reply = node4.push_check_basic(d2)

        self.assertDictAlmostEqual(d3, reply)

    def test_deny(self):
        d1 = {"volume": 20, "phosphate": 0.6, "temperature": 13.5}

        d2 = {"volume": 0, "phosphate": 0, "temperature": 0}

        node = Node(name="")

        reply = node.pull_check_deny(d1)
        self.assertDictEqual(d2, reply)

        reply = node.pull_check_deny()
        self.assertDictEqual(d2, reply)

        reply = node.pull_set_deny(d1)
        self.assertDictEqual(d2, reply)

        reply = node.push_set_deny(d1)
        self.assertDictEqual(d1, reply)

        reply = node.push_check_deny(d1)
        self.assertDictEqual(d2, reply)

        reply = node.push_check_deny()
        self.assertDictEqual(d2, reply)

    def test_data_read(self):
        node = Node(name="", data_input_dict={("temperature", 1): 15})
        node.t = 1

        self.assertEqual(15, node.get_data_input("temperature"))

    def test_data_overrides(self):
        data_path = os.path.join(
            os.getcwd(),
            "docs",
            "demo",
            "data",
            "processed",
            "example_override_data.csv.gz",
        )
        input_data = pd.read_csv(data_path)

        overrides = {"filename": data_path}
        node = Node(name="")
        node.apply_overrides(overrides)
        node.t = list(node.data_input_dict.keys())[0][1]

        self.assertEqual(
            input_data.groupby("variable").get_group("temperature")["value"].iloc[0],
            node.get_data_input("temperature"),
        )
        # test runtime error
        self.assertRaises(RuntimeError, lambda: node.apply_overrides({"filename": 123}))


if __name__ == "__main__":
    unittest.main()
