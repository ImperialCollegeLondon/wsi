import ast
import os
from pathlib import Path
from typing import Any, Literal, Optional, Union

import pandas as pd
import yaml

from wsimod.core import constants


def evaluate_input_file(settings: Path) -> Literal["saved", "custom"]:
    """Decides what type of input file we are dealing with.

    "save" correspond to fully constructed models which have been saved, alongside
    any necessary data files. "custom" are input files constructed manually.

    Raises:
        ValueError: If the settings file do not exist.

    Return:
        If the input file is a saved model file or a custom input.
    """
    if settings.is_dir() or not settings.exists():
        raise ValueError(
            f"The settings file at {settings.absolute()} could not be found."
        )

    with settings.open("rb") as f:
        settings_ = yaml.safe_load(f)

    if set(["data", "inputs", "outputs"]).isdisjoint(settings_.keys()):
        return "saved"

    return "custom"


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
        settings_ = yaml.safe_load(f)

    # Valildate inputs folder
    settings_["inputs"] = _validate_input_dir(
        inputs if inputs else settings_.get("inputs", None), default=settings.parent
    )

    # Valildate outputs folder
    settings_["outputs"] = _validate_output_dir(
        outputs if outputs else settings_.get("outputs", None), default=settings.parent
    )

    return settings_


def _validate_input_dir(input_dir: Optional[Path], default: Path) -> Path:
    """Validates the directory of input files.

    If not provided, the default directory is used.

    Args:
        input_dir (Optional[Path]): The potential directory with the inputs.
        default (Path): Default input path if none provided.

    Raises:
        ValueError: If the inputs base directory is not actually a directory.

    Returns:
        Path: The validated path containing the inputs.
    """
    if not input_dir:
        return default.absolute()

    input_dir = Path(input_dir).absolute()
    if not input_dir.is_dir():
        raise ValueError(
            f"The inputs base directory at {input_dir} is not a directory."
        )
    return input_dir


def _validate_output_dir(output_dir: Optional[Path], default: Path) -> Path:
    """Validates the directory for output files.

    If not provided, the default path is used. If it does not exist, it is created.

    Args:
        output_dir (Optional[Path]): The potential directory for the outputs.
        default (Path): Defualt output path if none provided.

    Raises:
        ValueError: If a file with the same name already exist.

    Returns:
        Path: The validated path containing where outputs will be saved.
    """
    if not output_dir:
        return default.absolute()

    output_dir = Path(output_dir).absolute()
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"A file at {output_dir} exists and is not a directory.")

    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def load_data_files(
    data_settings: dict[str, Any], input_dir: Path
) -> dict[str, Union[pd.DataFrame, pd.Series, dict]]:
    """Reads the settings data section and reads the required data from files.

    Args:
        data_settings (dict[str, Any]): The data section of the settings file.
        input_dir (Path): The directory where input files are located.

    Returns:
        dict[str, Union[pd.DataFrame, pd.Series, dict]]: Loaded dataframe, series or
        dictionary following the instructions.
    """
    return {
        f"data:{key}": read_data(var, input_dir) for key, var in data_settings.items()
    }


def assign_data_to_settings(
    settings: dict[str, Any],
    data_settings: dict[str, Union[pd.DataFrame, pd.Series, dict]],
) -> dict[str, Any]:
    """Assigns the data files to the right variables in the settings dictionary.

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
            loaded_settings[k] = assign_data_to_settings(v, data_settings)
        elif isinstance(v, list):
            loaded_settings[k] = [
                assign_data_to_settings(item, data_settings) for item in v
            ]
        elif isinstance(v, str) and v.startswith("data:"):
            try:
                loaded_settings[k] = data_settings[v]
            except KeyError:
                raise ValueError(
                    f"{v} could not be found. Did you configure loading that data in"
                    " the data section of the settings file?"
                )
        else:
            loaded_settings[k] = v

    return loaded_settings


def read_data(
    instructions: dict[str, Any], inputs: Path
) -> Union[pd.DataFrame, pd.Series, dict]:
    """Uses the instructions to load tabular data.

    The instructions are a dictionary of options that define what file to load, how
    to load it and some simple manipulations to do to the loaded pandas Dataframe
    before returing it.

    The keys to control this proces are:

        filename: Filename of the data to load
        filter (optional): List of filters for the dataframe, each a dictionary in the
            form:
            where: column to filer
            is: value of that column
        scaling (optional): List of variable scaling, each a dictionary of the form:
            where: column to filer (optional)
            is: value of that column (optional)
            variable: name of the column to scale
            factor: unit conversion factor, as defined in `wsimod.core.constants`,
                eg. MM_TO_M
        format (optional): How the output should be provided. If format is `dict` then
            the output is provided as a dictonary, otherwise a Dataframe or a Series
            (if there is only 1 column) is output.
        index (optional): Column(s) to use as index.
        output (optional): Column to provide as output.
        options (optional): Options to pass to the `pandas.read_csv` function.

    The order in which operations are done is:

        read -> filter -> scale -> set_index -> select_output -> convert_format

    Only the `read` step will always happen. The others depend on the inputs.

    Args:
        instructions (str): A dictionary with instructions to load the data.
        inputs (Path): Base directory of inputs.

    Returns:
        Union[pd.DataFrame, pd.Series, dict]: Loaded dataframe, series or dictionary
        following the instructions.
    """
    filename = inputs / Path(instructions["filename"])
    options_: dict[str, Any] = process_options(instructions.get("options", ""))
    data = pd.read_csv(inputs / Path(filename), **options_)

    for filter in instructions.get("filters", []):
        data = data.loc[data[filter["where"]] == filter["is"]]

    for scaler in instructions.get("scaling", []):
        idx = data[scaler["where"]] == scaler["is"] if "is" in scaler else slice(None)
        factor = (
            getattr(constants, scaler["factor"])
            if isinstance(scaler["factor"], str)
            else scaler["factor"]
        )
        data.loc[idx, scaler["variable"]] *= factor

    if index := instructions.get("index", None):
        data = data.set_index(index)

    if output := instructions.get("output", None):
        data = data[output]

    if isinstance(data, pd.DataFrame) and len(data.columns) == 1:
        data = data.squeeze()

    if instructions.get("format", "") == "dict":
        return data.to_dict()

    return data


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
