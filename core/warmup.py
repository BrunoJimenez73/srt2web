"""F183: Background model warm-up at server startup.

The first pipeline start pays heavy one-time costs:
  - ``import argostranslate.translate``  (~30s: first import downloads/extracts)
  - ``import faster_whisper``            (fast, but still CPU-bound)

These happen once per process and make the first ``POST /api/start`` block
the event loop for tens of seconds. ``prewarm_models()`` spawns a daemon
thread at server startup that imports everything ahead of time, so by the
time the user clicks Start the imports are already in ``sys.modules`` and
pipeline init takes seconds instead of ~40s+.

Everything here is best-effort: any failure is logged and ignored — the
pipeline falls back to the regular (slow) lazy path naturally.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("srt2web.warmup")

_warmup_lock = threading.Lock()
_warmup_started = False


def _safe_import(label: str, import_fn: Callable[[], Any]) -> None:
    """Run a single import, logging duration and failures."""
    import time

    t0 = time.monotonic()
    try:
        import_fn()
        logger.debug("Warmup: %s ready in %.1fs", label, time.monotonic() - t0)
    except Exception as exc:  # best effort by design
        logger.warning("Warmup: %s failed (pipeline will load it lazily): %s", label, exc)


def _warmup_worker() -> None:
    """Daemon thread body — runs the expensive one-time imports."""
    _safe_import("argostranslate", lambda: __import__("argostranslate").translate)
    _safe_import("faster_whisper", lambda: __import__("faster_whisper"))


def prewarm_models(service: str = "srt2web") -> None:
    """Start the one-time warm-up in a daemon thread (idempotent).

    Safe to call from any startup hook (server entry point, tests). In
    testing mode the warm-up is skipped to keep the test suite fast and
    deterministic — the models are never required by unit tests.
    """
    global _warmup_started
    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True

    if service == "srt2web":
        import os

        if os.environ.get("SRT2WEB_TESTING"):
            logger.debug("Warmup skipped (SRT2WEB_TESTING)")
            return

    t = threading.Thread(target=_warmup_worker, name="srt2web-warmup", daemon=True)
    t.start()
    logger.info("Model warm-up started in background thread")
