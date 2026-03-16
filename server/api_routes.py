"""
REST API routes for SRT2Web.

Provides endpoints for pipeline control, configuration,
and module management.
"""

import re
import logging
import traceback
from typing import Optional, Any, Dict, List
from datetime import datetime

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
    }
)

# Valid input/output types
VALID_INPUT_TYPES = frozenset({"srt", "file", "rtmp", "audio"})
VALID_OUTPUT_TYPES = frozenset({"web", "hls", "srt", "rtmp", "audio"})

# Allowed values for specific config fields
ALLOWED_WHISPER_MODELS = {"tiny", "small", "medium", "large-v2", "large-v3", "large"}
ALLOWED_LANGUAGES = {"auto", "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ru"}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_SRT_MODES = {"listener", "caller"}


def sanitize_module_name(name: str) -> str:
    """Validate and sanitize module name to prevent injection."""
    if not name or not isinstance(name, str):
        raise HTTPException(400, "Module name is required and must be a string")

    if not re.match(r"^[a-z_]+$", name):
        raise HTTPException(
            400,
            f"Invalid module name format: '{name}'. Only lowercase letters and underscores are allowed.",
        )

    if name not in VALID_MODULE_NAMES:
        raise HTTPException(
            400,
            f"Unknown module: '{name}'. Valid modules are: {', '.join(sorted(VALID_MODULE_NAMES))}",
        )

    return name


def validate_config_value(key: str, value: Any) -> Any:
    """Validate specific configuration values with detailed error messages."""
    key_lower = key.lower()

    if "port" in key_lower:
        if not isinstance(value, int):
            raise HTTPException(
                400, f"Port must be an integer, got {type(value).__name__}: {value}"
            )
        if not (1 <= value <= 65535):
            raise HTTPException(400, f"Port must be between 1 and 65535, got: {value}")

    if "latency" in key_lower:
        if not isinstance(value, (int, float)):
            raise HTTPException(
                400, f"Latency must be a number, got {type(value).__name__}: {value}"
            )
        if value < 0:
            raise HTTPException(400, f"Latency cannot be negative, got: {value}")

    if key == "transcriber.model":
        if value not in ALLOWED_WHISPER_MODELS:
            raise HTTPException(
                400,
                f"Invalid Whisper model: '{value}'. Valid models are: {', '.join(sorted(ALLOWED_WHISPER_MODELS))}",
            )

    if key in (
        "transcriber.language",
        "translator.source_lang",
        "translator.target_lang",
    ):
        if value not in ALLOWED_LANGUAGES:
            raise HTTPException(
                400,
                f"Invalid language: '{value}'. Valid languages are: {', '.join(sorted(ALLOWED_LANGUAGES))}",
            )

    if key == "transcriber.device":
        if value not in ALLOWED_DEVICES:
            raise HTTPException(
                400,
                f"Invalid device: '{value}'. Valid devices are: {', '.join(sorted(ALLOWED_DEVICES))}",
            )

    if key == "srt.mode":
        if value not in ALLOWED_SRT_MODES:
            raise HTTPException(
                400,
                f"Invalid SRT mode: '{value}'. Valid modes are: {', '.join(sorted(ALLOWED_SRT_MODES))}",
            )

    if "volume" in key_lower:
        if not isinstance(value, (int, float)):
            raise HTTPException(
                400, f"Volume must be a number, got {type(value).__name__}: {value}"
            )
        if not (0 <= value <= 2.0):
            raise HTTPException(
                400, f"Volume must be between 0.0 and 2.0, got: {value}"
            )

    if "speed" in key_lower:
        if not isinstance(value, (int, float)):
            raise HTTPException(
                400, f"Speed must be a number, got {type(value).__name__}: {value}"
            )
        if not (0.5 <= value <= 2.0):
            raise HTTPException(400, f"Speed must be between 0.5 and 2.0, got: {value}")

    return value


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    error: str
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


