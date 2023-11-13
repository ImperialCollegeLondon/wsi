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
    parser.add_argument(
        "--force-output",
        "-f",
        type=bool,
        help="Overwrite contents of output directory, if it exists. Default to False.",
        default=False,
    )

    return parser


def run() -> None:
    """Main entry point of the application."""
    args = vars(create_parser().parse_args())
    print(f"Running WSIMOD with these arguments: {args}")
