"""
Unit tests for ConfigManager.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import ConfigManager


@pytest.mark.unit
class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default config (using nonexistent path)."""
        config = ConfigManager("/nonexistent/path.yaml")

        assert config.get("server.port") == 9999
        assert config.get("input.srt.listen_port") == 9000

    def test_get_with_default(self) -> None:
        """Test get method with default value."""
        config = ConfigManager("/nonexistent/path.yaml")

        result = config.get("nonexistent.key", "default_value")
        assert result == "default_value"

    def test_set(self) -> None:
        """Test setting a value."""
        config = ConfigManager("/nonexistent/path.yaml")

        config.set("server.port", 9000)

        assert config.get("server.port") == 9000

    def test_get_nested(self) -> None:
        """Test getting nested values."""
        config = ConfigManager("/nonexistent/path.yaml")

        result = config.get("server.port")
        assert result is not None

    def test_get_module_config(self) -> None:
        """Test getting module config."""
        config = ConfigManager("/nonexistent/path.yaml")

        module_config = config.get_module_config("transcriber")

        assert module_config is not None

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        config = ConfigManager("/nonexistent/path.yaml")

        result = config.to_dict()

        assert isinstance(result, dict)
        assert "server" in result

    def test_update_from_dict(self) -> None:
        """Test partial update from dict."""
        config = ConfigManager("/nonexistent/path.yaml")

        config.update_from_dict({"input": {"srt": {"listen_port": 8888}}})

        assert config.get("input.srt.listen_port") == 8888

    def test_invalid_path_uses_defaults(self) -> None:
        """Test that invalid config path uses defaults."""
        config = ConfigManager("/nonexistent/path.yaml")

        assert config.get("server.port") == 9999

    def test_all_default_modules_present(self) -> None:
        """Test that all expected modules are in default config."""
        config = ConfigManager("/nonexistent/path.yaml")

        modules = config.get("modules", {})

        expected_modules = [
            "audio_extractor",
            "transcriber",
            "translator",
            "subtitle_generator",
            "tts_engine",
            "audio_mixer",
            "video_muxer",
        ]

        for module in expected_modules:
            assert module in modules