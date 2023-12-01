from pytest import mark
from pathlib import Path
import subprocess


def collect_examples() -> list[Path]:
    root = Path.cwd() / "docs" / "demo" / "examples"
    return list(root.glob("**/*.yaml"))


@mark.parametrize("example", collect_examples())
def test_examples(example: Path, tmp_path: Path) -> None:
    result = subprocess.run(
        f"wsimod {str(example)} -o {str(tmp_path)}",
        shell=True,
        check=True,
    )
    assert (tmp_path / "flows.csv").exists()
    assert (tmp_path / "tanks.csv").exists()
    assert (tmp_path / "surfaces.csv").exists()
