"""Smoke test: mypy modules/ must pass (F75)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _mypy_executable() -> bool:
    """Probe whether mypy can run at all (DLL/OS policy may block it)."""
    probe = subprocess.run(
        [sys.executable, "-m", "mypy", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


def test_mypy_modules_zero_errors() -> None:
    if not _mypy_executable():
        pytest.skip("mypy is not executable in this environment (blocked by OS policy or missing)")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "modules/",
            "--config-file",
            str(PROJECT_ROOT / "pyproject.toml"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
