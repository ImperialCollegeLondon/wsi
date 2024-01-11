# -*- coding: utf-8 -*-
"""Created on Tue Nov  1 09:03:17 2022.

@author: Barney
"""
import os
import re

import pandas as pd

from wsimod.arcs.arcs import Arc
from wsimod.core import constants
from wsimod.nodes.catchment import Catchment
from wsimod.nodes.demand import ResidentialDemand
from wsimod.nodes.land import Land
from wsimod.nodes.nodes import Node
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.storage import Groundwater, Reservoir
from wsimod.nodes.waste import Waste
from wsimod.nodes.wtw import FWTW, WWTW
from wsimod.orchestration.model import Model

# NOTE - these are only supplements to the demos in the documentation
# if you want to see demos, go to docs/demo/scripts!


def preprocess_oxford(data_dir=None):
    """

    Args:
        data_dir:
    """
    # This function is used to create the timeseries data for the oxford demo
    if data_dir is None:
        data_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "demo",
            "data",
        )

    UG_L_TO_KG_M3 = 1e-6
    MG_L_TO_KG_M3 = 1e-3

    q_lab = [
        ("39008_gdf.csv", "thames"),
        ("39034_gdf.csv", "evenlode"),
        ("39021_gdf.csv", "cherwell"),
        ("39140_gdf.csv", "ray"),
    ]

    flows = []
    for fn, river in q_lab:
        df = pd.read_csv(
            os.path.join(data_dir, "raw", fn), skiprows=19, error_bad_lines=False
        )
        if df.shape[1] == 2:
            df.columns = ["date", "flow"]
        else:
            df.columns = ["date", "flow", "missing"]
        df["site"] = river
        flows.append(df)

    flows = pd.concat(flows)
    flows = flows.pivot(columns="site", index="date", values="flow")
    flows.index = pd.to_datetime(flows.index)

    wq_data = pd.read_csv(
        os.path.join(
            data_dir, "raw", "CEHThamesInitiative_WaterQualityData_2009-2013.csv"
        )
    )

    rain = pd.read_csv(
        os.path.join(data_dir, "raw", "39008_cdr.csv"),
        skiprows=19,
        error_bad_lines=False,
    )
    rain.columns = ["date", "value", "misc"]
    rain["site"] = "oxford_land"
    rain["variable"] = "precipitation"
    rain = rain.drop("misc", axis=1)
    rain.date = pd.to_datetime(rain.date)

    sites = {
        "River Thames at Swinford": "thames",
        "River Evenlode at Cassington Mill": "evenlode",
        "River Ray at Islip": "ray",
        "River Cherwell at Hampton Poyle": "cherwell",
    }
    wq = wq_data.loc[wq_data.Site.isin(sites.keys())]
    wq["Sampling date (dd/mm/yyyy)"] = pd.to_datetime(
        wq["Sampling date (dd/mm/yyyy)"], format="%d/%m/%Y"
    )
    wq = wq.rename(columns={"Sampling date (dd/mm/yyyy)": "date", "Site": "site"})

    wq.site = [sites[x] for x in wq.site]

    wq = wq.set_index("date").drop("Sampling time (hh:mm)", axis=1)
    wq[wq.columns.drop("site")] = wq[wq.columns.drop("site")].apply(
        lambda x: pd.to_numeric(x, errors="coerce")
    )
    wq = wq.dropna(axis=1, how="any")
    wq = wq.drop("Mean daily river discharge (m3 s-1)", axis=1)
    wq = wq.groupby("site").resample("d").interpolate().drop("site", axis=1)
    wq = wq.reset_index()
    wq.loc[:, wq.columns.str.contains("ug")] *= UG_L_TO_KG_M3
    wq.loc[:, wq.columns.str.contains("mg")] *= MG_L_TO_KG_M3

    columns = []
    for pol in wq.columns.unique():
        text = pol.lower()
        for sub in ["water", "dissolved", "total", " ", r"\(.*\)"]:
            text = re.sub(sub, "", text)
        columns.append(text)
    wq.columns = columns

    # Convert to nitrate as N
    wq["nitrate"] /= 4.43

    # Convert to Silica as SiO2
    wq["silicon"] *= 2.14

    wq = wq.melt(id_vars=["site", "date"])

    # wq.date = pd.to_datetime(wq.date.dt.date)

    flows = flows.loc[flows.index.isin(wq.date)]
    flows = flows.unstack().rename("value").reset_index()
    flows["variable"] = "flow"

    rain = rain.loc[rain.date.isin(wq.date)]
    evaporation = create_timeseries(2 / 1000, rain.date, "et0")
    evaporation["site"] = "oxford_land"

    temperature_ = (
        wq.loc[wq.variable == "temperature"].groupby("date").mean().reset_index()
    )
    temperature_["site"] = "oxford_land"
    temperature_["variable"] = "temperature"

    input_data = pd.concat([wq, flows, rain, evaporation, temperature_], axis=0)
    input_data.to_csv(
        os.path.join(data_dir, "processed", "timeseries_data.csv"), index=False
    )


