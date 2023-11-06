# -*- coding: utf-8 -*-
"""Created on Thu Feb  2 10:37:05 2023.

@author: Barney

"""

import os

import pandas as pd

from wsimod.core.core import WSIObj
from wsimod.nodes.nutrient_pool import NutrientPool


def get_classes():
    """

    Returns:

    """

    # Function to return all loaded subclasses of WSIObj (import arcs to include that)
    def all_subclasses(cls):
        """

        Args:
            cls:

        Returns:

        """
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in all_subclasses(c)]
        )

    subclasses = all_subclasses(WSIObj)
    subclasses = {repr(x).split(".")[-1].replace("'>", ""): x for x in subclasses}
    return subclasses


def format_text(text):
    """

    Args:
        text:

    Returns:

    """
    # Convert docstring to a tidy format
    lines = text.strip().split("\n")
    lines = [line.strip().lstrip(" ") for line in lines]
    lines = [" - " + x.rstrip(" ") for x in " ".join(lines).split("- ") if len(x) > 0]
    return "<br>".join(lines)


# Identify which reference file to link modules to
reference_lookup = {}
for file in os.listdir(os.getcwd()):
    if "reference-" in file:
        with open(file) as f:
            for line in f:
                if ":::" in line:
                    reference_lookup[
                        line.replace("::: ", "").replace("\n", "")
                    ] = file.replace(".md", "")

# Iterate over classes
subclasses = get_classes()
subclasses["NutrientPool"] = NutrientPool
mytable = []
for subclass, obj in subclasses.items():
    # Get docstring
    otext = obj.__init__.__doc__
    if otext:
        # Only include docstrings with Key assumptions
        if "Key assumptions:" in otext:
            # Format reference
            rclass = ".".join(
                repr(obj).replace("<class '", "").replace("'>", "").split(".")
            )
            module = ".".join(rclass.split(".")[0:-1])
            subclass = "[`{0}`](./../{1}/#{2})".format(
                subclass, reference_lookup[module], rclass
            )

            # Format assumptions
            assum = format_text(
                otext.split("Key assumptions:")[1].split(
                    "Input data and parameter requirements:"
                )[0]
            )

            # Format inputs
            inputs = format_text(
                otext.split("Input data and parameter requirements:")[1]
            )

            # Append to table
            mytable.append(
                {"Component": subclass, "Assumptions": assum, "Data": inputs}
            )

# Convert to table
mytable = pd.DataFrame(mytable).sort_values(by="Component")
mytable["Assumptions"] = mytable["Assumptions"].str.replace("\n", "\n - ")
mytable["Component"] = mytable["Component"].str.replace("\n", "\n - ")
front_text = """
## Introduction\n
WSIMOD contains a variety of components to represent physical processes.
We recommend viewing the [API](#reference) for a detailed description of the
models included, however, we provide an overview of documented
components, their assumptions and required input data on this page.
\n\n

## Component Library
"""

# Write
with open("component-library.md", "w") as f:
    f.write(front_text)
    f.write(mytable.to_markdown(index=False))
