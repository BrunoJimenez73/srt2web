"""
REST API routes for SRT2Web.

Provides endpoints for pipeline control, configuration,
and module management.
"""

import re
import logging
from typing import Optional, Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, field_validator

logger = logging.getLogger("srt2web.api")

# Whitelist of valid module names
VALID_MODULE_NAMES = frozenset(
    {
        "audio_extractor",
        "transcriber",
        "translator",
        "subtitle_generator",
        "tts_engine",
        "audio_mixer",
        "video_muxer",
    }
)

# Allowed values for specific config fields
ALLOWED_WHISPER_MODELS = {"tiny", "small", "medium", "large-v2", "large-v3", "large"}
ALLOWED_LANGUAGES = {"auto", "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ru"}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_SRT_MODES = {"listener", "caller"}


def sanitize_module_name(name: str) -> str:
    """Validate and sanitize module name to prevent injection."""
    if not re.match(r"^[a-z_]+$", name):
        raise HTTPException(400, f"Invalid module name: {name}")
    if name not in VALID_MODULE_NAMES:
        raise HTTPException(400, f"Unknown module: {name}")
    return name


def validate_config_value(key: str, value: Any) -> Any:
    """Validate specific configuration values."""
    key_lower = key.lower()

    if "port" in key_lower:
        if not isinstance(value, int) or not (1 <= value <= 65535):
            raise HTTPException(400, f"Invalid port value: {value}")

    if "latency" in key_lower:
        if not isinstance(value, (int, float)) or value < 0:
            raise HTTPException(400, f"Invalid latency value: {value}")

    if key == "transcriber.model":
        if value not in ALLOWED_WHISPER_MODELS:
            raise HTTPException(400, f"Invalid Whisper model: {value}")

    if key in (
        "transcriber.language",
        "translator.source_lang",
        "translator.target_lang",
    ):
        if value not in ALLOWED_LANGUAGES:
            raise HTTPException(400, f"Invalid language: {value}")

    if key == "transcriber.device":
        if value not in ALLOWED_DEVICES:
            raise HTTPException(400, f"Invalid device: {value}")

    if key == "srt.mode":
        if value not in ALLOWED_SRT_MODES:
            raise HTTPException(400, f"Invalid SRT mode: {value}")

    if "volume" in key_lower:
        if not isinstance(value, (int, float)) or not (0 <= value <= 2.0):
            raise HTTPException(400, f"Invalid volume value: {value}")

    if "speed" in key_lower:
        if not isinstance(value, (int, float)) or not (0.5 <= value <= 2.0):
            raise HTTPException(400, f"Invalid speed value: {value}")

    return value


class ConfigUpdate(BaseModel):
    """Request body for configuration updates with validation."""

    config: dict

    @field_validator("config")
    @classmethod
    def validate_config_keys(cls, v: dict) -> dict:
        """Validate configuration keys and values."""
        for key, value in v.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, dict):
                        for k, v_val in subvalue.items():
                            full_key = f"{key}.{subkey}.{k}"
                            validate_config_value(full_key, v_val)
                    else:
                        full_key = f"{key}.{subkey}"
                        validate_config_value(full_key, subvalue)
            else:
                validate_config_value(key, value)
        return v


class ModuleToggle(BaseModel):
    """Request body for toggling a module."""

    enabled: bool