def create_oxford_model(data_folder):
    """

    Args:
        data_folder:

    Returns:

    """
    input_fid = os.path.join(data_folder, "processed", "timeseries_data.csv")
    input_data = pd.read_csv(input_fid)
    input_data.loc[input_data.variable == "flow", "value"] *= constants.M3_S_TO_M3_DT
    input_data.loc[input_data.variable == "precipitation", "value"] *= constants.MM_TO_M
    input_data.date = pd.to_datetime(input_data.date)
    data_input_dict = input_data.set_index(["variable", "date"]).value.to_dict()
    data_input_dict = (
        input_data.groupby("site")
        .apply(lambda x: x.set_index(["variable", "date"]).value.to_dict())
        .to_dict()
    )
    dates = input_data.date.unique()
    dates = dates[dates.argsort()]
    dates = [pd.Timestamp(x) for x in dates]
    constants.POLLUTANTS = input_data.variable.unique().tolist()
    constants.POLLUTANTS.remove("flow")
    constants.POLLUTANTS.remove("precipitation")
    constants.POLLUTANTS.remove("et0")
    constants.NON_ADDITIVE_POLLUTANTS = ["temperature"]
    constants.ADDITIVE_POLLUTANTS = list(
        set(constants.POLLUTANTS).difference(constants.NON_ADDITIVE_POLLUTANTS)
    )
    constants.FLOAT_ACCURACY = 1e-8
    thames_above_abingdon = Waste(name="thames_above_abingdon")
    farmoor_abstraction = Node(name="farmoor_abstraction")
    evenlode_thames = Node(name="evenlode_thames")
    cherwell_ray = Node(name="cherwell_ray")
    cherwell_thames = Node(name="cherwell_thames")
    thames_mixer = Node(name="thames_mixer")
    evenlode = Catchment(name="evenlode", data_input_dict=data_input_dict["evenlode"])
    thames = Catchment(name="thames", data_input_dict=data_input_dict["thames"])
    ray = Catchment(name="ray", data_input_dict=data_input_dict["ray"])
    cherwell = Catchment(name="cherwell", data_input_dict=data_input_dict["cherwell"])
    oxford_fwtw = FWTW(
        service_reservoir_storage_capacity=1e5,
        service_reservoir_storage_area=2e4,
        service_reservoir_initial_storage=0.9e5,
        treatment_throughput_capacity=4.5e4,
        name="oxford_fwtw",
    )
    land_inputs = data_input_dict["oxford_land"]
    pollutant_deposition = {
        "boron": 100e-10,
        "calcium": 70e-7,
        "chloride": 60e-10,
        "fluoride": 0.2e-7,
        "magnesium": 6e-7,
        "nitrate": 2e-9,
        "nitrogen": 4e-7,
        "potassium": 7e-7,
        "silicon": 7e-9,
        "sodium": 30e-9,
        "sulphate": 70e-7,
    }
    surface = [
        {
            "type_": "PerviousSurface",
            "area": 2e7,
            "pollutant_load": pollutant_deposition,
            "surface": "rural",
            "field_capacity": 0.3,
            "depth": 0.5,
            "initial_storage": 2e7 * 0.4 * 0.5,
        },
        {
            "type_": "ImperviousSurface",
            "area": 1e7,
            "pollutant_load": pollutant_deposition,
            "surface": "urban",
            "initial_storage": 5e6,
        },
    ]
    oxford_land = Land(
        surfaces=surface, name="oxford_land", data_input_dict=land_inputs
    )
    oxford = ResidentialDemand(
        name="oxford",
        population=2e5,
        per_capita=0.15,
        pollutant_load={
            "boron": 500 * constants.UG_L_TO_KG_M3 * 0.15,
            "calcium": 150 * constants.MG_L_TO_KG_M3 * 0.15,
            "chloride": 180 * constants.MG_L_TO_KG_M3 * 0.15,
            "fluoride": 0.4 * constants.MG_L_TO_KG_M3 * 0.15,
            "magnesium": 30 * constants.MG_L_TO_KG_M3 * 0.15,
            "nitrate": 60 * constants.MG_L_TO_KG_M3 * 0.15,
            "nitrogen": 50 * constants.MG_L_TO_KG_M3 * 0.15,
            "potassium": 30 * constants.MG_L_TO_KG_M3 * 0.15,
            "silicon": 20 * constants.MG_L_TO_KG_M3 * 0.15,
            "sodium": 200 * constants.MG_L_TO_KG_M3 * 0.15,
            "sulphate": 250 * constants.MG_L_TO_KG_M3 * 0.15,
            "temperature": 14,
        },
        data_input_dict=land_inputs,
    )
    farmoor = Reservoir(
        name="farmoor", capacity=1e7, initial_storage=1e7, area=1.5e6, datum=62
    )
    distribution = Node(name="oxford_distribution")
    oxford_wwtw = WWTW(
        stormwater_storage_capacity=2e4,
        stormwater_storage_area=2e4,
        treatment_throughput_capacity=5e4,
        name="oxford_wwtw",
    )
    combined_sewer = Sewer(
        capacity=4e6, pipe_timearea={0: 0.8, 1: 0.15, 2: 0.05}, name="combined_sewer"
    )
    gw = Groundwater(capacity=3.2e9, area=3.2e8, name="gw", residence_time=20)
    nodelist = [
        thames_above_abingdon,
        evenlode,
        thames,
        ray,
        cherwell,
        oxford,
        distribution,
        farmoor,
        oxford_fwtw,
        oxford_wwtw,
        combined_sewer,
        oxford_land,
        gw,
        farmoor_abstraction,
        evenlode_thames,
        cherwell_ray,
        cherwell_thames,
        thames_mixer,
    ]
    fwtw_to_distribution = Arc(
        in_port=oxford_fwtw, out_port=distribution, name="fwtw_to_distribution"
    )
    abstraction_to_farmoor = Arc(
        in_port=farmoor_abstraction,
        out_port=farmoor,
        name="abstraction_to_farmoor",
        capacity=5e4,
    )
    sewer_to_wwtw = Arc(
        in_port=combined_sewer,
        out_port=oxford_wwtw,
        preference=1e10,
        name="sewer_to_wwtw",
    )
    sewer_overflow = Arc(
        in_port=combined_sewer,
        out_port=thames_mixer,
        preference=1e-10,
        name="sewer_overflow",
    )
    evenlode_to_thames = Arc(
        in_port=evenlode, out_port=evenlode_thames, name="evenlode_to_thames"
    )

    thames_to_thames = Arc(
        in_port=thames, out_port=evenlode_thames, name="thames_to_thames"
    )

    ray_to_cherwell = Arc(in_port=ray, out_port=cherwell_ray, name="ray_to_cherwell")

    cherwell_to_cherwell = Arc(
        in_port=cherwell, out_port=cherwell_ray, name="cherwell_to_cherwell"
    )

    thames_to_farmoor = Arc(
        in_port=evenlode_thames, out_port=farmoor_abstraction, name="thames_to_farmoor"
    )

    farmoor_to_mixer = Arc(
        in_port=farmoor_abstraction, out_port=thames_mixer, name="farmoor_to_mixer"
    )

    cherwell_to_mixer = Arc(
        in_port=cherwell_ray, out_port=thames_mixer, name="cherwell_to_mixer"
    )

    wwtw_to_mixer = Arc(
        in_port=oxford_wwtw, out_port=thames_mixer, name="wwtw_to_mixer"
    )

    mixer_to_waste = Arc(
        in_port=thames_mixer, out_port=thames_above_abingdon, name="mixer_to_waste"
    )

    distribution_to_demand = Arc(
        in_port=distribution, out_port=oxford, name="distribution_to_demand"
    )

    reservoir_to_fwtw = Arc(
        in_port=farmoor, out_port=oxford_fwtw, name="reservoir_to_fwtw"
    )

    fwtw_to_sewer = Arc(
        in_port=oxford_fwtw, out_port=combined_sewer, name="fwtw_to_sewer"
    )

    demand_to_sewer = Arc(
        in_port=oxford, out_port=combined_sewer, name="demand_to_sewer"
    )

    land_to_sewer = Arc(
        in_port=oxford_land, out_port=combined_sewer, name="land_to_sewer"
    )

    land_to_gw = Arc(in_port=oxford_land, out_port=gw, name="land_to_gw")

    garden_to_gw = Arc(in_port=oxford, out_port=gw, name="garden_to_gw")

    gw_to_mixer = Arc(in_port=gw, out_port=thames_mixer, name="gw_to_mixer")
    arclist = [
        evenlode_to_thames,
        thames_to_thames,
        ray_to_cherwell,
        cherwell_to_cherwell,
        thames_to_farmoor,
        farmoor_to_mixer,
        cherwell_to_mixer,
        wwtw_to_mixer,
        sewer_overflow,
        mixer_to_waste,
        abstraction_to_farmoor,
        distribution_to_demand,
        demand_to_sewer,
        land_to_sewer,
        sewer_to_wwtw,
        fwtw_to_sewer,
        fwtw_to_distribution,
        reservoir_to_fwtw,
        land_to_gw,
        garden_to_gw,
        gw_to_mixer,
    ]
    my_model = Model()
    my_model.add_instantiated_nodes(nodelist)
    my_model.add_instantiated_arcs(arclist)
    my_model.dates = dates
    return my_model


