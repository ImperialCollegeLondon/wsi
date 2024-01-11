# -*- coding: utf-8 -*-
"""Created on Mon Jul  4 16:01:48 2022.

@author: bdobson
"""
import csv
import gzip
import inspect
import os
import sys
from datetime import datetime
from math import log10

import dill as pickle
import yaml
from tqdm import tqdm

from wsimod import nodes
from wsimod.arcs import arcs as arcs_mod
from wsimod.core import constants
from wsimod.core.core import WSIObj
from wsimod.nodes.land import ImperviousSurface
from wsimod.nodes.nodes import Node, QueueTank, ResidenceTank, Tank

os.environ["USE_PYGEOS"] = "0"


class to_datetime:
    """"""

    # TODO document and make better
    def __init__(self, date_string):
        """Simple datetime wrapper that has key properties used in WSIMOD components.

        Args:
            date_string (str): A string containing the date, expected in
                format %Y-%m-%d or %Y-%m.
        """
        self._date = self._parse_date(date_string)

    def __str__(self):
        return self._date.strftime("%Y-%m-%d")

    def __repr__(self):
        return self._date.strftime("%Y-%m-%d")

    @property
    def dayofyear(self):
        """

        Returns:

        """
        return self._date.timetuple().tm_yday

    @property
    def day(self):
        """

        Returns:

        """
        return self._date.day

    @property
    def year(self):
        """

        Returns:

        """
        return self._date.year

    @property
    def month(self):
        """

        Returns:

        """
        return self._date.month

    def to_period(self, args="M"):
        """

        Args:
            args:

        Returns:

        """
        return to_datetime(f"{self._date.year}-{str(self._date.month).zfill(2)}")

    def is_leap_year(self):
        """

        Returns:

        """
        year = self._date.year
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def _parse_date(self, date_string, date_format="%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            try:
                return datetime.strptime(date_string, "%Y-%m-%d")
            except ValueError:
                try:
                    # Check if valid 'YYYY-MM' format
                    if len(date_string.split("-")[0]) == 4:
                        int(date_string.split("-")[0])
                    if len(date_string.split("-")[1]) == 2:
                        int(date_string.split("-")[1])
                    return date_string
                except ValueError:
                    raise ValueError

    def __eq__(self, other):
        if isinstance(other, to_datetime):
            return self._date == other._date
        return False

    def __hash__(self):
        return hash(self._date)


class Model(WSIObj):
    """"""

    def __init__(self):
        """Object to contain nodes and arcs that provides a default orchestration.

        Returns:
            Model: An empty model object
        """
        super().__init__()
        self.arcs = {}
        # self.arcs_type = {} #not sure that this would be necessary
        self.nodes = {}
        self.nodes_type = {}

        def all_subclasses(cls):
            """

            Args:
                cls:

            Returns:

            """
            return set(cls.__subclasses__()).union(
                [s for c in cls.__subclasses__() for s in all_subclasses(c)]
            )

        self.nodes_type = [x.__name__ for x in all_subclasses(Node)] + ["Node"]
        self.nodes_type = set(
            getattr(nodes, x)(name="").__class__.__name__ for x in self.nodes_type
        ).union(["Foul"])
        self.nodes_type = {x: {} for x in self.nodes_type}

    def get_init_args(self, cls):
        """Get the arguments of the __init__ method for a class and its superclasses."""
        init_args = []
        for c in cls.__mro__:
            # Get the arguments of the __init__ method
            args = inspect.getfullargspec(c.__init__).args[1:]
            init_args.extend(args)
        return init_args

    def load(self, address, config_name="config.yml", overrides={}):
        """

        Args:
            address:
            config_name:
            overrides:
        """
        with open(os.path.join(address, config_name), "r") as file:
            data = yaml.safe_load(file)

        for key, item in overrides.items():
            data[key] = item

        constants.POLLUTANTS = data["pollutants"]
        constants.ADDITIVE_POLLUTANTS = data["additive_pollutants"]
        constants.NON_ADDITIVE_POLLUTANTS = data["non_additive_pollutants"]
        constants.FLOAT_ACCURACY = float(data["float_accuracy"])
        self.__dict__.update(Model().__dict__)

        nodes = data["nodes"]

        for name, node in nodes.items():
            if "filename" in node.keys():
                node["data_input_dict"] = read_csv(
                    os.path.join(address, node["filename"])
                )
                del node["filename"]
            if "surfaces" in node.keys():
                for key, surface in node["surfaces"].items():
                    if "filename" in surface.keys():
                        node["surfaces"][key]["data_input_dict"] = read_csv(
                            os.path.join(address, surface["filename"])
                        )
                        del surface["filename"]
                node["surfaces"] = list(node["surfaces"].values())
        arcs = data["arcs"]
        self.add_nodes(list(nodes.values()))
        self.add_arcs(list(arcs.values()))
        if "dates" in data.keys():
            self.dates = [to_datetime(x) for x in data["dates"]]

    def save(self, address, config_name="config.yml", compress=False):
        """Save the model object to a yaml file and input data to csv.gz format in the
        directory specified.

        Args:
            address (str): Path to a directory
            config_name (str, optional): Name of yaml model file.
                Defaults to 'model.yml'
        """
        if not os.path.exists(address):
            os.mkdir(address)
        nodes = {}

        if compress:
            file_type = "csv.gz"
        else:
            file_type = "csv"
        for node in self.nodes.values():
            init_args = self.get_init_args(node.__class__)
            special_args = set(["surfaces", "parent", "data_input_dict"])

            node_props = {
                x: getattr(node, x) for x in set(init_args).difference(special_args)
            }
            node_props["type_"] = node.__class__.__name__
            node_props["node_type_override"] = (
                repr(node.__class__).split(".")[-1].replace("'>", "")
            )

            if "surfaces" in init_args:
                surfaces = {}
                for surface in node.surfaces:
                    surface_args = self.get_init_args(surface.__class__)
                    surface_props = {
                        x: getattr(surface, x)
                        for x in set(surface_args).difference(special_args)
                    }
                    surface_props["type_"] = surface.__class__.__name__

                    # Exceptions...
                    # TODO I need a better way to do this
                    del surface_props["capacity"]
                    if set(["rooting_depth", "pore_depth"]).intersection(surface_args):
                        del surface_props["depth"]
                    if "data_input_dict" in surface_args:
                        if surface.data_input_dict:
                            filename = (
                                "{0}-{1}-inputs.{2}".format(
                                    node.name, surface.surface, file_type
                                )
                                .replace("(", "_")
                                .replace(")", "_")
                                .replace("/", "_")
                                .replace(" ", "_")
                            )
                            write_csv(
                                surface.data_input_dict,
                                {"node": node.name, "surface": surface.surface},
                                os.path.join(address, filename),
                                compress=compress,
                            )
                            surface_props["filename"] = filename
                    surfaces[surface_props["surface"]] = surface_props
                node_props["surfaces"] = surfaces

            if "data_input_dict" in init_args:
                if node.data_input_dict:
                    filename = "{0}-inputs.{1}".format(node.name, file_type)
                    write_csv(
                        node.data_input_dict,
                        {"node": node.name},
                        os.path.join(address, filename),
                        compress=compress,
                    )
                    node_props["filename"] = filename

            nodes[node.name] = node_props

        arcs = {}
        for arc in self.arcs.values():
            init_args = self.get_init_args(arc.__class__)
            special_args = set(["in_port", "out_port"])
            arc_props = {
                x: getattr(arc, x) for x in set(init_args).difference(special_args)
            }
            arc_props["type_"] = arc.__class__.__name__
            arc_props["in_port"] = arc.in_port.name
            arc_props["out_port"] = arc.out_port.name
            arcs[arc.name] = arc_props

        data = {
            "nodes": nodes,
            "arcs": arcs,
            "pollutants": constants.POLLUTANTS,
            "additive_pollutants": constants.ADDITIVE_POLLUTANTS,
            "non_additive_pollutants": constants.NON_ADDITIVE_POLLUTANTS,
            "float_accuracy": constants.FLOAT_ACCURACY,
        }
        if hasattr(self, "dates"):
            data["dates"] = [str(x) for x in self.dates]

        def coerce_value(value):
            """

            Args:
                value:

            Returns:

            """
            conversion_options = {
                "__float__": float,
                "__iter__": list,
                "__int__": int,
                "__str__": str,
                "__bool__": bool,
            }
            converted = False
            for property, func in conversion_options.items():
                if hasattr(value, property):
                    try:
                        yaml.safe_dump(func(value))
                        value = func(value)
                        converted = True
                        break
                    except Exception:
                        raise ValueError(f"Cannot dump: {value} of type {type(value)}")
            if not converted:
                raise ValueError(f"Cannot dump: {value} of type {type(value)}")

            return value

        def check_and_coerce_dict(data_dict):
            """

            Args:
                data_dict:
            """
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    check_and_coerce_dict(value)
                else:
                    try:
                        yaml.safe_dump(value)
                    except yaml.representer.RepresenterError:
                        if hasattr(value, "__iter__"):
                            for idx, val in enumerate(value):
                                if isinstance(val, dict):
                                    check_and_coerce_dict(val)
                                else:
                                    value[idx] = coerce_value(val)
                        data_dict[key] = coerce_value(value)

        check_and_coerce_dict(data)

        write_yaml(address, config_name, data)

    def load_pickle(self, fid):
        """Load model object to a pickle file, including the model states.

        Args:
            fid (str): File address to load the pickled model from

        Returns:
            model (obj): loaded model

        Example:
            >>> # Load and run your model
            >>> my_model.load(model_dir,config_name = 'config.yml')
            >>> _ = my_model.run()
            >>>
            >>> # Save it including its different states
            >>> my_model.save_pickle('model_at_end_of_run.pkl')
            >>>
            >>> # Load it at another time to resume the model from the end
            >>> # of the previous run
            >>> new_model = Model()
            >>> new_model = new_model.load_pickle('model_at_end_of_run.pkl')
        """
        file = open(fid, "rb")
        return pickle.load(file)

    def save_pickle(self, fid):
        """Save model object to a pickle file, including saving the model states.

        Args:
            fid (str): File address to save the pickled model to

        Returns:
            message (str): Exit message of pickle dump
        """
        file = open(fid, "wb")
        pickle.dump(self, file)
        return file.close()

    def add_nodes(self, nodelist):
        """Add nodes to the model object from a list of dicts, where each dict contains
        all of the parameters for a node. Intended to be called before add_arcs.

        Args:
            nodelist (list): List of dicts, where a dict is a node
        """

        def all_subclasses(cls):
            """

            Args:
                cls:

            Returns:

            """
            return set(cls.__subclasses__()).union(
                [s for c in cls.__subclasses__() for s in all_subclasses(c)]
            )

        for data in nodelist:
            name = data["name"]
            type_ = data["type_"]
            if "node_type_override" in data.keys():
                node_type = data["node_type_override"]
                del data["node_type_override"]
            else:
                node_type = type_
            if "foul" in name:
                # Absolute hack to enable foul sewers to be treated separate from storm
                type_ = "Foul"
            if "geometry" in data.keys():
                del data["geometry"]
            del data["type_"]
            self.nodes_type[type_][name] = getattr(nodes, node_type)(**dict(data))
            self.nodes[name] = self.nodes_type[type_][name]
            self.nodelist = [x for x in self.nodes.values()]

    def add_instantiated_nodes(self, nodelist):
        """Add nodes to the model object from a list of objects, where each object is an
        already instantiated node object. Intended to be called before add_arcs.

        Args:
            nodelist (list): list of objects that are nodes
        """
        self.nodelist = nodelist
        self.nodes = {x.name: x for x in nodelist}
        for x in nodelist:
            self.nodes_type[x.__class__.__name__][x.name] = x

    def add_arcs(self, arclist):
        """Add nodes to the model object from a list of dicts, where each dict contains
        all of the parameters for an arc.

        Args:
            arclist (list): list of dicts, where a dict is an arc
        """
        river_arcs = {}
        for arc in arclist:
            name = arc["name"]
            type_ = arc["type_"]
            del arc["type_"]
            arc["in_port"] = self.nodes[arc["in_port"]]
            arc["out_port"] = self.nodes[arc["out_port"]]
            self.arcs[name] = getattr(arcs_mod, type_)(**dict(arc))

            if arc["in_port"].__class__.__name__ in [
                "River",
                "Node",
                "Waste",
                "Reservoir",
            ]:
                if arc["out_port"].__class__.__name__ in [
                    "River",
                    "Node",
                    "Waste",
                    "Reservoir",
                ]:
                    river_arcs[name] = self.arcs[name]

        if any(river_arcs):
            upstreamness = {x: 0 for x in self.nodes_type["Waste"].keys()}
            upstreamness = self.assign_upstream(river_arcs, upstreamness)

            self.river_discharge_order = []
            for node in sorted(
                upstreamness.items(), key=lambda item: item[1], reverse=True
            ):
                if node[0] in self.nodes_type["River"].keys():
                    self.river_discharge_order.append(node[0])

    def add_instantiated_arcs(self, arclist):
        """Add arcs to the model object from a list of objects, where each object is an
        already instantiated arc object.

        Args:
            arclist (list): list of objects that are arcs.
        """
        self.arclist = arclist
        self.arcs = {x.name: x for x in arclist}
        river_arcs = {}
        for arc in arclist:
            if arc.in_port.__class__.__name__ in [
                "River",
                "Node",
                "Waste",
                "Reservoir",
            ]:
                if arc.out_port.__class__.__name__ in [
                    "River",
                    "Node",
                    "Waste",
                    "Reservoir",
                ]:
                    river_arcs[arc.name] = arc
        upstreamness = {x: 0 for x in self.nodes_type["Waste"].keys()}

        upstreamness = self.assign_upstream(river_arcs, upstreamness)

        self.river_discharge_order = []
        for node in sorted(
            upstreamness.items(), key=lambda item: item[1], reverse=True
        ):
            if node[0] in self.nodes_type["River"].keys():
                self.river_discharge_order.append(node[0])

    def assign_upstream(self, arcs, upstreamness):
        """Recursive function to trace upstream up arcs to determine which are the most
        upstream.

        Args:
            arcs (list): list of dicts where dicts are arcs
            upstreamness (dict): dictionary contain nodes in
                arcs as keys and a number representing upstreamness
                (higher numbers = more upstream)

        Returns:
            upstreamness (dict): final version of upstreamness
        """
        upstreamness_ = upstreamness.copy()
        in_nodes = [
            x.in_port.name
            for x in arcs.values()
            if x.out_port.name in upstreamness.keys()
        ]
        ind = max(list(upstreamness_.values())) + 1
        in_nodes = list(set(in_nodes).difference(upstreamness.keys()))
        for node in in_nodes:
            upstreamness[node] = ind
        if upstreamness == upstreamness_:
            return upstreamness
        else:
            upstreamness = self.assign_upstream(arcs, upstreamness)
            return upstreamness

    def debug_node_mb(self):
        """Simple function that iterates over nodes calling their mass balance
        function."""
        for node in self.nodelist:
            _ = node.node_mass_balance()

    def default_settings(self):
        """Incomplete function that enables easy specification of results storage.

        Returns:
            (dict): default settings
        """
        return {
            "arcs": {"flows": True, "pollutants": True},
            "tanks": {"storages": True, "pollutants": True},
            "mass_balance": False,
        }

    def change_runoff_coefficient(self, relative_change, nodes=None):
        """Clunky way to change the runoff coefficient of a land node.

        Args:
            relative_change (float): amount that the impervious area in the land
                node is multiplied by (grass area is changed in compensation)
            nodes (list, optional): list of land nodes to change the parameters of.
                Defaults to None, which applies the change to all land nodes.
        """
        # Multiplies impervious area by relative change and adjusts grassland
        # accordingly
        if nodes is None:
            nodes = self.nodes_type["Land"].values()

        if isinstance(relative_change, float):
            relative_change = {x: relative_change for x in nodes}

        for node in nodes:
            surface_dict = {x.surface: x for x in node.surfaces}
            if "Impervious" in surface_dict.keys():
                impervious_area = surface_dict["Impervious"].area
                grass_area = surface_dict["Grass"].area

                new_impervious_area = impervious_area * relative_change[node]
                new_grass_area = grass_area + (impervious_area - new_impervious_area)
                if new_grass_area < 0:
                    print("not enough grass")
                    break
                surface_dict["Impervious"].area = new_impervious_area
                surface_dict["Impervious"].capacity *= relative_change[node]

                surface_dict["Grass"].area = new_grass_area
                surface_dict["Grass"].capacity *= new_grass_area / grass_area
                for pol in constants.ADDITIVE_POLLUTANTS + ["volume"]:
                    surface_dict["Grass"].storage[pol] *= new_grass_area / grass_area
                for pool in surface_dict["Grass"].nutrient_pool.pools:
                    for nutrient in pool.storage.keys():
                        pool.storage[nutrient] *= new_grass_area / grass_area

    def run(
        self,
        dates=None,
        settings=None,
        record_arcs=None,
        record_tanks=None,
        record_surfaces=None,
        verbose=True,
        record_all=True,
        objectives=[],
    ):
        """Run the model object with the default orchestration.

        Args:
            dates (list, optional): Dates to simulate. Defaults to None, which
                simulates all dates that the model has data for.
            settings (dict, optional): Dict to specify what results are stored,
                not currently used. Defaults to None.
            record_arcs (list, optional): List of arcs to store result for.
                Defaults to None.
            record_tanks (list, optional): List of nodes with water stores to
                store results for. Defaults to None.
            record_surfaces (list, optional): List of tuples of
                (land node, surface) to store results for. Defaults to None.
            verbose (bool, optional): Prints updates on simulation if true.
                Defaults to True.
            record_all (bool, optional): Specifies to store all results.
                Defaults to True.
            objectives (list, optional): A list of dicts with objectives to
                calculate (see examples). Defaults to [].

        Returns:
            flows: simulated flows in a list of dicts
            tanks: simulated tanks storages in a list of dicts
            objective_results: list of values based on objectives list
            surfaces: simulated surface storages of land nodes in a list of dicts

        Examples:
            # Run a model without storing any results but calculating objectives
            import statistics as stats
            objectives = [{'element_type' : 'flows',
                           'name' : 'my_river',
                           'function' : @ (x, _) stats.mean([y['phosphate'] for y in x])
                           },
                          {'element_type' : 'tanks',
                           'name' : 'my_reservoir',
                           'function' : @ (x, model) sum([y['storage'] < (model.nodes
                           ['my_reservoir'].tank.capacity / 2) for y in x])
                           }]
            _, _, results, _ = my_model.run(record_all = False, objectives = objectives)
        """
        if record_arcs is None:
            record_arcs = []
            if record_all:
                record_arcs = list(self.arcs.keys())
        if record_tanks is None:
            record_tanks = []

        if record_surfaces is None:
            record_surfaces = []

        if settings is None:
            settings = self.default_settings()

        def blockPrint():
            """

            Returns:

            """
            stdout = sys.stdout
            sys.stdout = open(os.devnull, "w")
            return stdout

        def enablePrint(stdout):
            """

            Args:
                stdout:
            """
            sys.stdout = stdout

        if not verbose:
            stdout = blockPrint()
        if dates is None:
            dates = self.dates

        for objective in objectives:
            if objective["element_type"] == "tanks":
                record_tanks.append(objective["name"])
            elif objective["element_type"] == "flows":
                record_arcs.append(objective["name"])
            elif objective["element_type"] == "surfaces":
                record_surfaces.append((objective["name"], objective["surface"]))
            else:
                print("element_type not recorded")

        flows = []
        tanks = []
        surfaces = []
        for date in tqdm(dates, disable=(not verbose)):
            # for date in dates:
            for node in self.nodelist:
                node.t = date
                node.monthyear = date.to_period("M")

            # Run FWTW
            for node in self.nodes_type["FWTW"].values():
                node.treat_water()

            # Create demand (gets pushed to sewers)
            for node in self.nodes_type["Demand"].values():
                node.create_demand()

            # Create runoff (impervious gets pushed to sewers, pervious to groundwater)
            for node in self.nodes_type["Land"].values():
                node.run()

            # Infiltrate GW
            for node in self.nodes_type["Groundwater"].values():
                node.infiltrate()

            # Discharge sewers (pushed to other sewers or WWTW)
            for node in self.nodes_type["Sewer"].values():
                node.make_discharge()

            # Foul second so that it can discharge any misconnection
            for node in self.nodes_type["Foul"].values():
                node.make_discharge()

            # Discharge WWTW
            for node in self.nodes_type["WWTW"].values():
                node.calculate_discharge()

            # Discharge GW
            for node in self.nodes_type["Groundwater"].values():
                node.distribute()

            # river
            for node in self.nodes_type["River"].values():
                node.calculate_discharge()

            # Abstract
            for node in self.nodes_type["Reservoir"].values():
                node.make_abstractions()

            for node in self.nodes_type["Land"].values():
                node.apply_irrigation()

            for node in self.nodes_type["WWTW"].values():
                node.make_discharge()

            # Catchment routing
            for node in self.nodes_type["Catchment"].values():
                node.route()

            # river
            for node_name in self.river_discharge_order:
                self.nodes[node_name].distribute()

            # mass balance checking
            # nodes/system
            sys_in = self.empty_vqip()
            sys_out = self.empty_vqip()
            sys_ds = self.empty_vqip()

            # arcs
            for arc in self.arcs.values():
                in_, ds_, out_ = arc.arc_mass_balance()
                for v in constants.ADDITIVE_POLLUTANTS + ["volume"]:
                    sys_in[v] += in_[v]
                    sys_out[v] += out_[v]
                    sys_ds[v] += ds_[v]
            for node in self.nodelist:
                # print(node.name)
                in_, ds_, out_ = node.node_mass_balance()

                # temp = {'name' : node.name,
                #         'time' : date}
                # for lab, dict_ in zip(['in','ds','out'], [in_, ds_, out_]):
                #     for key, value in dict_.items():
                #         temp[(lab, key)] = value
                # node_mb.append(temp)

                for v in constants.ADDITIVE_POLLUTANTS + ["volume"]:
                    sys_in[v] += in_[v]
                    sys_out[v] += out_[v]
                    sys_ds[v] += ds_[v]

            for v in constants.ADDITIVE_POLLUTANTS + ["volume"]:
                # Find the largest value of in_, out_, ds_
                largest = max(sys_in[v], sys_in[v], sys_in[v])

                if largest > constants.FLOAT_ACCURACY:
                    # Convert perform comparison in a magnitude to match the largest
                    # value
                    magnitude = 10 ** int(log10(largest))
                    in_10 = sys_in[v] / magnitude
                    out_10 = sys_in[v] / magnitude
                    ds_10 = sys_in[v] / magnitude
                else:
                    in_10 = sys_in[v]
                    ds_10 = sys_in[v]
                    out_10 = sys_in[v]

                if (in_10 - ds_10 - out_10) > constants.FLOAT_ACCURACY:
                    print(
                        "system mass balance error for "
                        + v
                        + " of "
                        + str(sys_in[v] - sys_ds[v] - sys_out[v])
                    )

            # Store results
            for arc in record_arcs:
                arc = self.arcs[arc]
                flows.append(
                    {"arc": arc.name, "flow": arc.vqip_out["volume"], "time": date}
                )
                for pol in constants.POLLUTANTS:
                    flows[-1][pol] = arc.vqip_out[pol]

            for node in record_tanks:
                node = self.nodes[node]
                tanks.append(
                    {
                        "node": node.name,
                        "storage": node.tank.storage["volume"],
                        "time": date,
                    }
                )

            for node, surface in record_surfaces:
                node = self.nodes[node]
                name = node.name
                surface = node.get_surface(surface)
                if not isinstance(surface, ImperviousSurface):
                    surfaces.append(
                        {
                            "node": name,
                            "surface": surface.surface,
                            "percolation": surface.percolation["volume"],
                            "subsurface_r": surface.subsurface_flow["volume"],
                            "surface_r": surface.infiltration_excess["volume"],
                            "storage": surface.storage["volume"],
                            "evaporation": surface.evaporation["volume"],
                            "precipitation": surface.precipitation["volume"],
                            "tank_recharge": surface.tank_recharge,
                            "capacity": surface.capacity,
                            "time": date,
                            "et0_coef": surface.et0_coefficient,
                            # 'crop_factor' : surface.crop_factor
                        }
                    )
                    for pol in constants.POLLUTANTS:
                        surfaces[-1][pol] = surface.storage[pol]
                else:
                    surfaces.append(
                        {
                            "node": name,
                            "surface": surface.surface,
                            "storage": surface.storage["volume"],
                            "evaporation": surface.evaporation["volume"],
                            "precipitation": surface.precipitation["volume"],
                            "capacity": surface.capacity,
                            "time": date,
                        }
                    )
                    for pol in constants.POLLUTANTS:
                        surfaces[-1][pol] = surface.storage[pol]
            if record_all:
                for node in self.nodes.values():
                    for prop_ in dir(node):
                        prop = node.__getattribute__(prop_)
                        if prop.__class__ in [QueueTank, Tank, ResidenceTank]:
                            tanks.append(
                                {
                                    "node": node.name,
                                    "time": date,
                                    "storage": prop.storage["volume"],
                                    "prop": prop_,
                                }
                            )
                            for pol in constants.POLLUTANTS:
                                tanks[-1][pol] = prop.storage[pol]

                for name, node in self.nodes_type["Land"].items():
                    for surface in node.surfaces:
                        if not isinstance(surface, ImperviousSurface):
                            surfaces.append(
                                {
                                    "node": name,
                                    "surface": surface.surface,
                                    "percolation": surface.percolation["volume"],
                                    "subsurface_r": surface.subsurface_flow["volume"],
                                    "surface_r": surface.infiltration_excess["volume"],
                                    "storage": surface.storage["volume"],
                                    "evaporation": surface.evaporation["volume"],
                                    "precipitation": surface.precipitation["volume"],
                                    "tank_recharge": surface.tank_recharge,
                                    "capacity": surface.capacity,
                                    "time": date,
                                    "et0_coef": surface.et0_coefficient,
                                    # 'crop_factor' : surface.crop_factor
                                }
                            )
                            for pol in constants.POLLUTANTS:
                                surfaces[-1][pol] = surface.storage[pol]
                        else:
                            surfaces.append(
                                {
                                    "node": name,
                                    "surface": surface.surface,
                                    "storage": surface.storage["volume"],
                                    "evaporation": surface.evaporation["volume"],
                                    "precipitation": surface.precipitation["volume"],
                                    "capacity": surface.capacity,
                                    "time": date,
                                }
                            )
                            for pol in constants.POLLUTANTS:
                                surfaces[-1][pol] = surface.storage[pol]

            for node in self.nodes.values():
                node.end_timestep()

            for arc in self.arcs.values():
                arc.end_timestep()
        objective_results = []
        for objective in objectives:
            if objective["element_type"] == "tanks":
                val = objective["function"](
                    [x for x in tanks if x["node"] == objective["name"]], self
                )
            elif objective["element_type"] == "flows":
                val = objective["function"](
                    [x for x in flows if x["arc"] == objective["name"]], self
                )
            elif objective["element_type"] == "surfaces":
                val = objective["function"](
                    [
                        x
                        for x in surfaces
                        if (x["node"] == objective["name"])
                        & (x["surface"] == objective["surface"])
                    ],
                    self,
                )
            objective_results.append(val)
        if not verbose:
            enablePrint(stdout)
        return flows, tanks, objective_results, surfaces

    def reinit(self):
        """Reinitialise by ending all node/arc timesteps and calling reinit function in
        all nodes (generally zero-ing their storage values)."""
        for node in self.nodes.values():
            node.end_timestep()
            for prop in dir(node):
                prop = node.__getattribute__(prop)
                for prop_ in dir(prop):
                    if prop_ == "reinit":
                        prop_ = node.__getattribute__(prop_)
                        prop_()

        for arc in self.arcs.values():
            arc.end_timestep()


def write_yaml(address, config_name, data):
    """

    Args:
        address:
        config_name:
        data:
    """
    with open(os.path.join(address, config_name), "w") as file:
        yaml.dump(
            data,
            file,
            default_flow_style=False,
            sort_keys=False,
            Dumper=yaml.SafeDumper,
        )


def open_func(file_path, mode):
    """

    Args:
        file_path:
        mode:

    Returns:

    """
    if mode == "rt" and file_path.endswith(".gz"):
        return gzip.open(file_path, mode)
    else:
        return open(file_path, mode)


def read_csv(file_path, delimiter=","):
    """

    Args:
        file_path:
        delimiter:

    Returns:

    """
    with open_func(file_path, "rt") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        data = {}
        for row in reader:
            key = (row["variable"], to_datetime(row["time"]))
            value = float(row["value"])
            data[key] = value
        return data


def write_csv(data, fixed_data={}, filename="", compress=False):
    """

    Args:
        data:
        fixed_data:
        filename:
        compress:
    """
    if compress:
        open_func = gzip.open
        mode = "wt"
    else:
        open_func = open
        mode = "w"
    with open_func(filename, mode, newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(list(fixed_data.keys()) + ["variable", "time", "value"])
        fixed_data_values = list(fixed_data.values())
        for key, value in data.items():
            writer.writerow(fixed_data_values + list(key) + [str(value)])


def flatten_dict(d, parent_key="", sep="-"):
    """

    Args:
        d:
        parent_key:
        sep:

    Returns:

    """
    # Initialize an empty dictionary
    flat_dict = {}
    # Loop through each key-value pair in the input dictionary
    for k, v in d.items():
        # Construct a new key by appending the parent key and separator
        new_key = str(parent_key) + sep + str(k) if parent_key else k
        # If the value is another dictionary, call the function recursively
        if isinstance(v, dict):
            flat_dict.update(flatten_dict(v, new_key, sep))
        # Otherwise, add the key-value pair to the flat dictionary
        else:
            flat_dict[new_key] = v
    # Return the flattened dictionary
    return flat_dict


def check_and_convert_string(value):
    """

    Args:
        value:

    Returns:

    """
    try:
        return int(value)
    except Exception:
        try:
            return float(value)
        except Exception:
            if value == "None":
                return None
            else:
                return value


def unflatten_dict(d, sep=":"):
    """

    Args:
        d:
        sep:

    Returns:

    """
    result = {}
    for k, v in d.items():
        keys = k.split(sep)
        current = result
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = v
    return result


def convert_keys(d):
    """

    Args:
        d:

    Returns:

    """
    # base case: if d is not a dict, return d
    if not isinstance(d, dict):
        return d
    # recursive case: create a new dict with int keys and converted values
    new_d = {}
    for k, v in d.items():
        new_d[check_and_convert_string(k)] = convert_keys(v)
    return new_d


def csv2yaml(address, config_name="config_csv.yml", csv_folder_name="csv"):
    """

    Args:
        address:
        config_name:
        csv_folder_name:
    """
    csv_path = os.path.join(address, csv_folder_name)
    csv_list = [
        os.path.join(csv_path, f)
        for f in os.listdir(csv_path)
        if os.path.isfile(os.path.join(csv_path, f))
    ]
    objs_type = {"nodes": {}, "arcs": {}}
    for fid in csv_list:
        with open(fid, "rt") as f:
            if "Dates" in fid:
                reader = csv.reader(f, delimiter=",")
                dates = []
                for row in reader:
                    dates.append(row[0])
                objs_type["dates"] = dates[1:]
            else:
                reader = csv.DictReader(f, delimiter=",")
                data = {}
                for row in reader:
                    formatted_row = {}
                    for key, value in row.items():
                        if value:
                            if ("[" in value) & ("]" in value):
                                # Convert lists
                                value = value.strip("[]")  # Remove the brackets
                                value = value.replace("'", "")  # Remove the string bits
                                value = value.split(", ")  # Split by comma
                                value = [check_and_convert_string(x) for x in value]
                            else:
                                # Convert ints, floats and strings
                                value = check_and_convert_string(value)

                            # Convert key and store converted values
                            formatted_row[key] = value
                    if "Sim_params" not in fid:
                        label = formatted_row["label"]
                        del formatted_row["label"]

                    formatted_row = unflatten_dict(formatted_row)
                    formatted_row = convert_keys(formatted_row)

                    # Convert nested dicts dicts
                    data[row["name"]] = formatted_row
                if "Sim_params" in fid:
                    objs_type = {
                        **objs_type,
                        **{x: y["value"] for x, y in data.items()},
                    }
                else:
                    objs_type[label] = {**objs_type[label], **data}
    write_yaml(address, config_name, objs_type)


def yaml2csv(address, config_name="config.yml", csv_folder_name="csv"):
    """

    Args:
        address:
        config_name:
        csv_folder_name:
    """
    with open(os.path.join(address, config_name), "r") as file:
        data = yaml.safe_load(file)

    # Format to easy format to write to database
    objs_type = {}
    for objects, object_label in zip([data["nodes"], data["arcs"]], ["nodes", "arcs"]):
        for key, value in objects.items():
            if isinstance(value, dict):
                # Identify node type
                if "node_type_override" in value.keys():
                    type_ = value["node_type_override"]
                elif "type_" in value.keys():
                    type_ = value["type_"]
                else:
                    type_ = False

                if type_:
                    # Flatten dictionaries
                    new_dict = {}
                    if type_ not in objs_type.keys():
                        objs_type[type_] = {}

                    for key_, value_ in value.items():
                        if isinstance(value_, dict):
                            new_dict[key_] = flatten_dict(value_, key_, ":")

                    for key_, value_ in new_dict.items():
                        del value[key_]
                        value = {**value, **value_}
                    value["label"] = object_label
                    objs_type[type_][key] = value

    del data["nodes"]
    del data["arcs"]
    if "dates" in data.keys():
        objs_type["Dates"] = data["dates"]
        del data["dates"]

    objs_type["Sim_params"] = {x: {"name": x, "value": y} for x, y in data.items()}

    csv_dir = os.path.join(address, csv_folder_name)

    if not os.path.exists(csv_dir):
        os.mkdir(csv_dir)

    for key, value in objs_type.items():
        if key == "Sim_params":
            fields = ["name", "value"]
        elif key == "Dates":
            fields = ["date"]
        else:
            fields = {}
            for value_ in value.values():
                fields = {**fields, **value_}

            del fields["name"]
            fields = ["name"] + list(fields.keys())

        with open(
            os.path.join(csv_dir, "{0}.csv".format(key)), "w", newline=""
        ) as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(fields)
            if key == "Dates":
                for date in value:
                    writer.writerow([date])
            else:
                for key_, value_ in value.items():
                    writer.writerow(
                        [str(value_[x]) if x in value_.keys() else None for x in fields]
                    )
