from __future__ import annotations

import subprocess
import sys


def get_creation_flags() -> int:
    """
    Get cross-platform subprocess creation flags.

    On Windows, returns ``CREATE_NO_WINDOW`` (0x08000000) to hide
    console windows when launching subprocesses.

    On other platforms (macOS, Linux, etc.), returns 0.
    """
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0
