from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence


def get_creation_flags() -> int:
    """
    Get cross-platform subprocess creation flags.

    On Windows, returns ``CREATE_NO_WINDOW`` (0x08000000) to hide
    console windows when launching subprocesses.

    On other platforms (macOS, Linux, etc.), returns 0.
    """
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def filter_command(cmd: Sequence[str | None]) -> list[str]:
    """Drop None entries from an argv list before subprocess calls."""
    return [part for part in cmd if part is not None]
