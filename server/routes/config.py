"""
Configuration routes for SRT2Web API.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.cache import cached, invalidate_cache
from server.ctx import get_ctx as _ctx
from server.validators import ChunkDurationRequest, ConfigUpdate, validate_module_dependencies

logger = logging.getLogger("srt2web.api.config")

router = APIRouter(tags=["config"])


class PresetSaveRequest(BaseModel):
    name: str
    description: str = ""


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
    ctx = _ctx(request)
    config = ctx["config"]
    body = PresetSaveRequest(**await request.json())

    if not body.name:
        raise HTTPException(400, "Preset name is required")

    # Reserved names
    if body.name.startswith("_"):
        raise HTTPException(400, "Preset name cannot start with '_'")

    # F161: Sanitize preset name to prevent path traversal
    import re

    if not re.match(r"^[a-zA-Z0-9_\-. ]+$", body.name) or ".." in body.name:
        raise HTTPException(400, "Preset name contains invalid characters")

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
        except KeyError as exc:
            raise HTTPException(404, f"Preset '{name}' not found") from exc

    # Apply the preset config (merge with current, then validate)
    try:
        config.update_from_dict(preset_config)
        config.save()
        config.reload()
    except ValueError as e:
        raise HTTPException(400, f"Invalid preset configuration: {e}") from e

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
    except KeyError as exc:
        raise HTTPException(404, f"Preset '{name}' not found") from exc

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
        logger.warning(f"Config validation failed: {e}")
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        logger.error("Failed to save config: %s", e)
        # F161: Return generic message to avoid leaking internal details
        raise HTTPException(500, "Failed to save configuration") from e

    # Hot reload!
    pipeline = ctx["pipeline"]
    try:
        pipeline.reconfigure(config)
    except Exception as e:
        logger.error("Failed to reconfigure pipeline: %s", e)
        # F161: Return generic message to avoid leaking internal details
        raise HTTPException(500, "Pipeline reconfiguration failed") from e

    invalidate_cache("config")
    invalidate_cache("status")
    return {"status": "updated", "config": config.to_dict()}


@router.put("/config/video_muxer")
async def update_video_muxer_config(request: Request) -> dict[str, Any]:
    """Update video muxer configuration from flat key-value pairs.

    Frontend HlsCard sends flat keys like:
      {engine: "hls", encoder_mode: "gpu_nvenc", video_crf: 18, ...}

    Maps them to nested config:
      - modules.video_muxer.* (full encoder settings)
      - output.hls.* / output.web.* (encoder_mode + audio_offset_ms for CompositeOutput)
    """
    ctx = _ctx(request)
    config = ctx["config"]
    pipeline = ctx["pipeline"]

    body = await request.json()
    logger.debug(f"[VIDEO_MUXER] PUT received: {json.dumps(body, indent=2)[:500]}")

    # Keys that map to output section (subset with schema support)
    OUTPUT_KEYS = {"encoder_mode", "audio_offset_ms"}

    # Keys that map to modules.video_muxer (full VideoMuxerConfig schema)
    MODULE_KEYS = {
        "encoder_mode",
        "video_crf",
        "video_preset",
        "gpu_preset",
        "audio_offset_ms",
        "audio_codec",
        "audio_bitrate",
        "video_bitrate",
        "video_fps",
        "video_width",
        "video_height",
        "audio_sample_rate",
    }

    nested: dict[str, Any] = {"output": {}, "modules": {}}
    has_data = False

    for key in MODULE_KEYS:
        if key in body:
            nested["modules"].setdefault("video_muxer", {})[key] = body[key]
            has_data = True

    for key in OUTPUT_KEYS:
        if key in body:
            nested["output"].setdefault("hls", {})[key] = body[key]
            nested["output"].setdefault("web", {})[key] = body[key]
            has_data = True

    if not has_data:
        raise HTTPException(400, "No recognized config keys provided")

    try:
        config.update_from_dict(nested)
        config.save()
        config.reload()
    except ValueError as e:
        logger.warning(f"[VIDEO_MUXER] Validation failed: {e}")
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        logger.error("[VIDEO_MUXER] Save failed: %s", e)
        # F161: Return generic message to avoid leaking internal details
        raise HTTPException(500, "Failed to save configuration") from e

    try:
        pipeline.reconfigure(config)
    except Exception as e:
        logger.error(f"[VIDEO_MUXER] Pipeline reconfigure failed: {e}")

    invalidate_cache("config")
    invalidate_cache("status")
    logger.info(f"[VIDEO_MUXER] Config updated: {body}")
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
    # Sync web/hls output (preservar encoder_mode del usuario, no tocar)
    config.set("output.web.segment_duration", chunk_duration)
    config.set("output.web.list_size", calculated_list_size)
    config.set("output.hls.segment_duration", chunk_duration)
    config.set("output.hls.list_size", calculated_list_size)
    # Sync video_muxer (preservar encoder_mode del usuario, no tocar)
    config.set("modules.video_muxer.hls_segment_duration", chunk_duration)
    config.set("modules.video_muxer.hls_list_size", calculated_list_size)
    # Sync subtitle generator
    config.set("modules.subtitle_generator.chunk_duration", chunk_duration)
    # Sync named outputs (handled by schema validator on save/reload)

    logger.info(f"[CHUNK] Syncing chunk_duration={chunk_duration}s, list_size={calculated_list_size} to all modules")

    try:
        config.save()
        config.reload()
    except Exception as e:
        logger.error(f"[CHUNK] Failed to save config: {e}")
        raise HTTPException(status_code=500, detail="Failed to save configuration") from e

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
        "pipeline_mode": "thread_parallel",
        "synced_to": [
            "pipeline.chunk_duration_sec",
            "pipeline.mode",
            "pipeline.max_concurrent_chunks",
            "input.srt/rtmp/file.chunk_duration_sec",
            "output.web/hls.segment_duration",
            "output.web/hls.list_size",
            "modules.video_muxer.hls_segment_duration",
            "modules.video_muxer.hls_list_size",
            "modules.subtitle_generator.chunk_duration",
        ],
        "encoder_mode_preserved": True,
    }
