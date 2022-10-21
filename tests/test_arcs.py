# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 10:35:51 2022

@author: Barney
"""

import pytest
# import pytest
import unittest
from unittest import TestCase

from wsimod.core import constants
from wsimod.nodes.nodes import Node, Tank, ResidenceTank, DecayTank, QueueTank, DecayQueueTank
from wsimod.nodes.waste import Waste
from wsimod.nodes.storage import Storage
from wsimod.arcs.arcs import Arc, QueueArc, AltQueueArc, DecayArc
constants.set_simple_pollutants()

    

class MyTestClass(TestCase):
    
    def assertDictAlmostEqual(self, d1, d2, accuracy = 19):
        for d in [d1, d2]:
            for key, item in d.items():
                d[key] = round(item, accuracy)
        self.assertDictEqual(d1, d2)
    
    def get_simple_model1(self):
        
        node1 = Storage(name = '1',
                        capacity = 20)
        node2 = Waste(name = '2')
        node3 = Node(name = '3')
        node4 = Node(name = '4')
        node5 = Waste(name = '5')
        
        arc1 = Arc(in_port = node1, 
                   out_port = node2, 
                   name = 'arc1')
        
        arc2 = Arc(in_port = node3, 
                   out_port = node1,
                   name = 'arc2')
        
        arc3 = Arc(in_port = node4, 
                   out_port = node1,
                   name = 'arc3')
        
        arc4 = Arc(in_port = node1, 
                   out_port = node5,
                   preference = 0.5,
                   name = 'arc4')
        
        return node1, node2, node3, node4, node5, arc1, arc2, arc3, arc4
    
    def test_arc_mb(self):
        d1 = {'volume' : 10,
            'phosphate' : 0.0001,
            'temperature' : 15}
        d2 = {'volume' : 0,
              'phosphate' : 0,
              'temperature' : 0}
        d3 = {'volume' : 20,
            'phosphate' : 0.0002,
            'temperature' : 15}
        d4 = {'volume' : 10,
              'phosphate' : 0,
              'temperature' : 0}
        d5 = {'volume' : 5,
              'phosphate' : 10,
              'temperature' : 10}
        node1 = Node(name = '1')
        node2 = Waste(name = '2')
        
        arc1 = Arc(in_port = node1, 
                   out_port = node2, 
                   name = 'arc1',
                   capacity = 10)
        
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
        
        reply = arc1.send_push_request(d1, force = True)
        in_, ds_, out_ = arc1.arc_mass_balance()
        self.assertDictAlmostEqual(d3, in_, 16)
    
    def test_arc_pull(self):
        d1 = {'volume' : 10,
                'phosphate' : 0.0001,
                'temperature' : 15}
        d2 = {'volume' : 5,
                'phosphate' : 0.00005,
                'temperature' : 15}
        node1, node2, node3, node4, node5, arc1, arc2, arc3, arc4 = self.get_simple_model1()
        node1.push_set(d1)
        
        reply = arc1.send_pull_check()
        self.assertDictAlmostEqual(d1, reply, 16)
        
        reply = arc1.send_pull_check({'volume' : 5})
        self.assertDictAlmostEqual(d2, reply, 16)
        
        reply = arc1.send_pull_request({'volume' : 5})
        self.assertDictAlmostEqual(d2, reply, 16)
        
        reply = arc1.send_pull_request({'volume' : 10})
        self.assertDictAlmostEqual(d2, reply, 16)
        
        
    def test_queue_arc_pull(self):
        node1 = Node(name = '1')
        node2 = Waste(name = '2')
        
        arc1 = QueueArc(in_port = node1, 
                        out_port = node2, 
                        name = 'arc1',
                        capacity = 10,
                        number_of_timesteps = 1
                        )
        
        d1 = {'volume' : 10,
                'phosphate' : 0.0001,
                'temperature' : 15}
        
        arc1.send_push_request(d1)
        pass
        
if __name__ == "__main__":
    unittest.main()
    