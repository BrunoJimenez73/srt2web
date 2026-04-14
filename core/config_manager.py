"""
Configuration manager for SRT2Web.

Loads config.yaml, validates it, provides defaults, and supports
runtime updates from the GUI.

VALIDACIÓN ESTRICTA: Ahora usa esquema Pydantic definido en config_schema.py
Todos los campos se validan automáticamente al cargar y guardar.
"""

import os
import copy
import logging
from pathlib import Path
from typing import Any, Optional
from pydantic import ValidationError

import yaml

from core.config_schema import SRT2WebConfig

logger = logging.getLogger("srt2web.config")

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
        # Cargar defaults desde esquema Pydantic
        default_config = SRT2WebConfig().to_dict()
        
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
                
                # Merge con defaults
                merged_config = _deep_merge(default_config, file_config)
                
                # Validar con esquema Pydantic
                try:
                    validated_config = SRT2WebConfig.from_dict(merged_config)
                    self._config = validated_config.to_dict()
                    logger.info(f"Configuration loaded and validated from {self._config_path}")
                except ValidationError as ve:
                    logger.error(f"Configuration validation error in {self._config_path}:\n{ve}")
                    logger.warning("Using defaults due to validation failure.")
                    self._config = default_config
            except Exception as e:
                logger.error(f"Error loading configuration file: {e}")
                logger.warning("Using defaults due to load failure.")
                self._config = default_config
        else:
            logger.info(
                f"Config file not found at {self._config_path}. Using defaults."
            )
            self._config = default_config

    def save(self) -> None:
        """Persist current configuration to YAML file."""
        try:
            # Validar antes de guardar
            validated_config = SRT2WebConfig.from_dict(self._config)
            self._config = validated_config.to_dict()
            
            os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)
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
        import logging
        import json
        logger = logging.getLogger("srt2web.config")
        
        logger.info(f"[update_from_dict] BEFORE merge - input.srt: {data.get('input', {}).get('srt', {})}")
        
        new_config = _deep_merge(self._config, data)
        
        logger.info(f"[update_from_dict] AFTER merge - input.srt: {new_config.get('input', {}).get('srt', {})}")
        
        try:
            # Validar que el resultado del merge sigue siendo válido
            validated_config = SRT2WebConfig.from_dict(new_config)
            self._config = validated_config.to_dict()
            
            logger.info(f"[update_from_dict] AFTER validate - input.srt: {self._config.get('input', {}).get('srt', {})}")
        except ValidationError as ve:
            logger.error(f"Invalid configuration update attempt:\n{ve}")
            raise ValueError(f"Configuration update failed: {ve}")

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()
