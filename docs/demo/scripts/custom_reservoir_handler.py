from wsimod.extensions import register_node_patch


@register_node_patch("my_reservoir", "pull_set_handler", item="FWTW")
def custom_pulls_fwtw(self, vqip, *args, **kwargs):
    """A custom `pull_set_handler` function.

    Pull from the storage when pulled with the tag "FWTW".
    """
    return self.tank.pull_storage(vqip)


@register_node_patch("my_reservoir", "pull_check_handler", item="FWTW")
def custom_pullc_fwtw(self, vqip, *args, **kwargs):
    """A custom `pull_check_handler` function.

    Return available storage when pulled with the tag "FWTW".
    """
    return self.tank.get_avail()


@register_node_patch("my_reservoir", "pull_set_handler", item="default")
def custom_pulls_default(self, vqip, *args, **kwargs):
    """A custom `pull_set_handler` function.

    Deny pull sets by default.
    """
    return self.pull_set_deny(vqip)


@register_node_patch("my_reservoir", "pull_check_handler", item="default")
def custom_pullc_default(self, vqip, *args, **kwargs):
    """A custom `pull_check_handler` function.

    Deny pull checks by default.
    """
    return self.pull_check_deny()
