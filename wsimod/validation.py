import ast
import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from tomllib import load


def validate_io_args(
    settings: Path, inputs: Optional[Path], outputs: Optional[Path]
) -> dict[str, Any]:
    """Validate the io arguments, including their definition in settings.

    This does not include validating the existance of data input files, which is done
    at a later stage.

    Args:
        settings (Path): The path to the file, in TOML format, containing all the
            configuration required for the simulation.
        inputs (Optional[Path]): Base directory for all input files. If present,
            overwrites value in the settings file.
        outputs (Optional[Path]): Base directory for all output files. If present,
            overwrites value in the settings file.

    Returns:
        dict[str, Any]: The loaded settings file with validated inputs and outputs.
    """
    if settings.is_dir() or not settings.exists():
        raise ValueError(
            f"The settings file at {settings.absolute()} could not be found."
        )

    with settings.open("rb") as f:
        settings_ = load(f)

    # Valildate inputs folder
    settings_["inputs"] = _validate_input_dir(settings_.get("inputs", inputs))

    # Valildate outputs folder
    settings_["outputs"] = _validate_output_dir(settings_.get("outputs", outputs))

    return settings_


def _validate_input_dir(input_dir: Optional[Path]) -> Path:
    """Validates the directory of input files.

    If not provided, the currect working directory is used.

    Args:
        input_dir (Optional[Path]): The potential directory with the inputs.

    Raises:
        ValueError: If the inputs base directory is not actually a directory.

    Returns:
        Path: The validated path containing the inputs.
    """
    if not input_dir:
        return Path.cwd().absolute()

    if not input_dir.is_dir():
        raise ValueError(
            f"The inputs base directory at {input_dir} is not a directory."
        )
    return input_dir.absolute()


def _validate_output_dir(output_dir: Optional[Path]) -> Path:
    """Validates the directory for output files.

    If not provided, the currect working directory is used. If it does not exist, it
    is created.

    Args:
        output_dir (Optional[Path]): The potential directory for the outputs.

    Raises:
        ValueError: If a file with the same name already exist.

    Returns:
        Path: The validated path containing where outputs will be saved.
    """

    if not output_dir:
        return Path.cwd().absolute()

    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"A file at {output_dir} exists and is not a directory.")

    os.makedirs(output_dir, exist_ok=True)
    return output_dir.absolute()


def load_data_into_settings(
    settings: dict[str, Any], input_dir: Path
) -> dict[str, Any]:
    """Loads data files contents into the settings dictionary.

    Search for data files to load is done recursively, walking through the whole
    settgins dictionary tree.

    Args:
        settings (dict[str, Any]): The settings dicitonary.
        input_dir (Path): The directory where input files are located.

    Returns:
        dict[str, Any]: A new settings dictionary where data files have been loaded.
    """
    loaded_settings: dict[str, Any] = {}

    for k, v in settings.items():
        if isinstance(v, dict):
            loaded_settings[k] = load_data_into_settings(v, input_dir)
        elif isinstance(v, list):
            loaded_settings[k] = [
                load_data_into_settings(item, input_dir) for item in v
            ]
        elif isinstance(v, str) and v.startswith("file:"):
            loaded_settings[k] = load_data(v.strip("file:"), input_dir)
        else:
            loaded_settings[k] = v

    return loaded_settings


def load_data(instruction: str, inputs: Path) -> pd.DataFrame:
    """Parses a string with information on how to load data, and then loads it.

    The instruction string must follow the format:

        FILENAME[:comma_separated_reading_options]

    Where the reading options must be valid input arguments to `pandas.read_csv`. For
    example, if instruction is simply `"data_file.csv"`, the reading command will be
    `pd.read_csv("data_file.csv")`. However if the instruction string is
    `"data_file.csv:sep=' ',index_col='datetime'"`, it will result in
    `pd.read_csv("data_file.csv", sep=' ', index_col='datetime')` being called.

    Args:
        instruction (str): A string detailing how to load the data.
        inputs (Path): Base directory of inputs.

    Returns:
        pd.DataFrame: Loaded dataframe following the instructions.
    """
    filename, _, options = instruction.partition(":")
    options_: dict[str, Any] = process_options(options)
    return pd.read_csv(inputs / Path(filename), **options_)


def process_options(options: str) -> dict[str, Any]:
    """Formats the options string as keyword arguments.

    >>> process_options("sep=' ',index_col='datetime'")
    {'sep': ' ', 'index_col': 'datetime'}

    Args:
        options (str): The strings with the arguments to process.

    Returns:
        dict[str, Any]: The dictionary with the processed keyword arguments.
    """
    if not options:
        return {}

    args = "f({})".format(options)
    tree = ast.parse(args)
    funccall = tree.body[0].value

    kwargs = {arg.arg: ast.literal_eval(arg.value) for arg in funccall.keywords}
    return kwargs
