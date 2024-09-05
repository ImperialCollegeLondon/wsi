import pytest


@pytest.fixture
def temp_extension_registry():
    from wsimod.extensions import extensions_registry

    bkp = extensions_registry.copy()
    extensions_registry.clear()
    yield
    extensions_registry.clear()
    extensions_registry.update(bkp)


def test_register_node_patch(temp_extension_registry):
    from wsimod.extensions import extensions_registry, register_node_patch

    # Define a dummy function to patch a node method
    @register_node_patch("node_name.method_name")
    def dummy_patch():
        print("Patched method")

    # Check if the patch is registered correctly
    assert extensions_registry[("node_name.method_name", None, False)] == dummy_patch

    # Another function with other arguments
    @register_node_patch("node_name.method_name", item="default", is_attr=True)
    def another_dummy_patch():
        print("Another patched method")

    # Check if this other patch is registered correctly
    assert (
        extensions_registry[("node_name.method_name", "default", True)]
        == another_dummy_patch
    )


def test_apply_patches(temp_extension_registry):
    from wsimod.arcs.arcs import Arc
    from wsimod.extensions import (
        apply_patches,
        extensions_registry,
        register_node_patch,
    )
    from wsimod.nodes import Node
    from wsimod.orchestration.model import Model

    # Create a dummy model
    node = Node("dummy_node")
    node.dummy_arc = Arc("dummy_arc", in_port=node, out_port=node)
    model = Model()
    model.nodes[node.name] = node

    # 1. Patch a method
    @register_node_patch("dummy_node.apply_overrides")
    def dummy_patch():
        pass

    # 2. Patch an attribute
    @register_node_patch("dummy_node.t", is_attr=True)
    def another_dummy_patch(node):
        return f"A pathced attribute for {node.name}"

    # 3. Patch a method with an item
    @register_node_patch("dummy_node.pull_set_handler", item="default")
    def yet_another_dummy_patch():
        pass

    # 4. Path a method of an attribute
    @register_node_patch("dummy_node.dummy_arc.arc_mass_balance")
    def arc_dummy_patch():
        pass

    # Check if all patches are registered
    assert len(extensions_registry) == 4

    # Apply the patches
    apply_patches(model)

    # Verify that the patches are applied correctly
    assert model.nodes[node.name].apply_overrides == dummy_patch
    assert model.nodes[node.name].t == another_dummy_patch(node)
    assert model.nodes[node.name].pull_set_handler["default"] == yet_another_dummy_patch
    assert model.nodes[node.name].dummy_arc.arc_mass_balance == arc_dummy_patch
