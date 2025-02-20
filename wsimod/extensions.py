"""This module contains the utilities to extend WSMOD with new features.

The `register_node_patch` decorator is used to register a function that will be used
instead of a method or attribute of a node. The `apply_patches` function applies all
registered patches to a model.

Example of patching a method:

`empty_distributed` will be called instead of `pull_distributed` of "my_node":

    >>> from wsimod.extensions import register_node_patch, apply_patches
    >>> @register_node_patch("my_node", "pull_distributed")
    >>> def empty_distributed(self, vqip):
    >>>      return {}

Attributes, methods of the node, and sub-attributes can be patched. Also, an item of a
list or a dictionary can be patched if the item argument is provided.

Example of patching an attribute:

`10` will be assigned to `t`:

    >>> @register_node_patch("my_node", "t", is_attr=True)
    >>> def patch_t(node):
    >>>     return 10

Example of patching an attribute item:

`patch_default_pull_set_handler` will be assigned to
`pull_set_handler["default"]`:

    >>> @register_node_patch("my_node", "pull_set_handler", item="default")
    >>> def patch_default_pull_set_handler(self, vqip):
    >>>     return {}

If patching a method of an attribute, the `is_attr` argument should be set to `True` and
the target should include the attribute name and the method name, all separated by
periods, eg. `attribute_name.method_name`.

It should be noted that the patched function should have the same signature as the
original method or attribute, and the return type should be the same as well, otherwise
there will be a runtime error. In particular, the first argument of the patched function
should be the node object itself, which will typically be named `self`.

The overridden method or attribute can be accessed within the patched function using the
`_patched_{method_name}` attribute of the object, eg. `self._patched_pull_distributed`.
The exception to this is when patching an item, in which case the original item is no
available to be used within the overriding function.

Finally, the `apply_patches` is called within the `Model.load` method and will apply all
patches in the order they were registered. This means that users need to be careful with
the order of the patches in their extensions files, as they may have interdependencies.

TODO: Update documentation on extensions files.
"""

import warnings
from typing import Callable, Hashable

from .orchestration.model import Model

extensions_registry: dict[tuple[str, Hashable, bool], Callable] = {}


def register_node_patch(
    node_name: str, target: str, item: Hashable = None, is_attr: bool = False
) -> Callable:
    """Register a function to patch a node method or any of its attributes.

    Args:
        node_name (str): The name of the node to patch.
        target (str): The target of the object to patch in the form of a string with the
            attribute, sub-attribute, etc. and finally method (or attribute) to replace,
            sepparated with period, eg. `make_discharge` or
            `sewer_tank.pull_storage_exact`.
        item (Hashable): Typically a string or an integer indicating the item to replace
            in the selected attribue, which should be a list or a dictionary.
        is_attr (bool): If True, the decorated function will be called when applying
            the patch and the result assigned to the target, instead of assigning the
            function itself. In this case, the only argument passed to the function is
            the node object.
    """
    target_id = (node_name, target, item, is_attr)
    if target_id in extensions_registry:
        warnings.warn(f"Patch for {target} already registered.")

    def decorator(func):
        extensions_registry[target_id] = func
        return func

    return decorator


def apply_patches(model: Model) -> None:
    """Apply all registered patches to the model.

    TODO: Validate signature of the patched methods and type of patched attributes.

    Args:
        model (Model): The model to apply the patches to.
    """
    for (node_name, target, item, is_attr), func in extensions_registry.items():
        starget = target.split(".")
        method = starget.pop()

        # Get the member to patch
        node = obj = model.nodes[node_name]
        for attr in starget:
            obj = getattr(obj, attr)

        # Apply the patch
        if item is not None:
            obj = getattr(obj, method)
            obj[item] = func(node) if is_attr else func.__get__(node, node.__class__)
        else:
            setattr(obj, f"_patched_{method}", getattr(obj, method))
            setattr(
                obj, method, func(node) if is_attr else func.__get__(obj, obj.__class__)
            )
