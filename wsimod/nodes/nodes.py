# -*- coding: utf-8 -*-
"""Created on Wed Apr  7 08:43:32 2021.

@author: Barney

Converted to totals on Thur Apr 21 2022
"""
import logging
from typing import Any, Dict

from wsimod.core import constants
from wsimod.core.core import WSIObj


class Node(WSIObj):
    """"""

    def __init_subclass__(cls, **kwargs):
        """Adds all subclasses to the nodes registry."""
        super().__init_subclass__(**kwargs)
        if cls.__name__ in NODES_REGISTRY:
            logging.warning(f"Overwriting {cls.__name__} in NODES_REGISTRY with {cls}")

        NODES_REGISTRY[cls.__name__] = cls

    def __init__(self, name, data_input_dict=None):
        """Base class for CWSD nodes. Constructs all the necessary attributes for the
        node object.

        Args:
            name (str): Name of node
            data_input_dict (dict, optional): Dictionary of data inputs relevant for
                the node. Keys are tuples where first value is the name of the
                variable to read from the dict and the second value is the time.
                Defaults to None.

        Examples:
            >>> my_node = nodes.Node(name = 'london_river_junction')

        Key assumptions:
            - No physical processes represented, can be used as a junction.

        Input data and parameter requirements:
            - All nodes require a `name`
        """
        node_types = list(NODES_REGISTRY.keys())

        # Default essential parameters
        # Dictionary of arcs
        self.in_arcs = {}
        self.out_arcs = {}
        self.in_arcs_type = {x: {} for x in node_types}
        self.out_arcs_type = {x: {} for x in node_types}

        # Set parameters
        self.name = name
        self.t = None
        self.data_input_dict = data_input_dict

        # Initiailise default handlers
        self.pull_set_handler = {"default": self.pull_distributed}
        self.push_set_handler = {
            "default": lambda x: self.push_distributed(
                x, of_type=["Node", "River", "Waste", "Reservoir"]
            )
        }
        self.pull_check_handler = {"default": self.pull_check_basic}
        self.push_check_handler = {
            "default": lambda x: self.push_check_basic(
                x, of_type=["Node", "River", "Waste", "Reservoir"]
            )
        }
        super().__init__()

        # Mass balance checking
        self.mass_balance_in = [self.total_in]
        self.mass_balance_out = [self.total_out]
        self.mass_balance_ds = [lambda: self.empty_vqip()]

    def apply_overrides(self, overrides: Dict[str, Any] = {}) -> None:
        """Apply overrides to the node.

        The Node does not have any overwriteable parameters. So if any
        overrides are passed up to the node, this means that there are unused
        parameters from the Node subclass, which is flagged.

        Args:
            overrides (dict, optional): Dictionary of overrides. Defaults to {}.
        """
        # overrides data_input_dict
        from wsimod.orchestration.model import read_csv

        content = overrides.pop("filename", None)
        if isinstance(content, str):
            self.data_input_dict = read_csv(content)
        elif not content:
            pass
        else:
            raise RuntimeError("Not recognised format for data_input_dict")

        if len(overrides) > 0:
            print(f"No override behaviour defined for: {overrides.keys()}")

    def total_in(self):
        """Sum flow and pollutant amounts entering a node via in_arcs.

        Returns:
            in_ (dict): Summed VQIP of in_arcs

        Examples:
            >>> node_inflow = my_node.total_in()
        """
        in_ = self.empty_vqip()
        for arc in self.in_arcs.values():
            in_ = self.sum_vqip(in_, arc.vqip_out)

        return in_

    def total_out(self):
        """Sum flow and pollutant amounts leaving a node via out_arcs.

        Returns:
            out_ (dict): Summed VQIP of out_arcs

        Examples:
            >>> node_outflow = my_node.total_out()
        """
        out_ = self.empty_vqip()
        for arc in self.out_arcs.values():
            out_ = self.sum_vqip(out_, arc.vqip_in)

        return out_

    def node_mass_balance(self):
        """Wrapper for core.py/WSIObj/mass_balance. Tracks change in mass balance.

        Returns:
            in_ (dict): A VQIP of the total from mass_balance_in functions
            ds_ (dict): A VQIP of the total from mass_balance_ds functions
            out_ (dict): A VQIP of the total from mass_balance_out functions

        Examples:
            >>> node_in, node_out, node_ds = my_node.node_mass_balance()
        """
        in_, ds_, out_ = self.mass_balance()
        return in_, ds_, out_

    def pull_set(self, vqip, tag="default"):
        """Receives pull set requests from arcs and passes request to query handler.

        Args:
            vqip (dict): the VQIP pull request (by default, only the 'volume' key is
                needed).
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            (dict): VQIP received from query_handler

        Examples:
            >>> water_received = my_node.pull_set({'volume' : 10})
        """
        return self.query_handler(self.pull_set_handler, vqip, tag)

    def push_set(self, vqip, tag="default"):
        """Receives push set requests from arcs and passes request to query handler.

        Args:
            vqip (_type_): the VQIP push request
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            (dict): VQIP not received from query_handler

        Examples:
            water_not_pushed = my_node.push_set(wastewater_vqip)
        """
        return self.query_handler(self.push_set_handler, vqip, tag)

    def pull_check(self, vqip=None, tag="default"):
        """Receives pull check requests from arcs and passes request to query handler.

        Args:
            vqip (dict, optional): the VQIP pull check (by default, only the
                'volume' key is used). Defaults to None, which returns all available
                water to pull.
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            (dict): VQIP available from query_handler

        Examples:
            >>> water_available = my_node.pull_check({'volume' : 10})
            >>> total_water_available = my_node.pull_check()
        """
        return self.query_handler(self.pull_check_handler, vqip, tag)

    def push_check(self, vqip=None, tag="default"):
        """Receives push check requests from arcs and passes request to query handler.

        Args:
            vqip (dict, optional): the VQIP push check. Defaults to None, which
                returns all available capacity to push
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'

        Returns:
            (dict): VQIP available to push from query_handler

        Examples:
            >>> total_available_push_capacity = my_node.push_check()
            >>> available_push_capacity = my_node.push_check(wastewater_vqip)
        """
        return self.query_handler(self.push_check_handler, vqip, tag)

    def get_direction_arcs(self, direction, of_type=None):
        """Identify arcs to/from all attached nodes in a given direction.

        Args:
            direction (str): can be either 'pull' or 'push' to send checks to
                receiving or contributing nodes
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)

        Returns:
            f (str): Either 'send_pull_check' or 'send_push_check' depending on
                direction
            arcs (list): List of arc objects

        Raises:
            Message if no direction is specified

        Examples:
            >>> arcs_to_push_to = my_node.get_direction_arcs('push')
            >>> arcs_to_pull_from = my_node.get_direction_arcs('pull')
            >>> arcs_from_reservoirs = my_node.get_direction_arcs('pull', of_type =
                'Reservoir')
        """
        if of_type is None:
            # Return all arcs
            if direction == "pull":
                arcs = list(self.in_arcs.values())
                f = "send_pull_check"
            elif direction == "push":
                arcs = list(self.out_arcs.values())
                f = "send_push_check"
            else:
                print("No direction")

        else:
            if isinstance(of_type, str):
                of_type = [of_type]

            # Assign arcs/function based on parameters
            arcs = []
            if direction == "pull":
                for type_ in of_type:
                    arcs += list(self.in_arcs_type[type_].values())
                f = "send_pull_check"
            elif direction == "push":
                for type_ in of_type:
                    arcs += list(self.out_arcs_type[type_].values())
                f = "send_push_check"
            else:
                print("No direction")

        return f, arcs

    def get_connected(self, direction="pull", of_type=None, tag="default"):
        """Send push/pull checks to all attached arcs in a given direction.

        Args:
            direction (str, optional): The type of check to send to all attached
                nodes. Can be 'push' or 'pull'. The default is 'pull'.
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            connected (dict) :
                Dictionary containing keys:
                'avail': (float) - total available volume for push/pull
                'priority': (float) - total (availability * preference)
                                    of attached arcs
                'allocation': (dict) - contains all attached arcs in specified
                                direction and respective (availability * preference)

        Examples:
            >>> vqip_available_to_pull = my_node.get_direction_arcs()
            >>> vqip_available_to_push = my_node.get_direction_arcs('push')
            >>> avail_reservoir_vqip = my_node.get_direction_arcs('pull',
                                                          of_type = 'Reservoir')
            >>> avail_sewer_push_to_sewers = my_node.get_direction_arcs('push',
                                                                of_type = 'Sewer',
                                                                tag = 'Sewer')
        """
        # Initialise connected dict
        connected = {"avail": 0, "priority": 0, "allocation": {}, "capacity": {}}

        # Get arcs
        f, arcs = self.get_direction_arcs(direction, of_type)

        # Iterate over arcs, updating connected dict
        for arc in arcs:
            avail = getattr(arc, f)(tag=tag)["volume"]
            if avail < constants.FLOAT_ACCURACY:
                avail = 0  # Improves convergence
            connected["avail"] += avail
            preference = arc.preference
            connected["priority"] += avail * preference
            connected["allocation"][arc.name] = avail * preference
            connected["capacity"][arc.name] = avail

        return connected

    def query_handler(self, handler, ip, tag):
        """Sends all push/pull requests/checks using the handler (i.e., ensures the
        correct function is used that lines up with 'tag').

        Args:
            handler (dict): contains all push/pull requests for various tags
            ip (vqip): the vqip request
            tag (str): describes what type of push/pull request should be called

        Returns:
            (dict): the VQIP reply from push/pull request

        Raises:
            Message if no functions are defined for tag and if request/check
            function fails
        """
        try:
            return handler[tag](ip)
        except Exception:
            if tag not in handler.keys():
                print("No functions defined for " + tag)
                return handler[tag](ip)
            else:
                print("Some other error")
                return handler[tag](ip)

    def pull_distributed(self, vqip, of_type=None, tag="default"):
        """Send pull requests to all (or specified by type) nodes connecting to self.
        Iterate until request is met or maximum iterations are hit. Streamlines if only
        one in_arc exists.

        Args:
            vqip (dict): Total amount to pull (by default, only the
                'volume' key is used)
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            pulled (dict): VQIP of combined pulled water
        """
        if len(self.in_arcs) == 1:
            # If only one in_arc, just pull from that
            if of_type is None:
                pulled = next(iter(self.in_arcs.values())).send_pull_request(
                    vqip, tag=tag
                )
            elif any(
                [x in of_type for x, y in self.in_arcs_type.items() if len(y) > 0]
            ):
                pulled = next(iter(self.in_arcs.values())).send_pull_request(
                    vqip, tag=tag
                )
            else:
                # No viable out arcs
                pulled = self.empty_vqip()
        else:
            # Pull in proportion from connected by priority

            # Initialise pulled, deficit, connected, iter_
            pulled = self.empty_vqip()
            deficit = vqip["volume"]
            connected = self.get_connected(direction="pull", of_type=of_type, tag=tag)
            iter_ = 0

            # Iterate over sending nodes until deficit met
            while (
                (deficit > constants.FLOAT_ACCURACY)
                & (connected["avail"] > constants.FLOAT_ACCURACY)
            ) & (iter_ < constants.MAXITER):
                # Pull from connected
                for key, allocation in connected["allocation"].items():
                    received = self.in_arcs[key].send_pull_request(
                        {"volume": deficit * allocation / connected["priority"]},
                        tag=tag,
                    )
                    pulled = self.sum_vqip(pulled, received)

                # Update deficit, connected and iter_
                deficit = vqip["volume"] - pulled["volume"]
                connected = self.get_connected(
                    direction="pull", of_type=of_type, tag=tag
                )
                iter_ += 1

            if iter_ == constants.MAXITER:
                print("Maxiter reached in {0} at {1}".format(self.name, self.t))
        return pulled

    def push_distributed(self, vqip, of_type=None, tag="default"):
        """Send push requests to all (or specified by type) nodes connecting to self.
        Iterate until request is met or maximum iterations are hit. Streamlines if only
        one in_arc exists.

        Args:
            vqip (dict): Total amount to push
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            not_pushed_ (dict): VQIP of water that cannot be pushed
        """
        if len(self.out_arcs) == 1:
            # If only one out_arc, just send the water down that
            if of_type is None:
                not_pushed_ = next(iter(self.out_arcs.values())).send_push_request(
                    vqip, tag=tag
                )
            elif any(
                [x in of_type for x, y in self.out_arcs_type.items() if len(y) > 0]
            ):
                not_pushed_ = next(iter(self.out_arcs.values())).send_push_request(
                    vqip, tag=tag
                )
            else:
                # No viable out arcs
                not_pushed_ = vqip
        else:
            # Push in proportion to connected by priority
            # Initialise pushed, deficit, connected, iter_
            not_pushed = vqip["volume"]
            not_pushed_ = self.copy_vqip(vqip)
            connected = self.get_connected(direction="push", of_type=of_type, tag=tag)
            iter_ = 0
            if not_pushed > connected["avail"]:
                # If more water than can be pushed, ignore preference and allocate all
                #   available based on capacity
                connected["priority"] = connected["avail"]
                connected["allocation"] = connected["capacity"]

            # Iterate over receiving nodes until sent
            while (
                (not_pushed > constants.FLOAT_ACCURACY)
                & (connected["avail"] > constants.FLOAT_ACCURACY)
                & (iter_ < constants.MAXITER)
            ):
                # Push to connected
                amount_to_push = min(connected["avail"], not_pushed)

                for key, allocation in connected["allocation"].items():
                    to_send = amount_to_push * allocation / connected["priority"]
                    to_send = self.v_change_vqip(not_pushed_, to_send)
                    reply = self.out_arcs[key].send_push_request(to_send, tag=tag)

                    sent = self.extract_vqip(to_send, reply)
                    not_pushed_ = self.extract_vqip(not_pushed_, sent)

                not_pushed = not_pushed_["volume"]
                connected = self.get_connected(
                    direction="push", of_type=of_type, tag=tag
                )
                iter_ += 1

            if iter_ == constants.MAXITER:
                print("Maxiter reached in {0} at {1}".format(self.name, self.t))

        return not_pushed_

    def check_basic(self, direction, vqip=None, of_type=None, tag="default"):
        """Generic function that conveys a pull or push check onwards to connected
        nodes. It is the default behaviour that treats a node like a junction.

        Args:
            direction (str): can be either 'pull' or 'push' to send checks to
                receiving or contributing nodes
            vqip (dict, optional): The VQIP to check. Defaults to None (if pulling
                this will return available water to pull, if pushing then available
                capacity to push).
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            avail (dict): VQIP responses summed over all requests
        """
        f, arcs = self.get_direction_arcs(direction, of_type)

        # Iterate over arcs, updating total
        avail = self.empty_vqip()
        for arc in arcs:
            avail = self.sum_vqip(avail, getattr(arc, f)(tag=tag))

        if vqip is not None:
            avail = self.v_change_vqip(avail, min(avail["volume"], vqip["volume"]))

        return avail

    def pull_check_basic(self, vqip=None, of_type=None, tag="default"):
        """Default node check behaviour that treats a node like a junction. Water
        available to pull is just the water available to pull from upstream connected
        nodes.

        Args:
            vqip (dict, optional): VQIP from handler of amount to pull check
                (by default, only the 'volume' key is used). Defaults to None (which
                returns all availalbe water to pull).
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            (dict): VQIP check response of upstream nodes
        """
        return self.check_basic("pull", vqip, of_type, tag)

    def push_check_basic(self, vqip=None, of_type=None, tag="default"):
        """Default node check behaviour that treats a node like a junction. Water
        available to push is just the water available to push to downstream connected
        nodes.

        Args:
            vqip (dict, optional): VQIP from handler of amount to push check.
                Defaults to None (which returns all available capacity to push).
            of_type (str or list) : optional, can be specified to send checks only
                to nodes of a given type (must be a subclass in nodes.py)
            tag (str, optional): optional message to direct query_handler which pull
                function to call. Defaults to 'default'.

        Returns:
            (dict): VQIP check response of downstream nodes
        """
        return self.check_basic("push", vqip, of_type, tag)

    def pull_set_deny(self, vqip):
        """Responds that no water is available to pull from a request.

        Args:
            vqip (dict): A VQIP amount of water requested (ignored)

        Returns:
            (dict): An empty VQIP indicated no water was pulled

        Raises:
            Message when called, since it would usually occur if a model is
            improperly connected
        """
        print("Attempted pull set from deny")
        return self.empty_vqip()

    def pull_check_deny(self, vqip=None):
        """Responds that no water is available to pull from a check.

        Args:
            vqip (dict): A VQIP amount of water requested (ignored)

        Returns:
            (dict): An empty VQIP indicated no water was pulled

        Raises:
            Message when called, since it would usually occur if a model is
            improperly connected
        """
        print("Attempted pull check from deny")
        return self.empty_vqip()

    def push_set_deny(self, vqip):
        """Responds that no water is available to push in a request.

        Args:
            vqip (dict): A VQIP amount of water to push

        Returns:
            vqip (dict): Returns the request indicating no water was pushed

        Raises:
            Message when called, since it would usually occur if a model is
            improperly connected
        """
        print("Attempted push set to deny")
        return vqip

    def push_check_deny(self, vqip=None):
        """Responds that no water is available to push in a check.

        Args:
            vqip (dict): A VQIP amount of water to push check (ignored)

        Returns:
            (dict): An empty VQIP indicated no capacity for pushes exists

        Raises:
            Message when called, since it would usually occur if a model is
            improperly connected
        """
        print("Attempted push check to deny")
        return self.empty_vqip()

    def push_check_accept(self, vqip=None):
        """Push check function that accepts all water.

        Args:
            vqip (dict, optional): A VQIP that has been pushed (ignored)

        Returns:
            (dict): VQIP or an unbounded capacity, indicating all water can be received
        """
        if not vqip:
            vqip = self.empty_vqip()
            vqip["volume"] = constants.UNBOUNDED_CAPACITY
        return vqip

    def get_data_input(self, var):
        """Read data from data_input_dict. Keys are tuples with the first entry as the
        variable to read and second entry the time.

        Args:
            var (str): Name of variable

        Returns:
            Data read
        """
        return self.data_input_dict[(var, self.t)]

    def end_timestep(self):
        """Empty function intended to be called at the end of every timestep.

        Subclasses will overwrite this functions.
        """
        pass

    def reinit(self):
        """Empty function to be written if reinitialisation capability is added."""
        pass


