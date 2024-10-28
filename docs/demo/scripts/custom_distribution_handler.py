from wsimod.extensions import register_node_patch


@register_node_patch("my_dist", "push_check_handler", item="Node")
def custom_handler_function(self, vqip, *args, **kwargs):
    """A custom `push_check_handler` function.

    Call the default handler for the "Node" item.
    """
    print("I reached a custom handler")
    return self.push_check_handler["default"](vqip)