def create_api_router() -> APIRouter:
    router = APIRouter(tags=["api"])

    def _ctx(request: Request) -> dict:
        return request.app.state.ctx

    # ── Pipeline Control ──────────────────────────────────

    @router.get("/status")
    async def get_status(request: Request):
        """Get full pipeline status including all modules."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        srt_ingest = ctx["srt_ingest"]

        status = pipeline.get_status()
        status["srt_receiving"] = srt_ingest.is_receiving()
        status["srt_url"] = srt_ingest.get_srt_url()
        return status

    @router.post("/start")
    async def start_pipeline(request: Request):
        """Start the processing pipeline."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        srt_ingest = ctx["srt_ingest"]
        log_broadcast = ctx.get("log_broadcast")

        from core.pipeline import PipelineState

        if pipeline.state == PipelineState.RUNNING:
            raise HTTPException(400, "Pipeline is already running")

        # Start the SRT ingest first
        try:
            srt_config = ctx["config"].get_section("srt")
            srt_config["chunk_duration_sec"] = ctx["config"].get(
                "pipeline.chunk_duration_sec", 4
            )
            srt_ingest.configure(srt_config)
            srt_ingest.start()

            # Reconfigure all pipeline modules with latest settings
            for module in pipeline.get_modules():
                mod_config = ctx["config"].get_module_config(module.name)
                module.configure(mod_config)

        except Exception as e:
            raise HTTPException(500, f"Failed to configure or start items: {e}")

        # Start the pipeline with SRT ingest as data source
        def on_log(level, message):
            if log_broadcast:
                log_broadcast(level, message)

        def on_state(state):
            if log_broadcast:
                log_broadcast("info", f"Pipeline state changed: {state}")

        pipeline.start(
            data_source=srt_ingest.get_next_chunk,
            on_log=on_log,
            on_state_change=on_state,
        )

        return {"status": "started", "srt_url": srt_ingest.get_srt_url()}

    @router.post("/stop")
    async def stop_pipeline(request: Request):
        """Stop the processing pipeline."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        srt_ingest = ctx["srt_ingest"]

        pipeline.stop()
        srt_ingest.stop()

        return {"status": "stopped"}

    # ── Configuration ─────────────────────────────────────

    @router.get("/config")
    async def get_config(request: Request):
        """Get current configuration."""
        ctx = _ctx(request)
        return ctx["config"].to_dict()

    @router.put("/config")
    async def update_config(request: Request, body: ConfigUpdate):
        """Update configuration (partial update)."""
        ctx = _ctx(request)
        config = ctx["config"]

        config.update_from_dict(body.config)
        config.save()

        # Hot reload!
        pipeline = ctx["pipeline"]
        pipeline.reconfigure(config)

        return {"status": "updated", "config": config.to_dict()}

    # ── Module Management ─────────────────────────────────

    @router.get("/modules")
    async def list_modules(request: Request):
        """List all registered modules and their status."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        return {"modules": [m.get_status().to_dict() for m in pipeline.get_modules()]}

    @router.put("/modules/{module_name}/toggle")
    async def toggle_module(
        request: Request,
        module_name: str,
        body: ModuleToggle,
    ):
        """Enable or disable a module."""
        # Sanitize module name to prevent injection
        safe_module_name = sanitize_module_name(module_name)

        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        config = ctx["config"]

        module = pipeline.get_module(safe_module_name)
        if not module:
            raise HTTPException(404, f"Module '{safe_module_name}' not found")

        module.enabled = body.enabled
        config.set_module_enabled(safe_module_name, body.enabled)
        config.save()

        # Also reconfigure the module itself
        pipeline.reconfigure(config)

        return {
            "module": safe_module_name,
            "enabled": body.enabled,
            "status": module.get_status().to_dict(),
        }

    # ── SRT Info ──────────────────────────────────────────

    @router.get("/srt-info")
    async def srt_info(request: Request):
        """Get SRT connection information for OBS/VMix."""
        ctx = _ctx(request)
        config = ctx["config"]
        srt_port = config.get("srt.listen_port", 9000)
        srt_latency = config.get("srt.latency_ms", 400)
        srt_mode = config.get("srt.mode", "listener")

        return {
            "mode": srt_mode,
            "port": srt_port,
            "latency_ms": srt_latency,
            "obs_url": f"srt://YOUR_IP:{srt_port}?mode=caller&latency={srt_latency * 1000}",
            "vmix_url": f"srt://YOUR_IP:{srt_port}",
            "instructions": {
                "obs": (
                    f"OBS → Settings → Stream → Service: Custom → "
                    f"Server: srt://YOUR_IP:{srt_port}?mode=caller"
                    f"&latency={srt_latency * 1000}"
                ),
                "vmix": (
                    f"vMix → Add Input → Stream/SRT → "
                    f"Hostname: YOUR_IP, Port: {srt_port}"
                ),
            },
        }

    return router
