"""Project version — single source of truth is pyproject.toml."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from core.paths import get_project_root

_PYPROJECT = get_project_root() / "pyproject.toml"


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return package version from installed metadata or pyproject.toml."""
    try:
        from importlib.metadata import version

        return version("srt2web")
    except Exception:
        with _PYPROJECT.open("rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        ver = project.get("version")
        if isinstance(ver, str) and ver:
            return ver
        raise RuntimeError("version not found in pyproject.toml") from None
