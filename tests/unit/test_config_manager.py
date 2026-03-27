"""
Unit tests for ConfigManager.
"""

import os
import pytest
from core.config_manager import ConfigManager, DEFAULT_CONFIG, _deep_merge


class TestDeepMerge:
    """Tests for the _deep_merge helper function."""

    def test_deep_merge_simple(self):
        """Test simple dictionary merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test nested dictionary merge."""
        base = {"outer": {"inner": 1, "keep": 2}}
        override = {"outer": {"inner": 3}}
        result = _deep_merge(base, override)

        assert result == {"outer": {"inner": 3, "keep": 2}}

    def test_deep_merge_overwrites_list(self):
        """Test that override completely replaces lists."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = _deep_merge(base, override)

        assert result == {"items": [4, 5]}


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_init_with_defaults(self):
        """Test initialization with default config (using nonexistent path)."""
        # Use a nonexistent path to get pure defaults
        config = ConfigManager("/nonexistent/path.yaml")

        assert config.get("server.port") == 8080
        assert config.get("input.srt.listen_port") == 9000
        assert config.get("pipeline.chunk_duration_sec") == 15

    def test_init_with_config_file(self, config_file):
        """Test initialization with a config file."""
        config = ConfigManager(config_file)

        assert config.get("server.port") == 8080
        assert config.get("input.srt.listen_port") == 9000

    def test_get_with_default(self):
        """Test get method with default value."""
        config = ConfigManager("/nonexistent/path.yaml")

        assert config.get("nonexistent.key", "default") == "default"
        assert config.get("nonexistent.key") is None

    def test_get_dotted_key(self):
        """Test getting nested values with dot notation."""
        config = ConfigManager("/nonexistent/path.yaml")

        assert config.get("input.srt.listen_port") == 9000
        assert config.get("modules.transcriber.model") == "tiny"

    def test_set_dotted_key(self):
        """Test setting nested values with dot notation."""
        config = ConfigManager("/nonexistent/path.yaml")

        config.set("input.srt.listen_port", 9999)
        assert config.get("input.srt.listen_port") == 9999

    def test_set_creates_intermediate_dicts(self):
        """Test that set creates intermediate dicts if needed."""
        config = ConfigManager("/nonexistent/path.yaml")

        config.set("new.nested.key", "value")

        assert config.get("new.nested.key") == "value"
        assert isinstance(config.get("new.nested"), dict)

    def test_get_section(self):
        """Test getting entire config section."""
        config = ConfigManager("/nonexistent/path.yaml")

        srt_section = config.get_section("input.srt")

        assert isinstance(srt_section, dict)
        assert srt_section.get("listen_port") == 9000
        assert srt_section.get("mode") == "listener"

    def test_get_module_config(self):
        """Test getting module-specific config."""
        config = ConfigManager("/nonexistent/path.yaml")

        transcriber_config = config.get_module_config("transcriber")

        assert transcriber_config.get("enabled") is True
        assert transcriber_config.get("model") == "tiny"

    def test_set_module_enabled(self):
        """Test enabling/disabling modules."""
        config = ConfigManager("/nonexistent/path.yaml")

        config.set_module_enabled("transcriber", False)

        assert config.get_module_config("transcriber").get("enabled") is False

    def test_to_dict(self):
        """Test serialization to dict."""
        config = ConfigManager("/nonexistent/path.yaml")

        result = config.to_dict()

        assert isinstance(result, dict)
        assert "server" in result
        assert "input" in result
        assert "modules" in result

    def test_update_from_dict(self):
        """Test partial update from dict."""
        config = ConfigManager("/nonexistent/path.yaml")

        config.update_from_dict({"input": {"srt": {"listen_port": 8888}}})

        assert config.get("input.srt.listen_port") == 8888
        assert config.get("input.srt.mode") == "listener"  # unchanged

    def test_save_and_reload(self, temp_dir):
        """Test saving and reloading config."""
        config_path = os.path.join(temp_dir, "save_test.yaml")

        config1 = ConfigManager("/nonexistent/path.yaml")
        config1.set("input.srt.listen_port", 7777)
        config1._config_path = config_path
        config1.save()

        config2 = ConfigManager(config_path)

        assert config2.get("input.srt.listen_port") == 7777

    def test_reload(self, config_file):
        """Test reloading config from file."""
        # First load config
        config = ConfigManager(config_file)
        original_port = config.get("server.port")

        # Modify the file by adding a new key
        import yaml

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        data["new_key"] = "new_value"

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        # Reload and verify new key is present
        config.reload()

        assert config.get("new_key") == "new_value"
        # Original keys should still be there
        assert config.get("server.port") == original_port

    def test_invalid_path_uses_defaults(self):
        """Test that invalid config path uses defaults."""
        config = ConfigManager("/nonexistent/path.yaml")

        assert config.get("server.port") == 8080

    def test_all_default_modules_present(self):
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
