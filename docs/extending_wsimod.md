# Extending and customising WSIMOD functionality

WSIMOD has many features built-in, but undoubtedly, to model real life scenarios, you will
need to customise it to your specific needs.

WSIMOD offers 3 ways of doing this customisation of increased complexity - and flexibility:
overrides, patches and custom classes.

## Overrides

[**NOTE**: I have not seen this in action in any example or demo, and `apply_overrides` does not seem to be used ever, so it is unclear how this is actually used.]

Overrides are the most direct way of customising the behaviour of nodes or arcs. They enable specifying the value of one or more parameters of a specific - existing - node or arc. These overrides are specified in the config file for the model under a `overrides` section, and therefore they need to be objects that can be parsed in yaml - strings, floats, etc.

## Patches

You can make a more elaborate customisation of your WSIMOD models by using patches. Patches override the behaviour of full methods of a node. As they are fully working Python code, these patches need to be included in an **extension file**.

Extensions files are extra Python modules that will be loaded when creating a model and that contain patches for specific nodes and custom classes - see below. Extension files are defined in the config file as:

```yaml
extensions = [
  "extension/file/one.py",
  "extension/file/two.py"
]
```

They are imported in order, something to keep in mind if the order of applying the patches matter.

Each python file can have any Python code, but it can only use the libraries and dependencies that are available in the system running WSIMOD. This means that, for maximum portability no other dependencies beyond those used by WSIMOD should be used in the extension files.

There are several ways in which a node can be patched. For full details, visit the [extensions reference section](./reference-extensions.md).

A very simple example of an extensions that overrides the method `pull_distributed` for node `my_node` would be:

```python
from wsimod.extensions import register_node_patch

@register_node_patch("my_node", "pull_distributed")
def empty_distributed(self, vqip):
    return self.empty_vqip()
```

Here `my_node` must be a valid node name in the model. In this case, we are indicating that in `my_node`, when calling `pull_distributted`, our custom `empty_distributted` should be used instead.

## Custom classes

The patches method is very powerful and allows for a great deal of flexibility. However, there might be cases where you need more complex customisation - for example, with multiple methods that require rewriting or that depend on each other.

In those cases, the simplest approach might be to create a new node class, subclassing an existing one - at the very least, subclassing `Node` if no other pre-defined node class is close enough.

For example, we might want some new `Land`-style of node that has some custom behaviour for irrigation and the direction arcs. In that case, we could do:

```python
from wsimod.nodes import Land


class MyLand(Land):

    def apply_irrigation(self):
        """Add custom functionality here."""

    def get_direction_arcs(self, direction, of_type=None):
        """Add some further customisation here."""
```

Custom classes defined this way must be included in extension files, the same way it is done with patches, with the same rules in terms of Python packages and dependencies available to them.