"""
    This is an attempt to generalise the behaviour of pull/push_distributed
    It doesn't yet work...

    def general_distribute(self, vqip, of_type = None, tag = 'default', direction =
        None):
        if direction == 'push':
            arcs = self.out_arcs
            arcs_type = self.out_arcs_type
            tracker = self.copy_vqip(vqip)
            requests = {x.name : lambda y : x.send_push_request(y, tag) for x in arcs.
                values()}
        elif direction == 'pull':
            arcs = self.in_arcs
            arcs_type = self.in_arcs_type
            tracker = self.empty_vqip()
            requests = {x.name : lambda y : x.send_pull_request(y, tag) for x in arcs.
                values()}
        else:
            print('No direction')

        if len(arcs) == 1:
            if (of_type == None) | any([x in of_type for x, y in arcs_type.items() if
                len(y) > 0]):
                arc = next(iter(arcs.keys()))
                return requests[arc](vqip)
            else:
                #No viable arcs
                return tracker

        connected = self.get_connected(direction = direction,
                                                                of_type = of_type,
                                                                tag = tag)

        iter_ = 0

        target = self.copy_vqip(vqip)
        #Iterate over sending nodes until deficit met
        while (((target['volume'] > constants.FLOAT_ACCURACY) &
                (connected['avail'] > constants.FLOAT_ACCURACY)) &
                (iter_ < constants.MAXITER)):

                amount = min(connected['avail'], target['volume']) #Deficit or amount
                    still to push
                replies = self.empty_vqip()

                for key, allocation in connected['allocation'].items():
                    to_request = amount * allocation / connected['priority']
                    to_request = self.v_change_vqip(target, to_request)
                    reply = requests[key](to_request)
                    replies = self.sum_vqip(replies, reply)

                if direction == 'pull':
                    target = self.extract_vqip(target, replies)
                elif direction == 'push':
                    target = replies

                connected = self.get_connected(direction = direction,
                                                                of_type = of_type,
                                                                tag = tag)
                iter_ += 1

                if iter_ == constants.MAXITER:
                    print('Maxiter reached')
        return target"""

