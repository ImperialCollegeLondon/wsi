"""Extensions module for decorators and subclasses.

Example use for decorators:
>>> from wsimod.extensions import extensions as extend
>>> @extend.node_attribute(obj=my_fwtw, attribute_name="pull_distributed")
>>> def new_distributed(pull_distributed, vqip):
>>>      return pull_distributed(vqip, tag="FWTW")
"""


def node_attribute(obj, attribute_name: str):
    """
    Decorator to extend or modify a node attribute.

    Args:
        obj: The node object whose attribute should be modified.
        attribute_name (str): The name of the attribute to modify.

    Returns:
        A decorator function that takes the extension function as an argument.
    """

    def decorator(func: callable):
        """
        Decorator function that applies the extension function to the node attribute.

        Args:
            func (callable): The extension function that modifies the node attribute.
        """
        attribute = getattr(obj, attribute_name)

        def wrapped_attribute(*args, **kwargs):
            return func(attribute, *args, **kwargs)

        setattr(obj, attribute_name, wrapped_attribute)
        return wrapped_attribute

    return decorator
