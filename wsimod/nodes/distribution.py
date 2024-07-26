# -*- coding: utf-8 -*-
"""Created on Sun Aug 14 16:27:14 2022.

@author: bdobson
"""

from typing import Any, Dict

from wsimod.core import constants
from wsimod.nodes.nodes import Node


def decorate_leakage_set(self, f):
    """Decorator to extend the functionality of `f` by introducing leakage. This is
    achieved by adjusting the volume of the request (vqip) to include anticipated
    leakage, calling the original function `f`, and then distributing the leaked amount
    to groundwater.

    Args:
        self (instance of Distribution class): The Distribution object to be
            extended
        f (function): The function to be extended. Expected to be the
            Distribution object's pull_set function.

    Returns:
        pull_set (function): The decorated function which includes the
            original functionality of `f` and additional leakage operations.
    """

    def pull_set(vqip, **kwargs):
        """

        Args:
            vqip:
            **kwargs:

        Returns:

        """
        vqip["volume"] /= 1 - self.leakage

        reply = f(vqip, **kwargs)

        amount_leaked = self.v_change_vqip(reply, reply["volume"] * self.leakage)

        reply = self.extract_vqip(reply, amount_leaked)

        unsuccessful_leakage = self.push_distributed(
            amount_leaked, of_type="Groundwater"
        )
        if unsuccessful_leakage["volume"] > constants.FLOAT_ACCURACY:
            print(
                "warning, distribution leakage not going to GW in {0} at {1}".format(
                    self.name, self.t
                )
            )
            reply = self.sum_vqip(reply, unsuccessful_leakage)

        return reply

    return pull_set


def decorate_leakage_check(self, f):
    """Decorator to extend the functionality of `f` by introducing leakage. This is
    achieved by adjusting the volume of the request (vqip) to include anticipated
    leakage and then calling the original function `f`.

    Args:
        self (instance of Distribution class): The Distribution object to be
            extended
        f (function): The function to be extended. Expected to be the
            Distribution object's pull_set function.

    Returns:
        pull_check (function): The decorated function which includes the
            original functionality of `f` and additional leakage operations.
    """

    def pull_check(vqip, **kwargs):
        """

        Args:
            vqip:
            **kwargs:

        Returns:

        """
        if vqip is not None:
            vqip["volume"] /= 1 - self.leakage
        reply = f(vqip, **kwargs)
        amount_leaked = self.v_change_vqip(reply, reply["volume"] * self.leakage)

        reply = self.extract_vqip(reply, amount_leaked)
        return reply

    return pull_check


class Distribution(Node):
    """"""

    def __init__(self, leakage=0, **kwargs):
        """A Node that cannot be pushed to. Intended to pass calls to FWTW - though this
        currently relies on the user to connect it properly.

        Args:
            leakage (float, optional): 1 > float >= 0 to express how much
                water should be leaked to any attached groundwater nodes. This
                number represents the proportion of total flow through the node
                that should be leaked.
                Defaults to 0.

        Functions intended to call in orchestration:
            None

        Key assumptions:
            - No distribution processes yet represented, this class is just
                for conveyance.

        Input data and parameter requirements:
            - None
        """
        self.leakage = leakage
        super().__init__(**kwargs)
        # Update handlers
        self.push_set_handler["default"] = self.push_set_deny
        self.push_check_handler["default"] = self.push_check_deny
        self.decorate_pull_handlers()

    def decorate_pull_handlers(self):
        """Decorate handlers if there is leakage ratio."""
        if self.leakage > 0:
            self.pull_set_handler["default"] = decorate_leakage_set(
                self, self.pull_set_handler["default"]
            )
            self.pull_check_handler["default"] = decorate_leakage_check(
                self, self.pull_check_handler["default"]
            )

    def apply_overrides(self, overrides: Dict[str, Any] = {}):
        """Apply overrides to the sewer.

        Enables a user to override any of the following parameters:
        leakage.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        self.leakage = overrides.pop("leakage", self.leakage)
        self.decorate_pull_handlers()
        super().apply_overrides(overrides)


class UnlimitedDistribution(Distribution):
    """"""

    def __init__(self, **kwargs):
        """A distribution node that provides unlimited water while tracking pass
        balance.

        Functions intended to call in orchestration:
            None

        Key assumptions:
            - Water demand is always satisfied.

        Input data and parameter requirements:
            - None
        """
        super().__init__(**kwargs)
        # Update handlers
        self.pull_set_handler["default"] = self.pull_set_unlimited
        self.pull_check_handler["default"] = lambda x: self.v_change_vqip(
            self.empty_vqip(), constants.UNBOUNDED_CAPACITY
        )

        # States
        self.supplied = self.empty_vqip()

        self.mass_balance_in.append(lambda: self.supplied)

    def pull_set_unlimited(self, vqip):
        """Respond that VQIP was fulfilled and update state variables for mass balance.

        Args:
            vqip (dict): A VQIP amount to request

        Returns:
            vqip (dict): A VQIP amount that was supplied
        """
        # TODO maybe need some pollutant concentrations?
        vqip = self.v_change_vqip(self.empty_vqip(), vqip["volume"])
        self.supplied = self.sum_vqip(self.supplied, vqip)
        return vqip

    def end_timestep(self):
        """Update state variables."""
        self.supplied = self.empty_vqip()
