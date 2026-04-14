"""
REST API routes for SRT2Web.

Provides endpoints for pipeline control, configuration,
and module management.
"""

import re
import glob
import logging
import traceback
import shutil
import os
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
        "video_muxer",
    }
)

# Valid input/output types
VALID_INPUT_TYPES = frozenset({"srt", "file", "rtmp", "audio"})
VALID_OUTPUT_TYPES = frozenset({"web", "hls", "srt", "rtmp", "audio"})

# Allowed values for specific config fields
ALLOWED_WHISPER_MODELS = {"tiny", "small", "medium", "large-v2", "large-v3", "large"}
ALLOWED_LANGUAGES = {"auto", "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ru"}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_TTS_ENGINES = {"edge-tts", "piper"}
ALLOWED_TTS_VOICES = {
    # Edge-TTS voices
    "es-ES-AlvaroNeural",
    "es-ES-ElviraNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "fr-FR-DeniseNeural",
    "de-DE-ConradNeural",
    # Piper voices - all available in models/piper/
    "es_ES-carlfm-x_low",
    "es_ES-davefx-medium",
    "es_ES-sharvard-medium",
    "es_ES-mls_10246-low",
    "es_MX-claude-high",
    "es_AR-daniela-high",
    "en_US-lessac-medium",
    "en_US-lessac-low",
    "en_US-amy-low",
    "en_US-ryan-low",
    "fr_FR-gilles-low",
    "fr_FR-siwis-medium",
    "de_DE-eva_k-x_low",
    "de_DE-thorsten-medium",
    "it_IT-paola-medium",
    "it_IT-riccardo-x_low",
    "pt_BR-cadu-medium",
    "pt_PT-tugao-medium",
}
ALLOWED_SRT_MODES = {"listener", "caller"}
ALLOWED_VIDEO_PRESETS = {
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
}
ALLOWED_GPU_PRESETS = {"p1", "p2", "p3", "p4", "p5", "p6", "p7"}


