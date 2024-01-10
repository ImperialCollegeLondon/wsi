from pathlib import Path
from typing import List

from pytest import mark


def available_tutorials() -> List[Path]:
    """Locate the available tutorials in the docs."""
    base_path = Path(__file__).parent.parent / "docs" / "demo"
    return [p for p in base_path.rglob("*.py")]


@mark.parametrize("tutorial", available_tutorials())
def test_tutorials(tutorial):
    import subprocess
    import sys

    subprocess.run([sys.executable, tutorial]).check_returncode()
