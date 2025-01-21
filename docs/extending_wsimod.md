# Extending and customising WSIMOD functionality

WSIMOD has many features built-in, but undoubtedly, to model real life scenarios, you will need to customise it to your specific needs.

WSIMOD offers 4 ways of doing this customisation of increased complexity - and flexibility: custom orchestration, overrides, patches and custom classes.

## Custom orchestration

When trying to capture a given behaviour, we encourage users to first attempt to implement it by connecting [`Nodes`](reference-nodes.md#wsimod.nodes.nodes.Node) and [`Arcs`](reference-arcs.md#wsimod.arcs.arcs.Arc) in a way that enables the behaviour to spontaneously arise from node interactions. By doing this, you create a model that is less prescribed and more likely to reveal interesting integrated mechanisms. That said, sometimes it is not possible, for example see Section 2.3 in our [theory paper](https://doi.org/10.5194/gmd-17-4495-2024). In cases like this, our first recommendation is to customise your orchestration, which changes the order of operations within a timestep for a [`Model`](reference-model.md#wsimod.orchestration.model.Model) object.

The model orchestration can be customised within the `orchestration` section of the config file. For example, the following orchestration will run the simulation with two actions: first it will run the `infiltrate` method for all nodes of `type_: Groundwater`, and then the `make_discharge` method for nodes all of `type_: Sewer`. Hint: just because the model sees a node as a given `type_`, doesn't mean the node has to be that class, see the [model tutorial](wsimod_models.md/#nodes) for more detail.

```yaml
orchestration:
- Groundwater: infiltrate
- Sewer: make_discharge
```

If no `orchestration` is provided, then a default sequence is used. Check the [Orchestration demonstration](./../demo/scripts/oxford_demo/#orchestration) for more details on how to customise this. Note, that if you change your orchestration *at all* then you will have to provide a full orchestration for all `type_: functions` that need calling (even ones that are in the default orchestration, which you can find in [`Model.__init__`](reference-model.md#Model.__init__)).

## Overrides

Overrides are the next way of customising the behaviour of nodes or arcs. They enable specifying the value of one or more parameters of a specific - existing - node or arc. These overrides are specified in the config file for the model under a `overrides` section, and therefore they need to be objects that can be parsed in yaml - strings, floats, etc.

Because many parameters require other states to change when they are changed, our recommendation is that any parameter changes are either changed directly in the `config` file or inside the `overrides` section of the config file (which offers a convenient location to include all changes made to a base `config`). Because of this, if you are changing parameters on-the-fly, we **strongly recommend** using the [`add_overrides`](reference-model.md#wsimod.orchestration.model.Model.add_overrides) functionality of the [`Model`](reference-model.md#wsimod.orchestration.model.Model) object.

The following snippet shows and example on how to add overrides, in this case one node and one arc. `name` and `type_` are mandatory fields:

```yaml
overrides:
  nodes:
    my_groundwater:
      name: my_groundwater
      type_: Groundwater,
      infiltration_threshold: 200
      infiltration_pct: 0.667
      capacity: 1.43
      area: 2.36
      datum: 0.32
  arcs:
    storm_outflow:
      name: storm_outflow
      type_: Arc
      capacity: 0.5
```

## Patches

You can make a more elaborate customisation of your WSIMOD models by using patches. Patches override the behaviour of full methods of a node. As they are fully working Python code, these patches need to be included in an **extension file**.

Extensions files are extra Python modules that will be loaded when creating a model and that contain patches for specific nodes and custom classes - see below. Extension files are defined in the config file as:

```yaml
extensions: [
  extension/file/one.py,
  extension/file/two.py
]
```

They are imported in order, something to keep in mind if the order of applying the patches matter.

Each python file can have any Python code, but it can only use the libraries and dependencies that are available in the system running WSIMOD. This means that, for maximum portability no other dependencies beyond those used by WSIMOD itself should be used in the extension files.

There are several ways in which a node can be patched. For full details, visit the [extensions reference section](./reference-extensions.md).

A very simple example of an extensions that overrides the method `pull_distributed` for node `my_node` would be:

```python
from wsimod.extensions import register_node_patch

@register_node_patch("my_node", "pull_distributed")
def empty_distributed(self, vqip):
    return self.empty_vqip()
```

Here `my_node` must be a valid node name in the model. In this case, we are indicating that in `my_node`, when calling `pull_distributted`, our custom `empty_distributted` should be used instead.

For further examples, see [customise interactions](./../demo/scripts/customise_interactions.py).

## Custom classes

The patches method is very powerful and allows for a great deal of flexibility. However, there might be cases where you need more complex customisation - for example, with multiple methods that require rewriting or that depend on each other, or if new steps for the orchestration are required.

In those cases, the simplest approach might be to create a new node class, subclassing an existing one - at the very least, subclassing `Node` if no other pre-defined node class is close enough.

For example, we might want some new `Reservoir`-style of node that has some custom behaviour for evaporation and abstractions. In that case, we could do:

```python
from wsimod.nodes.storage import Reservoir


class MyReservoir(Reservoir):

    def apply_evaporation(self):
        """Add custom functionality here."""

    def make_abstractions(self):
        """Add some further customisation here."""
```

Custom classes defined this way must be included in extension files, the same way it is done with patches, with the same rules in terms of Python packages and dependencies available to them. Also don't forget to [customise the orchestration](#custom-orchestration) to ensure that the new `apply_evaporation` function is called during simulation.