def pull_check_mrf(node, vqip=None):
    """

    Args:
        node:
        vqip:

    Returns:

    """
    reply = node.pull_check_basic()
    reply["volume"] = max(
        reply["volume"] - (node.mrf - node.mrf_satisfied_this_timestep), 0
    )
    if vqip is not None:
        reply["volume"] = min(reply["volume"], vqip["volume"])
    return reply


def pull_set_mrf(node, vqip):
    """

    Args:
        node:
        vqip:

    Returns:

    """
    request = node.copy_vqip(vqip)
    request["volume"] += node.mrf - node.mrf_satisfied_this_timestep
    reply = node.pull_distributed(request)
    reply_to_mrf = min((node.mrf - node.mrf_satisfied_this_timestep), reply["volume"])
    node.mrf_satisfied_this_timestep += reply_to_mrf
    reply_to_mrf = node.v_change_vqip(reply, reply_to_mrf)
    reply = node.extract_vqip(reply, reply_to_mrf)
    mrf_route_reply = node.push_distributed(reply_to_mrf, of_type=["Node"])
    if mrf_route_reply["volume"] > constants.FLOAT_ACCURACY:
        print("warning MRF not able to push")
    return reply


def push_set_mrf(node, vqip):
    """

    Args:
        node:
        vqip:

    Returns:

    """
    reply = node.push_distributed(vqip)
    total_pushed_downstream = vqip["volume"] - reply["volume"]
    node.mrf_satisfied_this_timestep = min(
        node.mrf, node.mrf_satisfied_this_timestep + total_pushed_downstream
    )
    return reply


