"""Tests for the tanks module."""

import unittest
from unittest import TestCase

from wsimod.core import constants
from wsimod.nodes.nodes import Node
from wsimod.nodes.tanks import (
    DecayQueueTank,
    DecayTank,
    QueueTank,
    ResidenceTank,
    Tank,
)


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

    def test_overrides(self):
        # node - no need to test
        # tank
        tank = Tank(capacity=10, area=8, datum=4)
        tank.apply_overrides({"capacity": 3, "area": 2, "datum": 3.5})
        self.assertEqual(tank.capacity, 3)
        self.assertEqual(tank.area, 2)
        self.assertEqual(tank.datum, 3.5)
        # residence tank
        tank = ResidenceTank(capacity=10, area=8, datum=4, residence_time=8)
        tank.apply_overrides(
            {"capacity": 3, "area": 2, "datum": 3.5, "residence_time": 6}
        )
        self.assertEqual(tank.capacity, 3)
        self.assertEqual(tank.area, 2)
        self.assertEqual(tank.datum, 3.5)
        self.assertEqual(tank.residence_time, 6)
        # decay tank
        tank = DecayTank(
            capacity=10,
            area=8,
            datum=4,
            decays={"nitrate": {"constant": 0.001, "exponent": 1.005}},
        )
        tank.apply_overrides(
            {
                "capacity": 3,
                "area": 2,
                "datum": 3.5,
                "decays": {"phosphate": {"constant": 1.001, "exponent": 10.005}},
            }
        )
        self.assertEqual(tank.capacity, 3)
        self.assertEqual(tank.area, 2)
        self.assertEqual(tank.datum, 3.5)
        self.assertDictEqual(
            tank.decays,
            {
                "nitrate": {"constant": 0.001, "exponent": 1.005},
                "phosphate": {"constant": 1.001, "exponent": 10.005},
            },
        )
        # queue tank
        tank = QueueTank(capacity=10, area=8, datum=4, number_of_timesteps=8)
        tank.apply_overrides(
            {"capacity": 3, "area": 2, "datum": 3.5, "number_of_timesteps": 6}
        )
        self.assertEqual(tank.capacity, 3)
        self.assertEqual(tank.area, 2)
        self.assertEqual(tank.datum, 3.5)
        self.assertEqual(tank.number_of_timesteps, 6)
        self.assertEqual(tank.internal_arc.number_of_timesteps, 6)
        # decay queue tank
        tank = DecayQueueTank(
            capacity=10,
            area=8,
            datum=4,
            number_of_timesteps=8,
            decays={"phosphate": {"constant": 0.001, "exponent": 1.005}},
        )
        tank.apply_overrides(
            {
                "capacity": 3,
                "area": 2,
                "datum": 3.5,
                "number_of_timesteps": 6,
                "decays": {"phosphate": {"constant": 1.001, "exponent": 10.005}},
            }
        )
        self.assertEqual(tank.capacity, 3)
        self.assertEqual(tank.area, 2)
        self.assertEqual(tank.datum, 3.5)
        self.assertEqual(tank.number_of_timesteps, 6)
        self.assertEqual(tank.internal_arc.number_of_timesteps, 6)
        self.assertDictEqual(
            tank.internal_arc.decays,
            {"phosphate": {"constant": 1.001, "exponent": 10.005}},
        )


if __name__ == "__main__":
    unittest.main()
