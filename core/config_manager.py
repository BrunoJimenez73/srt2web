"""
Configuration manager for SRT2Web.

Loads config.yaml, validates it, provides defaults, and supports
runtime updates from the GUI.

FUENTE ÚNICA DE VERDAD: schema Pydantic en config_schema.py
Todos los defaults vienen de SRT2WebConfig().to_dict()
"""

import copy
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

# Handle Pydantic v1 vs v2 import
try:
    from pydantic import ValidationError  # Pydantic v2
except ImportError:
    try:
        from pydantic.v1 import ValidationError  # Pydantic v1
    except ImportError:
        try:
            from pydantic_core import ValidationError  # Pydantic v2 (core)
        except ImportError:
            # Fallback - define a basic ValidationError
            class ValidationError(Exception):
                pass

from core.config_schema import SRT2WebConfig
from core.hardware import update_config_with_optimal_device

logger = logging.getLogger("srt2web.config")

# Única fuente de defaults — generada desde el schema Pydantic
DEFAULT_CONFIG = SRT2WebConfig().to_dict()


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
        self._config: dict = {}
        self._load()

    def _find_config(self) -> str:
        """Find config.yaml relative to the project root."""
        project_root = Path(__file__).parent.parent
        candidates = [
            project_root / "config" / "config.yaml",
            project_root / "config.yml",
            Path.cwd() / "config" / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return str(project_root / "config" / "config.yaml")

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
                except ValidationError as ve:
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
        """Persist current configuration to YAML file."""
        try:
            # Validar antes de guardar
            validated_config = SRT2WebConfig.from_dict(self._config)
            self._config = validated_config.to_dict()

            Path(self._config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
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
        except ValidationError as ve:
            logger.error(f"Invalid configuration update attempt:\n{ve}")
            raise ValueError(f"Configuration update failed: {ve}")

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()