def end_timestep(node):
    """

    Args:
        node:
    """
    node.mrf_satisfied_this_timestep = 0


def convert_to_mrf(node, mrf=5):
    """

    Args:
        node:
        mrf:
    """
    node.mrf = mrf
    node.mrf_satisfied_this_timestep = 0
    node.pull_set_handler["default"] = lambda x: pull_set_mrf(node, x)
    node.pull_check_handler["default"] = lambda x: pull_check_mrf(node, x)
    node.end_timestep = lambda: end_timestep(node)


def create_oxford_model_mrf(data_folder):
    """

    Args:
        data_folder:

    Returns:

    """
    my_model = create_oxford_model(data_folder)
    convert_to_mrf(my_model.nodes["farmoor_abstraction"], mrf=3 * 86400)
    return my_model


def create_timeseries(amount, dates, variable):
    """Create a timeseries with a constant value, formatted as a dataframe.

    Args:
        amount (float): Constant value to be applied over the timeseries
        dates (list): list or iterable of dates to be generated
        variable (str): String to store in the 'variable' column of the dataframe

    Returns:
        (DataFrame): the formatted dataframe
    """
    df = pd.DataFrame(columns=["date", "variable", "value"])
    df["date"] = dates
    df["variable"] = variable
    df["value"] = amount
    return df
