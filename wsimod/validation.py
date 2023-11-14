import os
from pathlib import Path
from typing import Any, Optional

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
