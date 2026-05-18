"""Tests for core.version — single source of truth from pyproject.toml."""

import tomllib
from pathlib import Path

from core.version import get_version

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_get_version_matches_pyproject() -> None:
    with (_PROJECT_ROOT / "pyproject.toml").open("rb") as f:
        expected = tomllib.load(f)["project"]["version"]
    assert get_version() == expected
