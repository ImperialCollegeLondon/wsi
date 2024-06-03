def model_attribute(obj, attribute_name):
    """
    Decorator to extend or modify a model attribute.

    Args:
        obj: The model object whose attribute should be modified.
        attribute_name (str): The name of the attribute to modify.

    Returns:
        A decorator function that takes the extension function as an argument.
    """
    def decorator(func):
        """
        Decorator function that applies the extension function to the model attribute.

        Args:
            func: The extension function that modifies the model attribute.
        """
        attribute = getattr(obj, attribute_name)
        
        def wrapped_attribute(*args, **kwargs):
            return func(attribute, *args, **kwargs)

        setattr(obj, attribute_name, wrapped_attribute)
        return wrapped_attribute

    return decorator