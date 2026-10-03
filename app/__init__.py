"""Gold Queen API application package."""

import tomllib
from pathlib import Path


def _read_project_version() -> str:
    """Return ``[project].version`` from pyproject.toml, the only copy."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject.open("rb") as handle:
        document = tomllib.load(handle)
    return str(document["project"]["version"])


__version__ = _read_project_version()
