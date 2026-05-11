"""
Validation utilities for SRT2Web API routes.

Contains validators, sanitizers, and dependency checkers
extracted from the monolithic api_routes.py.
"""

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from core.config_schema import (
    ALLOWED_DEVICES,
    ALLOWED_GPU_PRESETS,
    ALLOWED_LANGUAGES,
    ALLOWED_SRT_MODES,
    ALLOWED_TTS_ENGINES,
    ALLOWED_TTS_VOICES,
    ALLOWED_VIDEO_PRESETS,
    ALLOWED_WHISPER_MODELS,
    VALID_MODULE_NAMES,
)

logger = logging.getLogger("srt2web.api.validators")


def sanitize_module_name(name: str) -> str:
    """Validate and sanitize module name to prevent injection."""
    if not name or not isinstance(name, str):
        raise ValueError("Module name is required and must be a string")

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid module name format: '{name}'. Only letters, numbers and underscores are allowed.")

    if name not in VALID_MODULE_NAMES:
        raise ValueError(f"Unknown module: '{name}'. Valid modules are: {', '.join(sorted(VALID_MODULE_NAMES))}")

    return name


def validate_config_value(key: str, value: Any) -> Any:
    """Validate specific configuration values with detailed error messages."""
    key_lower = key.lower()

    if "port" in key_lower:
        if not isinstance(value, int):
            raise ValueError(f"Port must be an integer, got {type(value).__name__}: {value}")
        if not (1 <= value <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got: {value}")

    if "latency" in key_lower:
        if not isinstance(value, (int, float)):
            raise ValueError(f"Latency must be a number, got {type(value).__name__}: {value}")
        if value < 0:
            raise ValueError(f"Latency cannot be negative, got: {value}")

    if key == "transcriber.model":
        if value not in ALLOWED_WHISPER_MODELS:
            raise ValueError(
                f"Invalid Whisper model: '{value}'. Valid models are: {', '.join(sorted(ALLOWED_WHISPER_MODELS))}"
            )

    if key in (
        "transcriber.language",
        "translator.source_lang",
        "translator.target_lang",
    ):
        if value not in ALLOWED_LANGUAGES:
            raise ValueError(
                f"Invalid language: '{value}'. Valid languages are: {', '.join(sorted(ALLOWED_LANGUAGES))}"
            )

    if key == "transcriber.device":
        if value not in ALLOWED_DEVICES:
            raise ValueError(f"Invalid device: '{value}'. Valid devices are: {', '.join(sorted(ALLOWED_DEVICES))}")

    if key == "tts_engine.engine":
        if value not in ALLOWED_TTS_ENGINES:
            raise ValueError(
                f"Invalid TTS engine: '{value}'. Valid engines are: {', '.join(sorted(ALLOWED_TTS_ENGINES))}"
            )

    if key == "tts_engine.device":
        if value not in ALLOWED_DEVICES:
            raise ValueError(f"Invalid device: '{value}'. Valid devices are: {', '.join(sorted(ALLOWED_DEVICES))}")

    if key == "tts_engine.voice":
        if not value or not isinstance(value, str):
            raise ValueError("Voice must be a non-empty string")
        if value not in ALLOWED_TTS_VOICES:
            raise ValueError(f"Invalid voice: '{value}'. Valid voices are: {', '.join(sorted(ALLOWED_TTS_VOICES))}")

    if key == "srt.mode":
        if value not in ALLOWED_SRT_MODES:
            raise ValueError(f"Invalid SRT mode: '{value}'. Valid modes are: {', '.join(sorted(ALLOWED_SRT_MODES))}")

    if "volume" in key_lower:
        if not isinstance(value, (int, float)):
            raise ValueError(f"Volume must be a number, got {type(value).__name__}: {value}")
        if not (0 <= value <= 2.0):
            raise ValueError(f"Volume must be between 0.0 and 2.0, got: {value}")

    if "speed" in key_lower:
        if not isinstance(value, (int, float)):
            raise ValueError(f"Speed must be a number, got {type(value).__name__}: {value}")
        if not (0.5 <= value <= 2.0):
            raise ValueError(f"Speed must be between 0.5 and 2.0, got: {value}")

    # Validate video_muxer presets
    if key == "video_muxer.video_preset":
        if value not in ALLOWED_VIDEO_PRESETS:
            raise ValueError(
                f"Invalid video preset: '{value}'. Valid presets are: {', '.join(sorted(ALLOWED_VIDEO_PRESETS))}"
            )

    if key == "video_muxer.gpu_preset":
        if value not in ALLOWED_GPU_PRESETS:
            raise ValueError(
                f"Invalid GPU preset: '{value}'. Valid presets are: {', '.join(sorted(ALLOWED_GPU_PRESETS))}"
            )

    return value


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


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    error: str
    message: str
    timestamp: str
    details: Optional[dict[str, Any]] = None


def create_error_response(message: str, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Create a standardized error response."""
    from datetime import datetime

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


class SeekPosition(BaseModel):
    """Request body for seek position."""

    position: float  # Position in seconds


class ChunkDurationRequest(BaseModel):
    """Request body for updating chunk duration."""

    chunk_duration_sec: int

    @field_validator("chunk_duration_sec")
    @classmethod
    def validate_range(cls, v: int) -> int:
        if v < 1 or v > 60:
            raise ValueError("chunk_duration_sec must be between 1 and 60")
        return v


class AddOutputRequest(BaseModel):
    """Request body for adding a new output."""

    type: str
    name: Optional[str] = None
    config: Optional[dict[str, Any]] = {}


class UpdateOutputRequest(BaseModel):
    """Request body for updating an existing output."""

    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None
