from wsimod.nodes.nodes import Node


class CustomNode(Node):
    """A custom node."""

    def __init__(self, name):
        """Initialise the node."""
        super().__init__(name)
        self.custom_attr = 1

    def end_timestep(self):
        self.custom_attr += 1
        super().end_timestep()
