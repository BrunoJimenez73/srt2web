"""Smoke test: mypy modules/ must pass (F75)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_mypy_modules_zero_errors() -> None:
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