def sanitize_module_name(name: str) -> str:
    """Validate and sanitize module name to prevent injection."""
    if not name or not isinstance(name, str):
        raise HTTPException(400, "Module name is required and must be a string")

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise HTTPException(
            400,
            f"Invalid module name format: '{name}'. Only letters, numbers and underscores are allowed.",
        )

    # Lista de módulos válidos
    valid_modules = [
        "audio_extractor",
        "transcriber",
        "translator",
        "subtitle_generator",
        "tts_engine",
        "audio_mixer",
        "video_muxer",
    ]

    if name not in valid_modules:
        raise HTTPException(
            400,
            f"Unknown module: '{name}'. Valid modules are: {', '.join(sorted(valid_modules))}",
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

    if key == "tts_engine.engine":
        if value not in ALLOWED_TTS_ENGINES:
            raise HTTPException(
                400,
                f"Invalid TTS engine: '{value}'. Valid engines are: {', '.join(sorted(ALLOWED_TTS_ENGINES))}",
            )

    if key == "tts_engine.device":
        if value not in ALLOWED_DEVICES:
            raise HTTPException(
                400,
                f"Invalid device: '{value}'. Valid devices are: {', '.join(sorted(ALLOWED_DEVICES))}",
            )

    if key == "tts_engine.voice":
        if not value or not isinstance(value, str):
            raise HTTPException(400, "Voice must be a non-empty string")
        if value not in ALLOWED_TTS_VOICES:
            raise HTTPException(
                400,
                f"Invalid voice: '{value}'. Valid voices are: {', '.join(sorted(ALLOWED_TTS_VOICES))}",
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

    # Validate video_muxer presets
    if key == "video_muxer.video_preset":
        if value not in ALLOWED_VIDEO_PRESETS:
            raise HTTPException(
                400,
                f"Invalid video preset: '{value}'. Valid presets are: {', '.join(sorted(ALLOWED_VIDEO_PRESETS))}",
            )

    if key == "video_muxer.gpu_preset":
        if value not in ALLOWED_GPU_PRESETS:
            raise HTTPException(
                400,
                f"Invalid GPU preset: '{value}'. Valid presets are: {', '.join(sorted(ALLOWED_GPU_PRESETS))}",
            )

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


def validate_module_dependencies(config: dict) -> list:
    """
    Validate module dependencies according to pipeline rules.

    Rules:
    - subtitle_generator requires translator
    - tts_engine requires translator
    - audio_mixer requires translator AND tts_engine

    Returns list of error messages, empty if valid.
    """
    errors = []
    modules = config.get("modules", {})

    translator_enabled = modules.get("translator", {}).get("enabled", False)
    subtitle_enabled = modules.get("subtitle_generator", {}).get("enabled", False)
    tts_enabled = modules.get("tts_engine", {}).get("enabled", False)
    mixer_enabled = modules.get("audio_mixer", {}).get("enabled", False)

    if subtitle_enabled and not translator_enabled:
        errors.append("subtitle_generator requires translator to be enabled")

    if tts_enabled and not translator_enabled:
        errors.append("tts_engine requires translator to be enabled")

    if mixer_enabled:
        if not translator_enabled:
            errors.append("audio_mixer requires translator to be enabled")
        if not tts_enabled:
            errors.append("audio_mixer requires tts_engine to be enabled")

    return errors


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
        config = ctx["config"]

        status = pipeline.get_status()

        if input_source:
            status["input_receiving"] = input_source.is_receiving()
            status["input_info"] = input_source.get_connection_info()

        # Add network info
        from core.network_utils import get_network_info

        srt_port = config.get("input.srt.listen_port", 9000)
        server_port = config.get("server.port", 9999)
        latency_ms = config.get("input.srt.latency_ms", 1000)
        srt_mode = config.get("input.srt.mode", "listener")
        caller_address = config.get("input.srt.caller_address", "")

        network = get_network_info(
            srt_port=srt_port, server_port=server_port, latency_ms=latency_ms
        )
        network["srt_mode"] = srt_mode
        network["caller_address"] = caller_address
        status["network"] = network

        return status

    @router.post("/start")
    async def start_pipeline(request: Request):
        """Start the processing pipeline."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        input_source = ctx.get("input_source")
        log_broadcast = ctx.get("log_broadcast")
        config = ctx["config"]

        # Check if pipeline is already running (handle both string and enum)
        pipeline_state = getattr(pipeline, 'state', 'idle')
        if pipeline_state in ('running', 'RUNNING') or (hasattr(pipeline_state, 'value') and pipeline_state.value == 'running'):
            raise HTTPException(400, "Pipeline is already running")

        # RTMP input setup - no external server needed, FFmpeg listens for connections
        input_type = config.get("input.type", "srt") if config else "srt"
        logger.info(f"Starting pipeline with input type: {input_type}")
        
        if input_type == "rtmp" and input_source:
            rtmp_config = config.get("input.rtmp", {}) if config else {}
            logger.info(f"RTMP config: {rtmp_config}")
            # Configure RTMP input with listen port from config
            if hasattr(input_source, 'configure'):
                rtmp_port = rtmp_config.get("listen_port", 1935)
                app_name = rtmp_config.get("app", "live")
                stream_key = rtmp_config.get("stream_key", "stream")
                # URL without listen param - it's set via -rtmp_listen option in FFmpeg
                listen_url = f"rtmp://127.0.0.1:{rtmp_port}/{app_name}/{stream_key}"
                new_config = {**rtmp_config, "url": listen_url}
                input_source.configure(new_config)
                logger.info(f"RTMP input configured in listen mode: {listen_url}")

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
        """Stop the processing pipeline and clean up temporary files."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        output_dir = ctx.get("output_dir", "./output")

        try:
            await pipeline.stop()
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")
            pass

        # Clean up temporary files
        cleanup_dirs = [
            os.path.join(output_dir, "chunks"),
            os.path.join(output_dir, "temp_audio"),
            os.path.join(output_dir, "temp_mix"),
            os.path.join(output_dir, "temp_tts"),
        ]

        for cleanup_dir in cleanup_dirs:
            if os.path.exists(cleanup_dir):
                try:
                    shutil.rmtree(cleanup_dir)
                    os.makedirs(cleanup_dir, exist_ok=True)
                    logger.info(f"Cleaned up: {cleanup_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean {cleanup_dir}: {e}")

        # Also clean old HLS files
        hls_dir = os.path.join(output_dir, "hls")
        if os.path.exists(hls_dir):
            # Remove segment files
            for f in glob.glob(os.path.join(hls_dir, "seg_*.ts")):
                try:
                    os.remove(f)
                except:
                    pass
            # Remove chunk SRT files
            for f in glob.glob(os.path.join(hls_dir, "chunk_*.srt")):
                try:
                    os.remove(f)
                except:
                    pass
            # Remove playlist files but recreate them empty
            for m3u8_file in ["stream.m3u8", "master.m3u8"]:
                m3u8_path = os.path.join(hls_dir, m3u8_file)
                try:
                    if os.path.exists(m3u8_path):
                        os.remove(m3u8_path)
                except:
                    pass
            # Keep subs.vtt but clear old entries
            subs_path = os.path.join(hls_dir, "subs.vtt")
            if os.path.exists(subs_path):
                try:
                    with open(subs_path, "w", encoding="utf-8") as f:
                        f.write("WEBVTT\n\n")
                except:
                    pass

        return {"status": "stopped"}

    @router.post("/restart")
    async def restart_pipeline(request: Request):
        """Restart the pipeline to apply module configuration changes."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        config = ctx["config"]

        try:
            await pipeline.stop()
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
        """Update configuration (partial update) with dependency validation."""
        ctx = _ctx(request)
        config = ctx["config"]

        # Validate module dependencies BEFORE saving
        dependency_errors = validate_module_dependencies(body.config)
        if dependency_errors:
            raise HTTPException(
                400,
                f"Configuration violates module dependencies:\n• "
                + "\n• ".join(dependency_errors),
            )

        import json
        logger.info(f"[CONFIG] PUT receives: {json.dumps(body.config, indent=2)[:1000]}")
        logger.info(f"[CONFIG] PUT body keys: {list(body.config.keys())}")
        
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

    # ── Network Information ──────────────────────────────────

    @router.get("/network/info")
    async def network_info(request: Request):
        """Get network information for external connections."""
        from core.network_utils import get_network_info

        ctx = _ctx(request)
        config = ctx["config"]

        srt_port = config.get("input.srt.listen_port", 9000)
        server_port = config.get("server.port", 9999)
        latency_ms = config.get("input.srt.latency_ms", 1000)
        srt_mode = config.get("input.srt.mode", "listener")
        caller_address = config.get("input.srt.caller_address", "")

        network = get_network_info(
            srt_port=srt_port, server_port=server_port, latency_ms=latency_ms
        )

        network["srt_mode"] = srt_mode
        network["caller_address"] = caller_address

        return network

    # ── Health Check ───────────────────────────────────────────

    @router.get("/health")
    async def health_check(request: Request):
        """
        Health check endpoint for monitoring and load balancers.

        Returns:
            - status: overall health status (healthy/degraded/unhealthy)
            - uptime_seconds: time since startup
            - memory_mb: current memory usage
            - modules: status of each module with circuit breaker state
            - pipeline: pipeline state and stats
        """
        from time import time as get_time

        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        config = ctx["config"]

        start_time = ctx.get("_start_time", get_time())
        uptime = get_time() - start_time

        memory_info = {"memory_mb": 0, "memory_percent": 0}
        try:
            import psutil

            process = psutil.Process()
            memory_info = {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "memory_percent": round(process.memory_percent(), 1),
            }
        except ImportError:
            pass

        modules_status = {}
        overall_healthy = True
        has_degraded = False

        for module in pipeline.get_modules():
            status = module.get_status()
            status_dict = status.to_dict()
            circuit_state = status_dict.pop("circuit_state", "closed")

            modules_status[module.name] = {
                "state": status_dict["state"],
                "circuit_state": circuit_state,
                "enabled": status_dict["enabled"],
                "processed_chunks": status_dict["processed_chunks"],
                "last_process_time_ms": status_dict["last_process_time_ms"],
                "error": status_dict["error_message"],
            }

            if status.state == "error":
                overall_healthy = False
            elif circuit_state in ("open", "half_open"):
                has_degraded = True

        if overall_healthy and has_degraded:
            health_status = "degraded"
        elif overall_healthy:
            health_status = "healthy"
        else:
            health_status = "unhealthy"

        input_health = {"receiving": False}
        input_src = pipeline.get_input_source()
        if input_src:
            input_health = {
                "receiving": input_src.is_receiving() if hasattr(input_src, 'is_receiving') else False,
                "type": getattr(input_src, 'name', 'unknown'),
            }

        output_health = {"streaming": False}
        output_snk = pipeline.get_output_sink()
        if output_snk:
            output_health = {
                "streaming": output_snk.is_streaming() if hasattr(output_snk, 'is_streaming') else False,
                "type": getattr(output_snk, 'name', 'unknown'),
            }

        return {
            "status": health_status,
            "uptime_seconds": round(uptime, 1),
            "memory_mb": memory_info["memory_mb"],
            "memory_percent": memory_info["memory_percent"],
            "chunks_processed": pipeline._chunk_index,
            "pipeline_state": pipeline.state.value,
            "modules": modules_status,
            "input": input_health,
            "output": output_health,
        }

    return router
