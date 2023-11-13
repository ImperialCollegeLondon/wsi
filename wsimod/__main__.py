"""The entry point for the myproject program."""
from argparse import ArgumentParser
from pathlib import Path


def create_parser() -> ArgumentParser:
    """Create the CLI argument parser."""
    parser = ArgumentParser(prog="WSIMOD")
    parser.add_argument(
        "settings",
        type=Path,
        help="Path to the WSIMOD input file, in TOML format.",
    )
    parser.add_argument(
        "--inputs",
        "-i",
        type=Path,
        help="Base location for all input files. Default to 'inputs/'.",
        default=Path.cwd() / "inputs",
    )
    parser.add_argument(
        "--outputs",
        "-o",
        type=Path,
        help="Base location for all output files. Default to 'outputs/'.",
        default=Path.cwd() / "outputs",
    )
    parser.add_argument(
        "--force",
        "-f",
        type=bool,
        help="Overwrite output directory, if exists. Default to False.",
        default=False,
    )

    return parser


def run() -> None:
    """Main entry point of the application."""
    args = vars(create_parser().parse_args())
    print(f"Running WSIMOD with these arguments: {args}")
