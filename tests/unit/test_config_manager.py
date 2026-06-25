"""
Unit tests for ConfigManager.
"""


import pytest

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


class TestConfigManagerAtomicSave:
    """F117: Tests for atomic config save using os.replace()."""

    def test_save_creates_file(self, tmp_path):
        """Config save should create the file."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(str(config_path))
        config.set("server.port", 8888)
        config.save()
        assert config_path.exists()

    def test_save_is_atomic(self, tmp_path):
        """F117: Save should use os.replace() — no intermediate state without file."""

        config_path = tmp_path / "config.yaml"
        config = ConfigManager(str(config_path))
        config.set("server.port", 8888)
        config.save()

        # Verify file content
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["server"]["port"] == 8888

        # Overwrite — should not leave temp file behind
        config.set("server.port", 9999)
        config.save()

        # .tmp file should NOT exist after save
        temp_file = tmp_path / "config.yaml.tmp"
        assert not temp_file.exists(), ".tmp file should be cleaned up by os.replace()"

        # Verify updated content
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["server"]["port"] == 9999

    def test_save_preserves_valid_yaml(self, tmp_path):
        """Config save should produce valid YAML."""
        import yaml

        config_path = tmp_path / "config.yaml"
        config = ConfigManager(str(config_path))
        config.set("server.port", 8888)
        config.save()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "server" in data
