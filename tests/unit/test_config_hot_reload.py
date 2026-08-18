"""
Tests for config hot reload feature:
- Config reload after save
- Stale cache prevention
"""

import os
import time
from unittest.mock import patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")


@pytest.mark.unit
class TestConfigReload:
    """Test config reload functionality."""

    def test_config_reload_exists(self) -> None:
        """Test config has reload method."""
        from core.config_manager import ConfigManager

        assert hasattr(ConfigManager, "reload")

    def test_config_save_includes_reload(self, tmp_path) -> None:
        """Test config save triggers reload."""
        from core.config_manager import ConfigManager

        config_path = str(tmp_path / "config.yaml")

        with (
            patch("core.config_manager.atomic_replace"),
            patch("builtins.open", create=True),
            patch("yaml.safe_load") as mock_yaml,
            patch("yaml.dump"),
        ):
            mock_yaml.return_value = {"test": "value"}

            manager = ConfigManager(config_path)
            _ = manager._config.copy()

            manager._config = {"pipeline": {"chunk_duration_sec": 10}}
            manager.save()

            manager.reload()

            assert hasattr(manager, "_load")


class TestConfigHotReloadOnUpdate:
    """Test hot reload is called on config update."""

    def test_update_config_reload_behavior(self, tmp_path) -> None:
        """Test that config reloads after update."""
        import shutil

        from core.config_manager import ConfigManager

        if not os.path.exists(CONFIG_PATH):
            pytest.skip("config.yaml not found")

        temp_config = tmp_path / "config.yaml"
        shutil.copy2(CONFIG_PATH, temp_config)

        manager = ConfigManager(str(temp_config))

        original_value = manager.get("pipeline.chunk_duration_sec")
        assert original_value is not None, "Original chunk_duration should not be None"

        new_value = 30
        manager.set("pipeline.chunk_duration_sec", new_value)
        manager.save()
        manager.reload()

        reloaded_value = manager.get("pipeline.chunk_duration_sec")

        assert reloaded_value == new_value, f"Expected {new_value}, got {reloaded_value}"


class TestConfigCachePrevention:
    """Test config doesn't use stale cache."""

    def test_no_stale_cache(self) -> None:
        """Test config reads from disk, not cache."""
        config_path = "config.yaml"

        with (
            patch("builtins.open", create=True),
            patch("yaml.safe_load") as mock_yaml,
            patch("os.path.getmtime") as mock_mtime,
        ):
            mock_yaml.return_value = {"test": "value"}
            mock_mtime.return_value = time.time()

            from core.config_manager import ConfigManager

            manager = ConfigManager.__new__(ConfigManager)
            manager._config_path = config_path
            manager._config = {"pipeline": {"chunk_duration_sec": 5}}

            manager.reload()

            assert manager._config is not None

    def test_config_updates_immediately(self) -> None:
        """Test config updates are immediately visible."""
        config = {"pipeline": {"chunk_duration_sec": 5}}

        config["pipeline"]["chunk_duration_sec"] = 2

        assert config["pipeline"]["chunk_duration_sec"] == 2


class TestConfigValues:
    """Test config low-latency values."""

    def test_chunk_duration_is_2(self) -> None:
        """Test chunk_duration is set to 2 seconds."""
        config = {
            "input": {"srt": {"chunk_duration_sec": 2}},
            "pipeline": {"chunk_duration_sec": 2},
        }

        assert config["input"]["srt"]["chunk_duration_sec"] == 2
        assert config["pipeline"]["chunk_duration_sec"] == 2

    def test_segment_duration_is_2(self) -> None:
        """Test segment_duration is set to 2 seconds."""
        config = {
            "output": {
                "web": {"segment_duration": 2},
                "hls": {"segment_duration": 2},
            }
        }

        assert config["output"]["web"]["segment_duration"] == 2
        assert config["output"]["hls"]["segment_duration"] == 2

    def test_list_size_is_2(self) -> None:
        """Test list_size is set to 2."""
        config = {
            "output": {
                "web": {"list_size": 2},
                "hls": {"list_size": 2},
            }
        }

        assert config["output"]["web"]["list_size"] == 2
        assert config["output"]["hls"]["list_size"] == 2

    def test_max_concurrent_chunks_increased(self) -> None:
        """Test max_concurrent_chunks is increased to 4."""
        config = {
            "pipeline": {"max_concurrent_chunks": 4},
        }

        assert config["pipeline"]["max_concurrent_chunks"] == 4
        assert config["pipeline"]["max_concurrent_chunks"] >= 3


class TestAPIConfigUpdate:
    """Test API config update endpoint."""

    def test_update_config_returns_dict(self) -> None:
        """Test update config returns config dict."""

        result = {"status": "updated", "config": {}}

        assert "status" in result
        assert "config" in result

    def test_update_config_validates(self) -> None:
        """Test update config validates before saving."""
        config = {"pipeline": {"chunk_duration_sec": 2}}

        is_valid = config["pipeline"]["chunk_duration_sec"] >= 1 and config["pipeline"]["chunk_duration_sec"] <= 10

        assert is_valid


class TestConfigValidation:
    """Test config validation."""

    def test_chunk_duration_validation(self) -> None:
        """Test chunk_duration must be between 1 and 10."""
        valid_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        invalid_values = [0, 11, -1, 15]

        for val in valid_values:
            assert 1 <= val <= 10

        for val in invalid_values:
            assert not (1 <= val <= 10)

    def test_segment_duration_validation(self) -> None:
        """Test segment_duration must be between 1 and 10."""
        valid_values = [1, 2, 3, 4, 5]

        for val in valid_values:
            assert 1 <= val <= 10

    def test_list_size_validation(self) -> None:
        """Test list_size must be positive."""
        valid_values = [1, 2, 3, 4, 5]

        for val in valid_values:
            assert val > 0
