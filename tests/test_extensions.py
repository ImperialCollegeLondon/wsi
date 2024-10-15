from typing import Optional

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
    @register_node_patch("node_name", "method_name")
    def dummy_patch():
        print("Patched method")

    # Check if the patch is registered correctly
    assert extensions_registry[("node_name", "method_name", None, False)] == dummy_patch

    # Another function with other arguments
    @register_node_patch("node_name", "method_name", item="default", is_attr=True)
    def another_dummy_patch():
        print("Another patched method")

    # Check if this other patch is registered correctly
    assert (
        extensions_registry[("node_name", "method_name", "default", True)]
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
    @register_node_patch("dummy_node", "apply_overrides")
    def dummy_patch():
        pass

    # 2. Patch an attribute
    @register_node_patch("dummy_node", "t", is_attr=True)
    def another_dummy_patch(node):
        return f"A pathced attribute for {node.name}"

    # 3. Patch a method with an item
    @register_node_patch("dummy_node", "pull_set_handler", item="default")
    def yet_another_dummy_patch():
        pass

    # 4. Path a method of an attribute
    @register_node_patch("dummy_node", "dummy_arc.arc_mass_balance")
    def arc_dummy_patch():
        pass

    # Check if all patches are registered
    assert len(extensions_registry) == 4

    # Apply the patches
    apply_patches(model)

    # Verify that the patches are applied correctly
    assert (
        model.nodes[node.name].apply_overrides.__qualname__ == dummy_patch.__qualname__
    )
    assert (
        model.nodes[node.name]._patched_apply_overrides.__qualname__
        == "Node.apply_overrides"
    )
    assert model.nodes[node.name].t == another_dummy_patch(node)
    assert model.nodes[node.name]._patched_t == None
    assert (
        model.nodes[node.name].pull_set_handler["default"].__qualname__
        == yet_another_dummy_patch.__qualname__
    )
    assert (
        model.nodes[node.name].dummy_arc.arc_mass_balance.__qualname__
        == arc_dummy_patch.__qualname__
    )
    assert (
        model.nodes[node.name].dummy_arc._patched_arc_mass_balance.__qualname__
        == "Arc.arc_mass_balance"
    )


def assert_dict_almost_equal(d1: dict, d2: dict, tol: Optional[float] = None):
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

    @register_node_patch("dummy_node", "pull_distributed")
    def new_pull_distributed(self, vqip, of_type=None, tag="default"):
        return self._patched_pull_distributed(vqip, of_type=["Node"], tag=tag)

    # Apply the patches
    apply_patches(model)

    # Check appropriate result
    assert node.tank.storage["volume"] == 5
    vq = model.nodes[node.name].pull_distributed({"volume": 5})
    assert_dict_almost_equal(vq, node.empty_vqip())
    assert node.tank.storage["volume"] == 5


def test_handler_extensions(temp_extension_registry):
    from wsimod.arcs.arcs import Arc
    from wsimod.extensions import apply_patches, register_node_patch
    from wsimod.nodes import Node
    from wsimod.orchestration.model import Model

    # Create a dummy model
    node = Node("dummy_node")
    node.dummy_arc = Arc("dummy_arc", in_port=node, out_port=node)
    model = Model()
    model.nodes[node.name] = node

    # 1. Patch a handler
    @register_node_patch("dummy_node", "pull_check_handler", item="default")
    def dummy_patch(self, *args, **kwargs):
        return "dummy_patch"

    # 2. Patch a handler with access to self
    @register_node_patch("dummy_node", "pull_set_handler", item="default")
    def dummy_patch(self, vqip, *args, **kwargs):
        return f"{self.name} - {vqip['volume']}"

    apply_patches(model)

    assert node.pull_check() == "dummy_patch"
    assert node.pull_set({"volume": 1}) == "dummy_node - 1"


def test_custom_class_from_file():
    """Test a custom class."""
    from pathlib import Path
    import yaml
    import tempfile

    from wsimod.nodes.nodes import NODES_REGISTRY
    from wsimod.orchestration.model import Model, to_datetime

    # Remove in case it was in there from previous test
    NODES_REGISTRY.pop("CustomNode", None)

    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            "nodes": {"node_name": {"type_": "CustomNode", "name": "node_name"}},
            "extensions": [str(Path(__file__).parent / "custom_class.py")],
        }

        with open(temp_dir + "/config.yml", "w") as f:
            yaml.dump(config, f)

        model = Model()
        model.load(temp_dir)
        assert model.nodes["node_name"].custom_attr == 1
        model.run(dates=[to_datetime("2000-01-01")])
        assert model.nodes["node_name"].custom_attr == 2

        model.save(temp_dir, "new_config.yml")

        # Remove the custom class from the registry to test loading it again
        del model
        NODES_REGISTRY.pop("CustomNode", None)

        model = Model()
        model.load(temp_dir, "new_config.yml")
        assert model.nodes["node_name"].custom_attr == 1
        model.run(dates=[to_datetime("2000-01-01")])
        assert model.nodes["node_name"].custom_attr == 2


def test_custom_class_on_the_fly():
    """Test a custom class."""

    import tempfile

    from wsimod.nodes.nodes import Node, NODES_REGISTRY
    from wsimod.orchestration.model import Model, to_datetime

    # Remove in case it was in there from previous test
    NODES_REGISTRY.pop("CustomNode", None)

    class CustomNode(Node):
        def __init__(self, name):
            super().__init__(name)
            self.custom_attr = 1

        def end_timestep(self):
            self.custom_attr += 1
            super().end_timestep()

    with tempfile.TemporaryDirectory() as temp_dir:
        model = Model()
        model.nodes["node_name"] = CustomNode("node_name")
        model.save(temp_dir)

        del model
        model = Model()
        model.load(temp_dir)
        assert model.nodes["node_name"].custom_attr == 1
        model.run(dates=[to_datetime("2000-01-01")])
        assert model.nodes["node_name"].custom_attr == 2