def create_error_response(
    message: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "error": "validation_error",
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "details": details,
    }


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
        """Get full pipeline status including all modules and input/output."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        input_source = ctx.get("input_source")

        status = pipeline.get_status()

        if input_source:
            status["input_receiving"] = input_source.is_receiving()
            status["input_info"] = input_source.get_connection_info()

        return status

    @router.post("/start")
    async def start_pipeline(request: Request):
        """Start the processing pipeline."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        input_source = ctx.get("input_source")
        log_broadcast = ctx.get("log_broadcast")

        from core.pipeline import PipelineState

        if pipeline.state == PipelineState.RUNNING:
            raise HTTPException(400, "Pipeline is already running")

        def on_log(level, message):
            if log_broadcast:
                log_broadcast(level, message)

        def on_state(state):
            if log_broadcast:
                log_broadcast("info", f"Pipeline state changed: {state}")

        try:
            pipeline.start(
                on_log=on_log,
                on_state_change=on_state,
            )
        except Exception as e:
            logger.error(f"Failed to start pipeline: {e}")
            raise HTTPException(500, f"Failed to start pipeline: {e}")

        input_info = {}
        if input_source:
            input_info = input_source.get_connection_info()

        return {"status": "started", "input": input_info}

    @router.post("/stop")
    async def stop_pipeline(request: Request):
        """Stop the processing pipeline."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]

        try:
            pipeline.stop()
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")
            pass

        return {"status": "stopped"}

    @router.post("/restart")
    async def restart_pipeline(request: Request):
        """Restart the pipeline to apply module configuration changes."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        config = ctx["config"]

        try:
            pipeline.stop()
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")

        # Small delay to ensure clean shutdown
        import asyncio

        await asyncio.sleep(0.5)

        # Reconfigure all modules
        pipeline.reconfigure(config)

        # Start pipeline again
        try:
            pipeline.start(
                on_log=lambda level, msg: None,
                on_state_change=lambda state: None,
            )
        except Exception as e:
            logger.error(f"Failed to restart pipeline: {e}")
            raise HTTPException(500, f"Failed to restart pipeline: {e}")

        return {"status": "restarted"}

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

    @router.get("/modules/{module_name}/debug")
    async def debug_module(request: Request, module_name: str):
        """Debug endpoint to see raw module state."""
        safe_module_name = sanitize_module_name(module_name)
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        module = pipeline.get_module(safe_module_name)
        if not module:
            raise HTTPException(404, f"Module '{safe_module_name}' not found")
        return {
            "name": module.name,
            "enabled": module.enabled,
            "_state": str(module._state),
            "state_property": str(module.state),
        }

    @router.put("/modules/{module_name}/toggle")
    async def toggle_module(
        request: Request,
        module_name: str,
        body: ModuleToggle,
    ):
        """Enable or disable a module with hot reload."""
        from core.module_base import ModuleState

        safe_module_name = sanitize_module_name(module_name)

        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        config = ctx["config"]

        module = pipeline.get_module(safe_module_name)
        if not module:
            raise HTTPException(404, f"Module '{safe_module_name}' not found")

        was_enabled = module.enabled
        module.enabled = body.enabled
        config.set_module_enabled(safe_module_name, body.enabled)
        config.save()

        # Hot reload: start or stop the module if pipeline is running
        if pipeline.state.value == "running":
            try:
                if body.enabled and not was_enabled:
                    # Module was disabled, now enabled - start it
                    mod_config = config.get_module_config(safe_module_name)
                    module.configure(mod_config)
                    module.start()
                    module._state = ModuleState.RUNNING
                    logger.info(f"Hot-started module: {safe_module_name}")
                    # Force re-read of enabled state in next iteration
                    pipeline._chunk_index += 0
                elif not body.enabled and was_enabled:
                    # Module was enabled, now disabled - stop it
                    module.stop()
                    module._state = ModuleState.DISABLED
                    logger.info(f"Hot-stopped module: {safe_module_name}")
                else:
                    # Just reconfigure
                    pipeline.reconfigure(config)
            except Exception as e:
                import traceback

                err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                logger.error(f"Error in hot-reload for {safe_module_name}: {err_msg}")
                return {
                    "module": safe_module_name,
                    "enabled": body.enabled,
                    "status": module.get_status().to_dict(),
                    "warning": f"Hot reload failed: {str(e)}",
                    "error": err_msg,
                }
        else:
            pipeline.reconfigure(config)

        return {
            "module": safe_module_name,
            "enabled": body.enabled,
            "status": module.get_status().to_dict(),
            "hot_reload": True,
        }

    # ── Input/Output Info ───────────────────────────────────

    @router.get("/input-info")
    async def input_info(request: Request):
        """Get input source connection information."""
        ctx = _ctx(request)
        input_source = ctx.get("input_source")

        if not input_source:
            return {"error": "No input source configured"}

        return input_source.get_connection_info()

    @router.get("/output-info")
    async def output_info(request: Request):
        """Get output sink information."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]

        output_sink = pipeline.output_sink
        if not output_sink:
            return {"error": "No output sink configured"}

        return output_sink.get_stream_info()

    @router.get("/available")
    async def get_available(request: Request):
        """Get available input and output types."""
        from core.io_factory import InputFactory, OutputFactory

        return {
            "inputs": InputFactory.available(),
            "outputs": OutputFactory.available(),
        }

    # Legacy endpoint - redirects to input-info
    @router.get("/srt-info")
    async def srt_info(request: Request):
        """Get SRT connection information (legacy - use /input-info)."""
        return await input_info(request)

    return router
