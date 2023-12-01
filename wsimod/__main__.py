"""The entry point for the myproject program."""
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, cast

import pandas as pd

from wsimod.orchestration.model import Model
from wsimod.validation import assign_data_to_settings, load_data_files, validate_io_args


def create_parser() -> ArgumentParser:
    """Create the CLI argument parser."""
    parser = ArgumentParser(prog="WSIMOD")
    parser.add_argument(
        "settings",
        type=Path,
        help="Path to the WSIMOD input file, in YAML format.",
    )
    parser.add_argument(
        "--inputs",
        "-i",
        type=Path,
        help="Base directory for all input files. If present, overwrites value in the"
        " settings file.",
    )
    parser.add_argument(
        "--outputs",
        "-o",
        type=Path,
        help="Base directory for all output files. If present, overwrites value in the"
        " settings file.",
    )

    return parser


def run_model(settings: dict[str, Any], outputs: Path) -> None:
    """Runs the mode with the chosen settings and saves the outputs as csv.

    Args:
        settings (dict[str, Any]): Settings dictionary with loaded data.
        outputs(Path): Directory where to save the outputs.
    """
    model = Model()

    model.dates = cast(pd.Series, settings["dates"]).drop_duplicates()
    model.add_nodes(settings["nodes"])
    model.add_arcs(settings["arcs"])

    flows, tanks, _, surfaces = model.run()

    pd.DataFrame(flows).to_csv(outputs / "flows.csv")
    pd.DataFrame(tanks).to_csv(outputs / "tanks.csv")
    pd.DataFrame(surfaces).to_csv(outputs / "surfaces.csv")


def run() -> None:
    """Main entry point of the application."""
    args = vars(create_parser().parse_args())
    settings = validate_io_args(**args)

    inputs = settings.pop("inputs")
    outputs = settings.pop("outputs")
    loaded_data = load_data_files(settings.pop("data", {}), inputs)
    loaded_settings = assign_data_to_settings(settings, loaded_data)

    run_model(loaded_settings, outputs)


if __name__ == "__main__":
    run()
