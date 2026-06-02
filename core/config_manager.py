"""
Configuration manager for SRT2Web.

Loads config.yaml, validates it, provides defaults, and supports
runtime updates from the GUI.

FUENTE ÚNICA DE VERDAD: schema Pydantic en config_schema.py
Todos los defaults vienen de SRT2WebConfig().to_dict()
"""

import copy
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from core.paths import get_config_path, get_project_root

import yaml

# Note: we catch Exception instead of ValidationError to avoid
# import compatibility issues between Pydantic v1/v2
from core.config_schema import SRT2WebConfig
from core.hardware import update_config_with_optimal_device

logger = logging.getLogger("srt2web.config")

# Única fuente de defaults — generada desde el schema Pydantic
DEFAULT_CONFIG = SRT2WebConfig().to_dict()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
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

    def __init__(self, config_path: str | None = None):
        self._config_path = config_path or self._find_config()
        self._config: dict[str, Any] = {}
        self._lock = __import__("threading").Lock()
        self._load()

    def _find_config(self) -> str:
        """Find config.yaml relative to the project root."""
        project_root = get_project_root()
        candidates = [
            get_config_path(),
            project_root / "config.yml",
            Path.cwd() / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return str(get_config_path())

    def _load(self) -> None:
        """Load configuration from YAML file, merging with defaults."""
        if Path(self._config_path).exists():
            try:
                with open(self._config_path, encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}

                # Merge con defaults (fuente única: DEFAULT_CONFIG)
                merged_config = _deep_merge(DEFAULT_CONFIG, file_config)

                # Validar con esquema Pydantic y auto-detect hardware
                try:
                    validated_config = SRT2WebConfig.from_dict(merged_config)
                    self._config = validated_config.to_dict()
                    self._config = update_config_with_optimal_device(self._config)
                    logger.info(f"Configuration loaded and validated from {self._config_path}")
                except Exception as ve:
                    logger.error(f"Configuration validation error in {self._config_path}:\n{ve}")
                    logger.warning("Using defaults due to validation failure.")
                    self._config = copy.deepcopy(DEFAULT_CONFIG)
            except Exception as e:
                logger.error(f"Error loading configuration file: {e}")
                logger.warning("Using defaults due to load failure.")
                self._config = copy.deepcopy(DEFAULT_CONFIG)
        else:
            logger.info(f"Config file not found at {self._config_path}. Using defaults.")
            self._config = update_config_with_optimal_device(copy.deepcopy(DEFAULT_CONFIG))

    def save(self) -> None:
        """Persist current configuration to YAML file atomically."""
        with self._lock:
            try:
                validated_config = SRT2WebConfig.from_dict(self._config)
                self._config = validated_config.to_dict()

                Path(self._config_path).parent.mkdir(parents=True, exist_ok=True)

                # Write to temp file, then rename for atomicity
                temp_path = f"{self._config_path}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        validated_config.to_dict(),
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )

                if Path(temp_path).exists():
                    if Path(self._config_path).exists():
                        Path(self._config_path).unlink()
                    Path(temp_path).rename(self._config_path)

                logger.info(f"Configuration validated and saved to {self._config_path}")
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

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire configuration section as a dict."""
        return copy.deepcopy(self.get(section, {}))

    def get_module_config(self, module_name: str) -> dict[str, Any]:
        """Get configuration for a specific module."""
        return self.get_section(f"modules.{module_name}")

    def set_module_enabled(self, module_name: str, enabled: bool) -> None:
        """Enable or disable a module."""
        self.set(f"modules.{module_name}.enabled", enabled)

    def to_dict(self) -> dict[str, Any]:
        """Return full configuration as a dict."""
        return copy.deepcopy(self._config)

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update configuration from a dictionary (partial update) with validation."""
        logger.debug(f"[update_from_dict] BEFORE merge - input.srt: {data.get('input', {}).get('srt', {})}")

        new_config = _deep_merge(self._config, data)

        logger.debug(f"[update_from_dict] AFTER merge - input.srt: {new_config.get('input', {}).get('srt', {})}")

        try:
            # Validar que el resultado del merge siga siendo válido
            validated_config = SRT2WebConfig.from_dict(new_config)
            self._config = validated_config.to_dict()

            logger.debug(
                f"[update_from_dict] AFTER validate - input.srt: {self._config.get('input', {}).get('srt', {})}"
            )
        except Exception as ve:
            logger.error(f"Invalid configuration update attempt:\n{ve}")
            raise ValueError(f"Configuration update failed: {ve}") from ve

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()

    # ── Preset Management (F19) ──────────────────────────────────

    @property
    def _preset_path(self) -> Path:
        """Path to presets.json in the config directory."""
        return Path(self._config_path).parent / "presets.json"

    def _load_presets(self) -> dict[str, Any]:
        """Load presets from disk."""
        path = self._preset_path
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return cast(dict[str, Any], json.load(f))
            except Exception as e:
                logger.warning("Could not load presets from %s: %s", path, e)
        return {}

    def _save_presets(self, presets: dict[str, Any]) -> None:
        """Save presets to disk atomically."""
        path = self._preset_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file, then rename for atomicity
            temp_path = f"{path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(presets, f, indent=2, ensure_ascii=False)

            if Path(temp_path).exists():
                if path.exists():
                    path.unlink()
                Path(temp_path).rename(path)
        except Exception as e:
            logger.error(f"Failed to save presets: {e}")
            raise

    def list_presets(self) -> list[dict[str, Any]]:
        """Return list of saved presets with metadata."""
        presets = self._load_presets()
        result: list[dict[str, Any]] = []
        for name, data in presets.items():
            result.append(
                {
                    "name": name,
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", ""),
                    "config_keys": list(data.get("config", {}).keys()),
                }
            )
        return result

    def save_preset(self, name: str, description: str = "") -> None:
        """Save current configuration as a named preset."""
        presets = self._load_presets()
        presets[name] = {
            "config": self.to_dict(),
            "description": description,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_presets(presets)
        logger.info(f"Preset '{name}' saved")

    def load_preset(self, name: str) -> dict[str, Any]:
        """Load a preset by name. Returns the config dict."""
        presets = self._load_presets()
        if name not in presets:
            raise KeyError(f"Preset '{name}' not found")
        return cast(dict[str, Any], presets[name]["config"])

    def delete_preset(self, name: str) -> None:
        """Delete a preset by name."""
        presets = self._load_presets()
        if name not in presets:
            raise KeyError(f"Preset '{name}' not found")
        del presets[name]
        self._save_presets(presets)
        logger.info(f"Preset '{name}' deleted")

    # ── Built-in Presets (F19) ──────────────────────────────────

    @staticmethod
    def built_in_presets() -> dict[str, dict[str, Any]]:
        """Return the built-in preset configurations."""
        return {
            "low_latency": {
                "config": {
                    "pipeline": {"chunk_duration_sec": 10},
                    "input": {
                        "srt": {"chunk_duration_sec": 10},
                        "rtmp": {"chunk_duration_sec": 10},
                    },
                    "modules": {
                        "translator": {"enabled": False},
                        "tts_engine": {"enabled": False},
                        "audio_mixer": {"enabled": False},
                    },
                },
                "description": "Low latency mode (10s chunks, no translation/TTS)",
            },
            "high_quality": {
                "config": {
                    "pipeline": {"chunk_duration_sec": 10},
                    "modules": {
                        "transcriber": {"model": "large", "beam_size": 5},
                        "translator": {"enabled": True},
                        "tts_engine": {
                            "enabled": True,
                            "engine": "piper",
                            "device": "auto",
                        },
                    },
                },
                "description": "High quality (large Whisper, full pipeline enabled)",
            },
            "spanish_stream": {
                "config": {
                    "pipeline": {"chunk_duration_sec": 10},
                    "modules": {
                        "transcriber": {"language": "es", "model": "medium"},
                        "translator": {
                            "enabled": True,
                            "source_lang": "es",
                            "target_lang": "en",
                        },
                        "tts_engine": {
                            "enabled": True,
                            "engine": "piper",
                            "voice": "es_ES-sharvard-medium",
                            "device": "auto",
                        },
                    },
                },
                "description": "Spanish stream (es→en translation with Sharvard voice)",
            },
        }
