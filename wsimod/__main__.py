"""The entry point for the myproject program."""
from argparse import ArgumentParser


def create_parser() -> ArgumentParser:
    """Create the CLI argument parser."""
    parser = ArgumentParser(prog="WSIMOD")

    return parser


def run() -> None:
    """Main entry point of the application."""
    args = vars(create_parser().parse_args())
    print(f"Running WSIMOD with these arguments: {args}")
