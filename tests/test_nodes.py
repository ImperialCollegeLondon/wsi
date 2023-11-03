# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.nodes import (
    DecayQueueTank,
    DecayTank,
    Node,
    QueueTank,
    ResidenceTank,
    Tank,
)
from wsimod.nodes.storage import Storage
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

    def test_tank_ds(self):
        tank = Tank(
            capacity=10,
            initial_storage={"volume": 5, "phosphate": 0.4, "temperature": 10},
        )
        tank.end_timestep()

        d1 = {"volume": 2, "phosphate": 0.01, "temperature": 15}

        _ = tank.push_storage(d1)

        diff = tank.ds()

        d2 = {"volume": 2, "phosphate": 0.01, "temperature": 0}

        self.assertDictAlmostEqual(d2, diff, 16)

    def test_ponded(self):
        tank = Tank(
            capacity=10,
            initial_storage={"volume": 15, "phosphate": 0.4, "temperature": 10},
        )
        d1 = {"volume": 5, "phosphate": 0.4 / 3, "temperature": 10}
        reply = tank.pull_ponded()
        self.assertDictAlmostEqual(d1, reply)

    def test_tank_get_avail(self):
        d1 = {"volume": 5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1)

        reply = tank.get_avail()
        self.assertDictAlmostEqual(d1, reply)

        reply = tank.get_avail({"volume": 2.5})
        d2 = {"volume": 2.5, "phosphate": 0.2, "temperature": 10}
        self.assertDictAlmostEqual(d2, reply)

        reply = tank.get_avail({"volume": 10})
        self.assertDictAlmostEqual(d1, reply)

    def test_tank_get_excess(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1)

        d2 = {"volume": 2.5, "phosphate": 0.4 / 3, "temperature": 10}
        reply = tank.get_excess()
        self.assertDictAlmostEqual(d2, reply)

        d2 = {"volume": 1, "phosphate": 0.4 * 1 / 7.5, "temperature": 10}
        reply = tank.get_excess({"volume": 1})
        self.assertDictAlmostEqual(d2, reply)

    def test_tank_push_storage(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1)

        d2 = {"volume": 5, "phosphate": 0.4, "temperature": 15}

        d3 = {"volume": 2.5, "phosphate": 0.2, "temperature": 15}
        reply = tank.push_storage(d2)
        self.assertDictAlmostEqual(d3, reply)

        d4 = {"volume": 0, "phosphate": 0, "temperature": 0}
        reply = tank.push_storage(d2, force=True)
        self.assertDictAlmostEqual(d4, reply)

    def test_tank_pull_storage(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1)

        d2 = {"volume": 5, "phosphate": 0.4 * 5 / 7.5, "temperature": 10}

        reply = tank.pull_storage({"volume": 5})
        self.assertDictAlmostEqual(d2, reply)

        d3 = {"volume": 2.5, "phosphate": 0.4 * 2.5 / 7.5, "temperature": 10}

        reply = tank.pull_storage({"volume": 5})

        self.assertDictAlmostEqual(d3, reply, 15)

    def test_tank_pull_pollutants(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1)

        d2 = {"volume": 5, "phosphate": 0.1, "temperature": 10}

        reply = tank.pull_pollutants(d2)
        self.assertDictAlmostEqual(d2, reply)

        reply = tank.pull_pollutants(d2)
        d3 = {"volume": 2.5, "phosphate": 0.1, "temperature": 10}
        self.assertDictAlmostEqual(d3, reply, 15)

    def test_tank_head(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1, datum=5, area=2.5)

        reply = tank.get_head()
        self.assertEqual(8, reply)

        reply = tank.get_head(datum=-1)
        self.assertEqual(2, reply)

        reply = tank.get_head(non_head_storage=2)
        self.assertEqual(7.2, reply)

        reply = tank.get_head(non_head_storage=10)
        self.assertEqual(5, reply)

    def test_evap(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = Tank(capacity=10, initial_storage=d1)

        d2 = {"volume": 0, "phosphate": 0.4, "temperature": 10}

        reply = tank.evaporate(10)
        self.assertEqual(7.5, reply)
        self.assertDictAlmostEqual(d2, tank.storage)

    def test_residence_tank(self):
        d1 = {"volume": 7.5, "phosphate": 0.4, "temperature": 10}
        tank = ResidenceTank(residence_time=3, initial_storage=d1)

        d2 = {"volume": 2.5, "phosphate": 0.4 / 3, "temperature": 10}
        reply = tank.pull_outflow()
        self.assertDictAlmostEqual(d2, reply)

    def test_decay_tank(self):
        node = Node(name="", data_input_dict={("temperature", 1): 15})
        node.t = 1
        d1 = {"volume": 8, "phosphate": 0.4, "temperature": 10}

        tank = DecayTank(
            decays={"phosphate": {"constant": 0.001, "exponent": 1.005}},
            initial_storage=d1,
            parent=node,
        )
        _ = tank.pull_storage({"volume": 2})

        d3 = {"volume": -2, "phosphate": -0.1, "temperature": 0}

        diff = tank.decay_ds()
        self.assertDictAlmostEqual(d3, diff, 16)

        tank.end_timestep_decay()

        d2 = {
            "volume": 6,
            "phosphate": 0.3 - 0.3 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 10,
        }

        self.assertDictAlmostEqual(d2, tank.storage, 16)

        self.assertAlmostEqual(
            0.3 * 0.001 * 1.005 ** (15 - 20), tank.total_decayed["phosphate"]
        )

    def test_queue_push(self):
        d1 = {"volume": 5, "phosphate": 0.4, "temperature": 10}
        tank = QueueTank(number_of_timesteps=1, capacity=10, initial_storage=d1)

        d2 = {"volume": 1, "phosphate": 0.1, "temperature": 15}

        tank.push_storage(d2)

        d3 = {"volume": 6, "phosphate": 0.5, "temperature": (5 * 10 + 15) / 6}

        self.assertDictAlmostEqual(d3, tank.storage)
        self.assertDictAlmostEqual(d1, tank.active_storage)
        self.assertDictAlmostEqual(d2, tank.internal_arc.queue[1])

        tank.push_storage(d2, force=True)
        self.assertDictAlmostEqual(d3, tank.active_storage)

        tank.end_timestep()

        d4 = {"volume": 7, "phosphate": 0.6, "temperature": ((5 * 10) + (15 * 2)) / 7}
        self.assertDictAlmostEqual(d4, tank.active_storage)

    def test_queue_pull(self):
        d1 = {"volume": 5, "phosphate": 0.4, "temperature": 10}
        tank = QueueTank(number_of_timesteps=1, capacity=10, initial_storage=d1)
        d2 = {"volume": 1, "phosphate": 0.1, "temperature": 15}
        reply = tank.push_storage(d2)

        reply = tank.pull_storage({"volume": 6})
        self.assertDictAlmostEqual(d1, reply)
        tank.end_timestep()
        self.assertDictAlmostEqual(d2, tank.active_storage)

    def test_queue_pull_exact(self):
        d1 = {"volume": 5, "phosphate": 0.4, "temperature": 10}
        tank = QueueTank(number_of_timesteps=1, capacity=10, initial_storage=d1)
        d2 = {"volume": 1, "phosphate": 0.1, "temperature": 15}
        reply = tank.push_storage(d2)

        reply = tank.pull_storage_exact(
            {"volume": 6, "phosphate": 0.1, "temperature": 10}
        )

        d3 = {"volume": 5, "phosphate": 0.1, "temperature": 10}
        self.assertDictAlmostEqual(d3, reply)

        reply = tank.pull_storage_exact(
            {"volume": 0, "phosphate": 0.6, "temperature": 10}
        )
        d4 = {"volume": 0, "phosphate": 0.3, "temperature": 10}
        self.assertDictAlmostEqual(d4, reply, 16)

    def test_decay_queue(self):
        node = Node(name="", data_input_dict={("temperature", 1): 15})
        node.t = 1
        d1 = {"volume": 5, "phosphate": 0.4, "temperature": 10}
        tank = DecayQueueTank(
            number_of_timesteps=1,
            capacity=10,
            initial_storage=d1,
            decays={"phosphate": {"constant": 0.001, "exponent": 1.005}},
            parent=node,
        )

        d2 = {"volume": 1, "phosphate": 0.1, "temperature": 15}

        _ = tank.push_storage(d2)

        tank.end_timestep()

        d4 = {
            "volume": 6,
            "phosphate": 0.4 + 0.1 * (1 - 0.001 * 1.005 ** (15 - 20)),
            "temperature": ((5 * 10) + (15 * 1)) / 6,
        }
        self.assertDictAlmostEqual(d4, tank.storage, 15)


if __name__ == "__main__":
    unittest.main()
