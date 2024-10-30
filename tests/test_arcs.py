# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.arcs.arcs import AltQueueArc, Arc, DecayArc, DecayArcAlt, QueueArc
from wsimod.core import constants
from wsimod.nodes.nodes import Node
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

    def test_arc_mb(self):
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 0, "phosphate": 0, "temperature": 0}
        d3 = {"volume": 20, "phosphate": 0.0002, "temperature": 15}
        d4 = {"volume": 10, "phosphate": 0, "temperature": 0}
        d5 = {"volume": 5, "phosphate": 10, "temperature": 10}
        node1 = Node(name="1")
        node2 = Waste(name="2")

        arc1 = Arc(in_port=node1, out_port=node2, name="arc1", capacity=10)

        reply = arc1.send_push_check()
        self.assertDictAlmostEqual(d4, reply, 16)

        reply = arc1.send_push_check(d5)
        self.assertDictAlmostEqual(d5, reply, 16)

        arc1.send_push_request(d1)

        in_, ds_, out_ = arc1.arc_mass_balance()

        self.assertDictAlmostEqual(d1, in_, 16)
        self.assertDictAlmostEqual(d2, ds_, 16)
        self.assertDictAlmostEqual(d1, out_, 16)

        reply = arc1.send_push_request(d1)
        self.assertDictAlmostEqual(d1, reply, 16)

        reply = arc1.send_push_request(d1, force=True)
        in_, ds_, out_ = arc1.arc_mass_balance()
        self.assertDictAlmostEqual(d3, in_, 16)

    def test_arc_pull(self):
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 15}
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

        reply = arc1.send_pull_check()
        self.assertDictAlmostEqual(d1, reply, 16)

        reply = arc1.send_pull_check({"volume": 5})
        self.assertDictAlmostEqual(d2, reply, 16)

        reply = arc1.send_pull_request({"volume": 5})
        self.assertDictAlmostEqual(d2, reply, 16)

        reply = arc1.send_pull_request({"volume": 10})
        self.assertDictAlmostEqual(d2, reply, 16)

    def test_enter_arcq(self):
        node1 = Node(name="1")
        node2 = Waste(name="2")

        arc1 = QueueArc(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
        )
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}

        request = arc1.enter_arc({"vqip": d1, "time": 1}, "pull", "hi")
        self.assertEqual(5, request["average_flow"])
        self.assertEqual(5, arc1.flow_in)
        self.assertEqual("pull", request["direction"])
        self.assertEqual("hi", request["tag"])
        self.assertDictAlmostEqual(d1, request["vqip"])
        self.assertDictAlmostEqual(d1, arc1.vqip_in)

    def test_enter_q_arcq(self):
        node1 = Node(name="1")
        node2 = Waste(name="2")

        arc1 = QueueArc(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
        )
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        req = {"vqip": d1, "time": 1}
        arc1.enter_queue(req, direction="pull", tag="hi")

        self.assertEqual(5, arc1.queue[0]["average_flow"])
        self.assertEqual(5, arc1.flow_in)
        self.assertEqual("pull", arc1.queue[0]["direction"])
        self.assertEqual("hi", arc1.queue[0]["tag"])
        self.assertDictAlmostEqual(d1, arc1.queue[0]["vqip"])
        self.assertDictAlmostEqual(d1, arc1.vqip_in)

    def test_queue_arc_push(self):
        node1 = Node(name="1")
        node2 = Waste(name="2")

        arc1 = QueueArc(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
            number_of_timesteps=1,
        )

        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}

        arc1.send_push_request(d1)

        self.assertDictAlmostEqual(d1, arc1.vqip_in)
        self.assertDictAlmostEqual(d1, arc1.queue[0]["vqip"])

        arc1.end_timestep()

        d2 = {"volume": 0, "phosphate": 0, "temperature": 0}
        self.assertDictAlmostEqual(d2, arc1.vqip_in)
        self.assertDictAlmostEqual(d1, arc1.queue[0]["vqip"])

        _ = arc1.update_queue(direction="push")
        self.assertDictAlmostEqual(d1, arc1.vqip_out)

    def test_queue_arc_pull(self):
        node1 = Node(name="1")
        node2 = Storage(name="2", capacity=10, initial_storage=5)

        arc1 = QueueArc(
            in_port=node2,
            out_port=node1,
            name="arc1",
            capacity=10,
            number_of_timesteps=1,
        )

        d1 = {"volume": 2.5}
        d2 = {"volume": 0, "phosphate": 0, "temperature": 0}

        reply = arc1.send_pull_request(d1)

        self.assertDictAlmostEqual(d2, reply)

        d2["volume"] = 2.5

        self.assertDictAlmostEqual(d2, arc1.queue[0]["vqip"])
        self.assertDictAlmostEqual(d2, arc1.vqip_in)

        arc1.end_timestep()

        self.assertDictAlmostEqual(d2, arc1.queue[0]["vqip"])

        _ = arc1.update_queue(direction="pull")
        self.assertDictAlmostEqual(d2, arc1.vqip_out)

    def test_altqueue_arc_sum(self):
        node1 = Node(name="1")
        node2 = Waste(name="2")

        arc1 = AltQueueArc(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
            number_of_timesteps=1,
        )

        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}

        arc1.queue[1] = d1
        arc1.queue[0] = d1

        d2 = {"volume": 20, "phosphate": 0.0002, "temperature": 15}

        self.assertDictAlmostEqual(d2, arc1.alt_queue_arc_sum())

    def test_enter_q_arcalt(self):
        node1 = Node(name="1")
        node2 = Waste(name="2")

        arc1 = AltQueueArc(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
        )
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        req = {"vqip": d1, "time": 1}
        arc1.enter_queue(req, direction="push", tag="hi")

        self.assertEqual(5, arc1.flow_in)
        self.assertDictAlmostEqual(d1, arc1.queue[1])
        self.assertDictAlmostEqual(d1, arc1.vqip_in)

        arc1.end_timestep()

        self.assertEqual(0, arc1.flow_in)
        self.assertDictAlmostEqual(d1, arc1.queue[0])

        d2 = {"volume": 0, "phosphate": 0, "temperature": 0}
        self.assertDictAlmostEqual(d2, arc1.vqip_in)

        arc1.update_queue()
        self.assertDictAlmostEqual(d2, arc1.queue[0])
        self.assertDictAlmostEqual(d1, arc1.vqip_out)

    def test_decay_arc(self):
        node1 = Node(name="1", data_input_dict={("temperature", 1): 10})
        node2 = Waste(name="2")
        node1.t = 1
        arc1 = DecayArc(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
            decays={"phosphate": {"constant": 0.005, "exponent": 1.005}},
            number_of_timesteps=1,
        )
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}

        arc1.send_push_request(d1)
        self.assertDictAlmostEqual(d1, arc1.vqip_in)
        d1["phosphate"] = d1["phosphate"] * (1 - 0.005 * 1.005 ** (10 - 20))
        self.assertDictAlmostEqual(d1, arc1.queue[0]["vqip"])

        arc1.end_timestep()
        d1["phosphate"] = d1["phosphate"] * (1 - 0.005 * 1.005 ** (10 - 20))
        self.assertDictAlmostEqual(d1, arc1.queue[0]["vqip"])

    def test_decay_arc_alt(self):
        node1 = Node(name="1", data_input_dict={("temperature", 1): 10})
        node2 = Waste(name="2")
        node1.t = 1
        arc1 = DecayArcAlt(
            in_port=node1,
            out_port=node2,
            name="arc1",
            capacity=10,
            number_of_timesteps=1,
            decays={"phosphate": {"constant": 0.005, "exponent": 1.005}},
        )
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}

        arc1.send_push_request(d1)
        self.assertDictAlmostEqual(d1, arc1.vqip_in)
        d1["phosphate"] = d1["phosphate"] * (1 - 0.005 * 1.005 ** (10 - 20))
        self.assertDictAlmostEqual(d1, arc1.queue[1])

        arc1.end_timestep()
        d1["phosphate"] = d1["phosphate"] * (1 - 0.005 * 1.005 ** (10 - 20))
        self.assertDictAlmostEqual(d1, arc1.queue[0])

    def test_overrides_simple_arc(self):
        model = self.get_simple_model1()
        arc1 = model[5]
        arc1.apply_overrides({"capacity": 3.1, "preference": 0.65})
        self.assertEqual(3.1, arc1.capacity)
        self.assertEqual(0.65, arc1.preference)

        # Test incorrect label
        overrides = {"capacity": 3.1, "preferenceasd": 0.65}
        arc1.apply_overrides(overrides)
        self.assertEqual({"preferenceasd": 0.65}, overrides)


if __name__ == "__main__":
    unittest.main()
