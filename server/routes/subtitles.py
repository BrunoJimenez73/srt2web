"""Subtitle rail routes (F205) — JSON feed for the client-side overlay.

The web player no longer depends on HLS-native WebVTT delivery: it polls
this endpoint and renders cues itself using hls.js's own video positions
as the clock. Public data (same content as /subtitles/*.vtt).
"""

import logging
from typing import Any, cast

from fastapi import APIRouter, Query, Request

from server.ctx import get_ctx as _ctx

logger = logging.getLogger("srt2web.api.subtitles")

router = APIRouter(tags=["subtitles"])


@router.get("/subtitles/recent")
async def recent_subtitles(
    request: Request,
    count: int = Query(default=16, ge=1, le=64),
) -> dict[str, Any]:
    """Return the last ``count`` subtitle chunks for the overlay renderer."""
    ctx = _ctx(request)
    pipeline = ctx.get("pipeline")
    module = pipeline.get_module("subtitle_generator") if pipeline else None
    writer = getattr(module, "_fragment_writer", None)
    if writer is None:
        return {"base": 0, "chunks": []}
    return cast("dict[str, Any]", writer.get_recent(count=count))
