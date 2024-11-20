# WSIMOD models

1. [Introduction](#introduction)

2. [What data do you need](#what-data-do-you-need)

3. [WSIMOD model](#wsimod-model)

    3.1. [Nodes](#nodes)

    3.2. [Arcs](#arcs)

    3.3. [Model properties](#model-properties)

4. [Input data](#input-data)

5. [Limitations](#limitations)

## Introduction

In other [tutorials](tutorials.md), we generally create nodes and arcs in a dictionary format
to best explain how to understand what is going on in WSIMOD. However, this
is not a streamlined way to setup or use a model in practice. Instead, we
provide a structured format that a model can be loaded from and the ability
to save models to this format. In this tutorial we will describe the format,
and give examples.

## What data do you need?

WSIMOD combines a variety of different models into different types of
node/component. Our goal is a highly flexible approach to representing a wide
variety of water systems. The result is that your data requirements will be
highly specific to your project, the systems that you want to include, and the
questions you want to ask of your model. To understand what model components
you should include, and what data requirements these have, we recommend
familiarising yourself with the WSIMOD approach through completing the
[tutorials](tutorials.md) and viewing the [API](reference.md). Ultimately though,
all nodes and arcs can be resolved in terms of dictionaries that
determine their parameters/input data, which makes them ideal to be structured using
the [PyYAML](https://pyyaml.org/) data langauge.

## WSIMOD model

As demonstrated in the tutorials, a [model object](reference-model.md#wsimod.orchestration.model.Model)
is a helpful way to contain your nodes/arcs and orchestrate your simulation.
From the model object, you can `save` or `load` data by providing a data
directory. Critically, these functions interact with a `config.yml` file that
contains all of the information to describe your model. Below, we will explain
this file using examples from [quickstart demo](demo/scripts/quickstart_demo.md),
highlighting the key features of this config file. You can create this yourself by
running the demo and appending the following command:

```python
my_model.save(<directory_address_on_your_filesystem>)
```

The top level entries of the `config.yml` file created in the provided directorty are:

```yaml
nodes
arcs
pollutants
additive_pollutants
non_additive_pollutants
float_accuracy
dates
```

, which cover all of the properties needed to describe a model object.

To load a model, we to initialise a model object and call the `load` function:

```python
my_model = Model()
my_model.load(<directory_address_on_your_filesystem>)
```

### Nodes

The `nodes` entry of `config.yml` will contain the information required to initialise all of the components
in your model. Below are a sewer node and default node.

```yaml
nodes:
  my_sewer:
    chamber_area: 1
    name: my_sewer
    pipe_time: 0
    chamber_floor: 10
    capacity: 0.04
    pipe_timearea:
      0: 1
    type_: Sewer
    node_type_override: Sewer
  my_river:
    name: my_river
    type_: Node
    node_type_override: Node
```

By inspecting the [`Sewer`](reference-sewer.md#wsimod.nodes.sewer.Sewer) API,
we can see that this entry contains the parameters required to initiliase a
`Sewer` object, however the `capacity` and `name` fields have been updated to
the values that they are set as in the [quickstart demo](demo/scripts/quickstart_demo.md).

We see two additional fields of `type_` and `node_type_override`. If only
`type_` is provided, then this will specify the object that is created which
should match an object in WSIMOD. It also specifies how other nodes view it,
for example, a [`Sewer`](reference-sewer.md#wsimod.nodes.sewer.Sewer) node
receives water differently from [`Land`](reference-land.md#wsimod.nodes.land.Land)
nodes than it does from [`Demand`](reference-other.md#wsimod.nodes.demand.Demand)
nodes. However, there are a variety of subclasses of `Demand` node, so to
ensure the `Sewer` object treats all `Demand` subclasses the same, we overwrite
the `__class__.__name__` property in each subclass so that the model treats
(e.g.,) [`ResidentialDemand`](reference-other.md#wsimod.nodes.demand.ResidentialDemand)
as a `Demand` object. In cases such as these, to ensure WSIMOD creates a
`ResidentialDemand` object that is treated like a `Demand` object, we specify
the `type_` as `Demand` but the `node_type_override` as `ResidentialDemand`.

### Arcs

The `arcs` entry of `config.yml` contains the initialisation fields of the
[`Arc`](reference-arc.md#wsimod.arcs.arcs.Arc)
object. If we inspect the [quickstart demo](demo/scripts/quickstart_demo.md),
we will see that the `storm_outflow` arc was not initiliased with any values
for the `preference` or `capacity` parameter. They are saved by the
`Model.save()` function because, upon initialisation, if they are not provided,
the arc receives a default unbounded capacity and a neutral preference of 1.

```yaml
arcs:
  storm_outflow:
    capacity: 1000000000000000.0
    name: storm_outflow
    preference: 1
    type_: Arc
    in_port: my_sewer
    out_port: my_river
```

### Model properties

The `pollutants` entries are used to tell the model which pollutants should be simulated, which are additive (i.e., mass based), and which are non-additive (e.g., temperature).

The `float_accuracy` entry provides a number used in [mass balance checking](reference-core.md#wsimod.core.core.WSIObj.mass_balance). Common sense is suggested in interpreting mass balance errors.

The `dates` entry is written if the model object has a `dates` property and is a list of `dates` for which the model will run for if the [`Model.run()`](reference-model.md#wsimod.orchestration.model.Model.run) function is called. It is assumed that the `dates` are compatible with the dates provided in the input data.

## Input data

While the `config.yml` file contains information to parameterise and initialise
WSIMOD objects, timeseries input data is stored separately to create a more
manageable model directory. As established through the [tutorials](tutorials.md),
any node timeseries input data must be provided as a dictionary where the keys
are tuples containing the variable and time, and stored in the `data_input_dict`
property. For example, using the [`Catchment`](reference-other.md#wsimod.nodes.catchment.Catchment)
node, which is primarily a data reader:

```python
# Imports
from wsimod.core import constants
from wsimod.nodes.catchment import Catchment
from wsimod.orchestration.model import to_datetime

# Model only temperature and phosphate
constants.set_simple_pollutants()

# Create input data dictionary
date = to_datetime('2000-01-01')
forcing_data = {('flow', date) : 2,
                    ('phosphate', date) : 0.2,
                    ('temperature', date) : 10}

# Create Catchment object
my_catch = Catchment(name = 'my_catchment', data_input_dict = forcing_data)

# Assign date
my_catch.t = date

# Get flows
print(my_catch.get_flow())
{'volume': 2, 'phosphate': 0.4, 'temperature': 10}
```

We note that dates can take any hashable format, however some components require the date to have properties such as `dayofyear`, and so recommend using `datetime` like objects, we provide a simple `datetime` wrapper in [`model.to_datetime`](reference-model.md#wsimod.orchestration.model.to_datetime).

When we call `Model.save()` it will convert each node's `data_input_dict`
into a separate `.csv` (or `.csv.gz` if the `compress` option is specified),
and create an entry called `filename` for the node in the `config.yml` file.

For example,

```python
import os
from wsimod.orchestration.model import Model

my_model = Model()
my_model.add_instantiated_nodes([my_catch])
my_model.save(os.getcwd())
```

Which will create a `config.yml` file containing the `nodes` entry of:

```yaml
nodes:
  my_catchment:
    name: my_catchment
    type_: Catchment
    node_type_override: Catchment
    filename: my_catchment-inputs.csv
```

and a file in the current directory named `my_catchment-inputs.csv` containing:

```text
node,variable,time,value
my_catchment,flow,2000-01-01,2
my_catchment,phosphate,2000-01-01,0.2
my_catchment,temperature,2000-01-01,10
```

## Limitations

It is important that there are key limitations to model saving/loading. To
avoid overly complicated `config.yml` files that are easy for a user to edit,
we opted to only save the properties of a node/arc required to initialise
that object. This means that state variables, user-added properties, or
method overriding are not preserved when the model is saved. Thus, when the
model is loaded, its objects are initialised as if new. However, if a user
wishes to achieve this then the `Model/save_pickle` and `Model/load_pickle`
functions can help to achieve it, though these create binary files that are not
user readable.
