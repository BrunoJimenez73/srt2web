"""
Configuration routes for SRT2Web API.
"""

import logging
import json

from fastapi import APIRouter, Request, HTTPException

from server.validators import ConfigUpdate, validate_module_dependencies

logger = logging.getLogger("srt2web.api.config")

router = APIRouter(tags=["config"])


def _ctx(request: Request) -> dict:
    return request.app.state.ctx


@router.get("/config")
async def get_config(request: Request):
    """Get current configuration."""
    ctx = _ctx(request)
    return ctx["config"].to_dict()


@router.put("/config")
async def update_config(request: Request, body: ConfigUpdate):
    """Update configuration (partial update) with dependency validation."""
    ctx = _ctx(request)
    config = ctx["config"]

    # Validate module dependencies BEFORE saving
    dependency_errors = validate_module_dependencies(body.config)
    if dependency_errors:
        raise HTTPException(
            400,
            "Configuration violates module dependencies:\n• "
            + "\n• ".join(dependency_errors),
        )

    logger.debug(f"[CONFIG] PUT receives: {json.dumps(body.config, indent=2)[:1000]}")
    logger.debug(f"[CONFIG] PUT body keys: {list(body.config.keys())}")

    try:
        config.update_from_dict(body.config)
        config.save()
        # Hot reload: force reload from disk to avoid stale cache
        config.reload()
    except ValueError as e:
        logger.warning(f"Invalid config but accepting anyway: {e}")
        return {"status": "updated", "config": config.to_dict(), "warning": str(e)}
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(500, f"Failed to save configuration: {e}")

    # Hot reload!
    pipeline = ctx["pipeline"]
    try:
        pipeline.reconfigure(config)
    except Exception as e:
        logger.error(f"Failed to reconfigure pipeline: {e}")
        raise HTTPException(500, f"Pipeline reconfiguration failed: {e}")

    return {"status": "updated", "config": config.to_dict()}


@router.post("/config/chunk")
async def update_chunk_duration(request: Request, body: dict):
    """
    Update chunk duration and synchronize all related parameters.

    Accepts: {"chunk_duration_sec": <int>}
    Syncs to:
    - config.pipeline.chunk_duration_sec
    - config.input.srt.chunk_duration_sec
    - config.modules.video_muxer.hls_segment_duration
    - config.modules.hls_output.segment_duration
    - Reconfigures running pipeline modules
    """
    ctx = _ctx(request)
    config = ctx["config"]
    pipeline = ctx["pipeline"]

    chunk_duration = body.get("chunk_duration_sec")
    if not chunk_duration:
        raise HTTPException(400, "chunk_duration_sec is required")
    if not isinstance(chunk_duration, int) or chunk_duration < 1 or chunk_duration > 60:
        raise HTTPException(400, "chunk_duration_sec must be between 1 and 60")

    # Sync to all config sections using config.set() method
    config.set("pipeline.chunk_duration_sec", chunk_duration)
    config.set("input.srt.chunk_duration_sec", chunk_duration)
    config.set("modules.video_muxer.hls_segment_duration", chunk_duration)
    config.set("modules.hls_output.segment_duration", chunk_duration)

    logger.info(f"[CHUNK] Syncing chunk_duration={chunk_duration}s to all modules")

    try:
        config.save()
        config.reload()
    except Exception as e:
        logger.error(f"[CHUNK] Failed to save config: {e}")

    # Reconfigure pipeline and modules
    try:
        pipeline.reconfigure(config)
    except Exception as e:
        logger.warning(f"[CHUNK] Pipeline reconfigure failed (may not be running): {e}")

    return {
        "status": "updated",
        "chunk_duration_sec": chunk_duration,
        "synced_to": [
            "pipeline.chunk_duration_sec",
            "input.srt.chunk_duration_sec",
            "modules.video_muxer.hls_segment_duration",
            "modules.hls_output.segment_duration",
        ],
    }
