from wsimod.extensions import register_node_patch


@register_node_patch("my_fwtw", "pull_distributed")
def custom_pull_distributed(self, vqip, *args, **kwargs):
    """A custom handler function."""
    return self._patched_pull_distributed(vqip, tag="FWTW")