# def replace(self, newnode):
#     #TODO - doesn't work because the bound methods (e.g., pull_set_handler) get
#     #associated with newnode and can't (as far as I can tell) be moved to self
#
#     """
#     Replace node with new node, maintaining any existing references to original node

#     Example
#     -------
#     print(my_node.name)
#     my_node.update(Node(name = 'new_node'))
#     print(my_node.name)
#     """


#     #You could use the below code to move the arcs_type references to arcs
#     #that are attached to this node. However, if you were creating a new
#     #subclass of Node then you would need to include this key in all
#     #arcs_type dictionaries in all nodes... which would get complicated
#     #probably safest to leave the arcs_type keys that are associated with
#     #this arc the same (for now...) -therefore - needs the same name

#     # for arc in self.in_arcs.values():
#     #     _ = arc.in_port.out_arcs_type[self.__class__.__name__].pop(arc.name)
#     #     arc.in_port.out_arcs_type[newnode.__class__.__name__][arc.name] = arc
#     # for arc in self.out_arcs.values():
#     #     _ = arc.out_port.in_arcs_type[self.__class__.__name__].pop(arc.name)
#     #     arc.out_port.in_arcs_type[newnode.__class__.__name__][arc.name] = arc


#     #Replace class
#     self.__class__ = newnode.__class__

#     #Replace object information (keeping some old information such as in_arcs)
#     for key in ['in_arcs',
#                 'out_arcs',
#                 'in_arcs_type',
#                 'out_arcs_type']:
#         newnode.__dict__[key] = self.__dict__[key]

#     self.__dict__.clear()
#     self.__dict__.update(newnode.__dict__)


NODES_REGISTRY: dict[str, type[Node]] = {Node.__name__: Node}
