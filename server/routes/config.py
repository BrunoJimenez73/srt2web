"""
Configuration routes for SRT2Web API.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from core.cache import cached, invalidate_cache
from server.validators import ChunkDurationRequest, ConfigUpdate, validate_module_dependencies

logger = logging.getLogger("srt2web.api.config")

router = APIRouter(tags=["config"])


def _ctx(request: Request) -> dict[str, Any]:
    return request.app.state.ctx  # type: ignore[no-any-return]


# ── Preset Endpoints (F19) ──────────────────────────────────────────


@router.get("/presets")
async def list_presets(request: Request) -> dict[str, Any]:
    """List all saved presets (including built-in ones)."""
    ctx = _ctx(request)
    config = ctx["config"]

    # Get saved presets
    saved = config.list_presets()

    # Add built-in presets
    built_in = config.built_in_presets()
    built_in_list = [
        {
            "name": name,
            "description": data["description"],
            "built_in": True,
            "config_keys": list(data["config"].keys()),
        }
        for name, data in built_in.items()
    ]

    return {"presets": saved + built_in_list}


@router.post("/presets")
async def save_preset(request: Request) -> dict[str, Any]:
    """Save current configuration as a named preset."""
    from pydantic import BaseModel

    class PresetSaveRequest(BaseModel):
        name: str
        description: str = ""

    ctx = _ctx(request)
    config = ctx["config"]
    body = PresetSaveRequest(**await request.json())

    if not body.name:
        raise HTTPException(400, "Preset name is required")

    # Reserved names
    if body.name.startswith("_"):
        raise HTTPException(400, "Preset name cannot start with '_'")

    config.save_preset(body.name, body.description)
    return {"status": "saved", "name": body.name}


@router.post("/presets/{name}/apply")
async def apply_preset(request: Request, name: str) -> dict[str, Any]:
    """Apply a preset (built-in or saved) to the current config."""
    ctx = _ctx(request)
    config = ctx["config"]
    pipeline = ctx["pipeline"]

    # Try built-in first
    built_in = config.built_in_presets()
    if name in built_in:
        preset_config = built_in[name]["config"]
    else:
        # Try saved preset
        try:
            preset_config = config.load_preset(name)
        except KeyError:
            raise HTTPException(404, f"Preset '{name}' not found")

    # Apply the preset config (merge with current, then validate)
    try:
        config.update_from_dict(preset_config)
        config.save()
        config.reload()
    except ValueError as e:
        raise HTTPException(400, f"Invalid preset configuration: {e}")

    # Reconfigure pipeline if running
    try:
        pipeline.reconfigure(config)
    except Exception as e:
        logger.warning(f"Pipeline reconfigure failed after preset apply: {e}")

    return {"status": "applied", "name": name, "config": config.to_dict()}


@router.delete("/presets/{name}")
async def delete_preset(request: Request, name: str) -> dict[str, Any]:
    """Delete a saved preset by name."""
    ctx = _ctx(request)
    config = ctx["config"]

    # Cannot delete built-in presets
    built_in = config.built_in_presets()
    if name in built_in:
        raise HTTPException(400, "Cannot delete built-in presets")

    try:
        config.delete_preset(name)
    except KeyError:
        raise HTTPException(404, f"Preset '{name}' not found")

    return {"status": "deleted", "name": name}


# ── Existing Config Endpoints ────────────────────────────────────────


@router.get("/config")
@cached("config", ttl_seconds=5)
async def get_config(request: Request) -> dict[str, Any]:
    """Get current configuration."""
    ctx = _ctx(request)
    return ctx["config"].to_dict()  # type: ignore[no-any-return]


@router.put("/config")
async def update_config(request: Request, body: ConfigUpdate) -> dict[str, Any]:
    """Update configuration (partial update) with dependency validation."""
    ctx = _ctx(request)
    config = ctx["config"]

    # Validate module dependencies BEFORE saving
    dependency_errors = validate_module_dependencies(body.config)
    if dependency_errors:
        raise HTTPException(
            400,
            "Configuration violates module dependencies:\n• " + "\n• ".join(dependency_errors),
        )

    logger.debug(f"[CONFIG] PUT receives: {json.dumps(body.config, indent=2)[:1000]}")
    logger.debug(f"[CONFIG] PUT body keys: {list(body.config.keys())}")

    try:
        config.update_from_dict(body.config)
        config.save()
        config.reload()
    except ValueError as e:
        logger.warning(f"Invalid config but accepting anyway: {e}")
        invalidate_cache("config")
        invalidate_cache("status")
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

    invalidate_cache("config")
    invalidate_cache("status")
    return {"status": "updated", "config": config.to_dict()}


@router.post("/config/chunk")
async def update_chunk_duration(request: Request, body: ChunkDurationRequest) -> dict[str, Any]:
    """
    Update chunk duration and synchronize all related parameters.

    Accepts: {"chunk_duration_sec": <int>}
    Syncs to:
    - config.pipeline.chunk_duration_sec
    - config.input.*.chunk_duration_sec
    - config.output.web|hls.segment_duration + list_size
    - config.modules.video_muxer.hls_segment_duration + list_size
    - config.modules.subtitle_generator.chunk_duration
    - named outputs with type web/hls
    - Reconfigures running pipeline modules
    """
    ctx = _ctx(request)
    config = ctx["config"]
    pipeline = ctx["pipeline"]

    chunk_duration = body.chunk_duration_sec
    # Validación de rango: 2-30 segundos
    if chunk_duration < 2 or chunk_duration > 30:
        raise HTTPException(400, f"chunk_duration_sec debe estar entre 2 y 30 segundos (recibido: {chunk_duration})")
    chunk_duration = max(2, min(chunk_duration, 30))

    # Calculate list_size for stable HLS buffer (at least 60s, min 6 segments)
    buffer_target_sec = 60
    calculated_list_size = max(6, (buffer_target_sec + chunk_duration - 1) // chunk_duration)

    # Sync pipeline
    config.set("pipeline.chunk_duration_sec", chunk_duration)
    config.set("pipeline.mode", "thread_parallel")
    config.set("pipeline.max_concurrent_chunks", 4)
    # Sync input types
    config.set("input.srt.chunk_duration_sec", chunk_duration)
    config.set("input.rtmp.chunk_duration_sec", chunk_duration)
    config.set("input.file.chunk_duration_sec", chunk_duration)
    # Sync web/hls output (passthrough para evitar recodificación)
    config.set("output.web.segment_duration", chunk_duration)
    config.set("output.web.list_size", calculated_list_size)
    config.set("output.web.encoder_mode", "passthrough")
    config.set("output.hls.segment_duration", chunk_duration)
    config.set("output.hls.list_size", calculated_list_size)
    config.set("output.hls.encoder_mode", "passthrough")
    # Sync video_muxer
    config.set("modules.video_muxer.hls_segment_duration", chunk_duration)
    config.set("modules.video_muxer.hls_list_size", calculated_list_size)
    config.set("modules.video_muxer.encoder_mode", "passthrough")
    # Sync subtitle generator
    config.set("modules.subtitle_generator.chunk_duration", chunk_duration)
    # Sync named outputs (handled by schema validator on save/reload)

    logger.info(
        f"[CHUNK] Syncing chunk_duration={chunk_duration}s, " f"list_size={calculated_list_size} to all modules"
    )

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

    invalidate_cache("config")
    invalidate_cache("status")
    return {
        "status": "updated",
        "chunk_duration_sec": chunk_duration,
        "list_size": calculated_list_size,
        "buffer_sec": chunk_duration * calculated_list_size,
        "encoder_mode": "passthrough",
        "pipeline_mode": "thread_parallel",
        "synced_to": [
            "pipeline.chunk_duration_sec",
            "pipeline.mode",
            "pipeline.max_concurrent_chunks",
            "input.srt/rtmp/file.chunk_duration_sec",
            "output.web/hls.segment_duration",
            "output.web/hls.list_size",
            "output.web/hls.encoder_mode",
            "modules.video_muxer.hls_segment_duration",
            "modules.video_muxer.hls_list_size",
            "modules.video_muxer.encoder_mode",
            "modules.subtitle_generator.chunk_duration",
        ],
    }
