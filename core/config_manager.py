"""
Configuration manager for SRT2Web.

Loads config.yaml, validates it, provides defaults, and supports
runtime updates from the GUI.
"""

import os
import copy
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger("srt2web.config")

# Default configuration - used as fallback for missing keys
DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "port": 8080,
        "cors_origins": ["http://localhost:*", "http://127.0.0.1:*"],
        "auth_token": "",
        "rate_limit_rpm": 60,
        "max_request_size_mb": 10,
    },
    "input": {
        "type": "srt",
        "srt": {
            "listen_port": 9000,
            "mode": "listener",
            "latency_ms": 1000,
            "caller_address": "",
        },
        "file": {
            "path": "",
            "loop": False,
            "speed": 1.0,
        },
    },
    "output": {
        "type": "web",
        "web": {
            "segment_duration": 15,
            "list_size": 6,
            "audio_offset_ms": 0,
        },
    },
    "pipeline": {
        "chunk_duration_sec": 15,
    },
    "modules": {
        "audio_extractor": {"enabled": True},
        "transcriber": {
            "enabled": True,
            "model": "tiny",
            "language": "auto",
            "device": "auto",
        },
        "translator": {
            "enabled": True,
            "source_lang": "en",
            "target_lang": "es",
        },
        "subtitle_generator": {
            "enabled": True,
            "format": "webvtt",
            "use_translated": True,
        },
        "tts_engine": {
            "enabled": False,
            "engine": "edge-tts",
            "device": "auto",
            "voice": "es-ES-ElviraNeural",
            "speed": 1.0,
        },
        "audio_mixer": {
            "enabled": False,
            "original_volume": 0.2,
            "dubbed_volume": 1.0,
        },
        "video_muxer": {
            "enabled": True,
            "hls_segment_duration": 4,
            "audio_offset_ms": 0,
        },
    },
    "output_dir": {
        "directory": "./output",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base.
    Values in override take precedence.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class ConfigManager:
    """
    Manages application configuration with file persistence.

    Usage:
        config = ConfigManager("config.yaml")
        port = config.get("server.port")
        config.set("srt.listen_port", 9001)
        config.save()
    """

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or self._find_config()
        self._config: dict = copy.deepcopy(DEFAULT_CONFIG)
        self._load()

    def _find_config(self) -> str:
        """Find config.yaml relative to the project root."""
        # Look relative to this file's location
        project_root = Path(__file__).parent.parent
        candidates = [
            project_root / "config.yaml",
            project_root / "config.yml",
            Path.cwd() / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        # Default: create in project root
        return str(project_root / "config.yaml")

    def _load(self) -> None:
        """Load configuration from YAML file, merging with defaults."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
                self._config = _deep_merge(DEFAULT_CONFIG, file_config)
                logger.info(f"Configuration loaded from {self._config_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load {self._config_path}: {e}. Using defaults."
                )
                self._config = copy.deepcopy(DEFAULT_CONFIG)
        else:
            logger.info(
                f"Config file not found at {self._config_path}. Using defaults."
            )
            self._config = copy.deepcopy(DEFAULT_CONFIG)

    def save(self) -> None:
        """Persist current configuration to YAML file."""
        try:
            os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            logger.info(f"Configuration saved to {self._config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        Example: config.get("srt.listen_port") → 9000
        """
        keys = dotted_key.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, dotted_key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        Creates intermediate dicts if needed.
        Example: config.set("srt.listen_port", 9001)
        """
        keys = dotted_key.split(".")
        target = self._config
        for key in keys[:-1]:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value

    def get_section(self, section: str) -> dict:
        """Get an entire configuration section as a dict."""
        return copy.deepcopy(self.get(section, {}))

    def get_module_config(self, module_name: str) -> dict:
        """Get configuration for a specific module."""
        return self.get_section(f"modules.{module_name}")

    def set_module_enabled(self, module_name: str, enabled: bool) -> None:
        """Enable or disable a module."""
        self.set(f"modules.{module_name}.enabled", enabled)

    def to_dict(self) -> dict:
        """Return full configuration as a dict."""
        return copy.deepcopy(self._config)

    def update_from_dict(self, data: dict) -> None:
        """Update configuration from a dictionary (partial update)."""
        self._config = _deep_merge(self._config, data)

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()
