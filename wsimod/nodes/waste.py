# -*- coding: utf-8 -*-
"""Created on Mon Nov 15 14:20:36 2021.

@author: bdobson
"""
from wsimod.nodes.nodes import Node


# TODO call this outlet not waste
class Waste(Node):
    """"""

    def __init__(self, name):
        """Outlet node that can receive any amount of water by pushes.

        Args:
            name (str): Node name

        Functions intended to call in orchestration:
            None

        Key assumptions:
            - Water 'disappears' (leaves the model) from these nodes.

        Input data and parameter requirements:
            - None
        """
        # Update args
        super().__init__(name)

        # Update handlers
        self.pull_set_handler["default"] = self.pull_set_deny
        self.pull_check_handler["default"] = self.pull_check_deny
        self.push_set_handler["default"] = self.push_set_accept
        self.push_check_handler["default"] = self.push_check_accept

        # Mass balance
        self.mass_balance_out.append(self.total_in)

    def push_set_accept(self, vqip):
        """Push set function that accepts all water.

        Args:
            vqip (dict): A VQIP that has been pushed (ignored)

        Returns:
            (dict): An empty VQIP, indicating all water was received
        """
        return self.empty_vqip()
