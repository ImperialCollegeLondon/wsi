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


def assert_dict_almost_equal(d1: dict, d2: dict, tol: float | None = None):
    """Check if two dictionaries are almost equal.

    Args:
        d1 (dict): The first dictionary.
        d2 (dict): The second dictionary.
        tol (float | None, optional): Relative tolerance. Defaults to 1e-6,
            `pytest.approx` default.
    """
    for key in d1.keys():
        assert d1[key] == pytest.approx(d2[key], rel=tol)


def test_path_method_with_reuse(temp_extension_registry):
    from functools import partial
    from wsimod.arcs.arcs import Arc
    from wsimod.extensions import apply_patches, register_node_patch
    from wsimod.nodes.storage import Reservoir
    from wsimod.orchestration.model import Model

    # Create a dummy model
    node = Reservoir(name="dummy_node", initial_storage=10, capacity=10)
    node.dummy_arc = Arc("dummy_arc", in_port=node, out_port=node)

    vq = node.pull_distributed({"volume": 5})
    assert_dict_almost_equal(vq, node.v_change_vqip(node.empty_vqip(), 5))

    model = Model()
    model.nodes[node.name] = node

    @register_node_patch("dummy_node.pull_distributed")
    def new_pull_distributed(self, vqip, of_type=None, tag="default"):
        return self._patched_pull_distributed(vqip, of_type=["Node"], tag=tag)

    # Apply the patches
    apply_patches(model)

    # Check appropriate result
    assert node.tank.storage["volume"] == 5
    vq = model.nodes[node.name].pull_distributed({"volume": 5})
    assert_dict_almost_equal(vq, node.empty_vqip())
    assert node.tank.storage["volume"] == 5
