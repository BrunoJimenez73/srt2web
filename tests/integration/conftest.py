"""
Integration test configuration and fixtures.

F109: Provides session-level autouse cleanup of debris in ``./output/`` so
that tests which accidentally read from the real output directory (before
they were updated to inject ``output_dir=tmp_path`` via ``_make_client``)
start from a clean state.

This is intentionally conservative: we only delete known debris patterns
(empty 0-byte recordings, leftover HLS placeholders), never the real
``config.yaml``, ``logs/`` or any user data.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


_DEBRIS_FILENAMES = {
    "test_recording.mp4",
    "test_recording.ts",
    "test_recording.wav",
}


def _is_empty_file(p: Path) -> bool:
    """Return True if the file is empty (0 bytes) — strong debris indicator."""
    try:
        return p.is_file() and p.stat().st_size == 0
    except OSError:
        return False


def _is_obvious_debris(p: Path) -> bool:
    """Detect obvious test debris by name and emptiness."""
    return p.name in _DEBRIS_FILENAMES or _is_empty_file(p)


@pytest.fixture(autouse=True, scope="session")
def _clean_runtime_debris() -> None:
    """Session-scope autouse: clean obvious debris from ``./output/`` once.

    F109: ensures the test session starts clean. Tests that need isolated
    paths MUST use ``tmp_path`` via ``_make_client(output_dir=...)``; this
    fixture is a safety net for tests that haven't been migrated yet.
    """
    if not OUTPUT_DIR.exists():
        return

    cleaned = []
    try:
        for pattern in ("recordings/*", "subtitles/subs.m3u8", "subtitles/subs.vtt"):
            for path in OUTPUT_DIR.glob(pattern):
                if not path.exists() or path.is_dir():
                    continue
                if _is_obvious_debris(path):
                    try:
                        path.unlink()
                        cleaned.append(str(path.relative_to(PROJECT_ROOT)))
                    except OSError:
                        pass
    except OSError:
        # If the output dir is locked or missing, skip silently
        # (test still runs; this is best-effort cleanup).
        if os.name != "nt":
            raise

    if cleaned:
        # Surface cleanup so debugging is easy
        print(f"\n[F109 cleanup] Removed {len(cleaned)} debris file(s): {cleaned}")
