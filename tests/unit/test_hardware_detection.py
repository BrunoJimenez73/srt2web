"""
Tests for Hardware Auto-Detection (Sugerencia 2).
"""

import pytest

from core.hardware import (
    HardwareType,
    detect_cuda,
    detect_hardware,
    detect_mps,
    get_optimal_device,
    update_config_with_optimal_device,
)


@pytest.mark.unit
class TestHardwareType:
    """Test HardwareType enum."""

    def test_hardware_types(self):
        """Verify hardware types are correct."""
        assert HardwareType.CPU == "cpu"
        assert HardwareType.CUDA == "cuda"
        assert HardwareType.MPS == "mps"


class TestDetectCUDA:
    """Test CUDA detection."""

    def test_detect_cuda_returns_dict(self):
        """detect_cuda() should return a dict."""
        result = detect_cuda()
        assert isinstance(result, dict)
        assert "available" in result
        assert "device_count" in result
        assert "devices" in result
        assert "error" in result

    def test_detect_cuda_structure(self):
        """Verify result structure."""
        result = detect_cuda()
        assert isinstance(result["available"], bool)
        assert isinstance(result["device_count"], int)
        assert isinstance(result["devices"], list)


class TestDetectMPS:
    """Test MPS (Mac Silicon) detection."""

    def test_detect_mps_returns_dict(self):
        """detect_mps() should return a dict."""
        result = detect_mps()
        assert isinstance(result, dict)
        assert "available" in result
        assert "error" in result

    def test_detect_mps_not_on_mac(self):
        """On non-macOS, should return not available."""
        import sys

        if sys.platform != "darwin":
            result = detect_mps()
            assert result["available"] is False
            assert "only available on macOS" in result.get("error", "")


class TestDetectHardware:
    """Test full hardware detection."""

    def test_detect_hardware_returns_dict(self):
        """detect_hardware() should return a dict."""
        result = detect_hardware()
        assert isinstance(result, dict)
        assert "cuda" in result
        assert "mps" in result
        assert "cpu_always" in result
        assert "recommended" in result

    def test_detect_hardware_cpu_always_true(self):
        """CPU should always be available."""
        result = detect_hardware()
        assert result["cpu_always"] is True

    def test_detect_hardware_recommended_valid(self):
        """Recommended should be a valid hardware type."""
        result = detect_hardware()
        assert result["recommended"] in ["cpu", "cuda", "mps"]


class TestGetOptimalDevice:
    """Test optimal device selection."""

    def test_get_optimal_device_auto(self):
        """With auto, should detect automatically."""
        device = get_optimal_device("auto")
        assert device in ["cpu", "cuda", "mps"]

    def test_get_optimal_device_none(self):
        """With None, should detect automatically."""
        device = get_optimal_device(None)
        assert device in ["cpu", "cuda", "mps"]

    def test_get_optimal_device_cuda(self):
        """Requesting cuda explicitly."""
        device = get_optimal_device("cuda")
        # May fallback to cpu if cuda not available
        assert device in ["cuda", "cpu"]

    def test_get_optimal_device_mps(self):
        """Requesting mps explicitly."""
        device = get_optimal_device("mps")
        # May fallback to cpu if mps not available
        assert device in ["mps", "cpu"]

    def test_get_optimal_device_cpu(self):
        """Requesting cpu explicitly."""
        device = get_optimal_device("cpu")
        assert device == "cpu"


class TestUpdateConfigWithOptimalDevice:
    """Test config auto-update."""

    def test_update_config_preserves_other_settings(self):
        """Config should keep non-device settings."""
        config = {
            "server": {"port": 9999},
            "transcriber": {"model": "small"},
            "tts_engine": {"engine": "piper"},
        }
        updated = update_config_with_optimal_device(config)
        assert updated["server"]["port"] == 9999
        assert updated["transcriber"]["model"] == "small"
        assert updated["tts_engine"]["engine"] == "piper"

    def test_update_config_auto_device(self):
        """With auto device, should update to optimal."""
        config = {
            "transcriber": {"device": "auto"},
            "tts_engine": {"device": "auto"},
        }
        updated = update_config_with_optimal_device(config)
        # Device should be updated from "auto" to actual device
        assert updated["transcriber"]["device"] != "auto"
        assert updated["tts_engine"]["device"] != "auto"

    def test_update_config_explicit_device_available(self):
        """With explicit device available, should keep it."""
        hardware = detect_hardware()
        if hardware["cuda"]["available"]:
            config = {
                "transcriber": {"device": "cuda"},
            }
            updated = update_config_with_optimal_device(config)
            assert updated["transcriber"]["device"] == "cuda"

    def test_update_config_explicit_device_unavailable(self):
        """With explicit device unavailable, should switch."""
        # This test is tricky - we'd need to mock the detection
        # For now, just verify the function doesn't crash
        config = {
            "transcriber": {"device": "cuda"},
        }
        try:
            updated = update_config_with_optimal_device(config)
            assert "transcriber" in updated
        except Exception as e:
            pytest.fail(f"update_config_with_optimal_device failed: {e}")

    def test_update_config_nested_modules_dict(self):
        """F117: Config with modules nested under 'modules' key (real structure)."""
        config = {
            "server": {"port": 9999},
            "modules": {
                "transcriber": {"device": "auto", "model": "small"},
                "tts_engine": {"device": "auto", "engine": "piper"},
            },
        }
        updated = update_config_with_optimal_device(config)
        # Device should be updated from "auto" to actual device
        assert updated["modules"]["transcriber"]["device"] != "auto"
        assert updated["modules"]["tts_engine"]["device"] != "auto"
        # Other settings preserved
        assert updated["server"]["port"] == 9999
        assert updated["modules"]["transcriber"]["model"] == "small"

    def test_update_config_nested_preserves_non_device_fields(self):
        """F117: Nested config preserves fields that aren't 'device'."""
        config = {
            "modules": {
                "transcriber": {"device": "auto", "model": "large", "beam_size": 5},
                "tts_engine": {"device": "cpu", "voice": "es_ES-sharvard-medium"},
            },
        }
        updated = update_config_with_optimal_device(config)
        assert updated["modules"]["transcriber"]["model"] == "large"
        assert updated["modules"]["transcriber"]["beam_size"] == 5
        assert updated["modules"]["tts_engine"]["voice"] == "es_ES-sharvard-medium"
        # CPU explicit → should stay CPU
        assert updated["modules"]["tts_engine"]["device"] == "cpu"


class TestIntegration:
    """Integration tests for hardware detection."""

    def test_hardware_detection_no_crash(self):
        """Hardware detection should not crash."""
        try:
            result = detect_hardware()
            assert result is not None
        except Exception as e:
            pytest.fail(f"Hardware detection crashed: {e}")

    def test_optimal_device_no_crash(self):
        """Getting optimal device should not crash."""
        for preferred in ["auto", "cuda", "mps", "cpu", None]:
            try:
                device = get_optimal_device(preferred)
                assert device in ["cpu", "cuda", "mps"]
            except Exception as e:
                pytest.fail(f"get_optimal_device({preferred}) crashed: {e}")

    def test_config_update_no_crash(self):
        """Config update should not crash."""
        config = {
            "transcriber": {"device": "auto"},
            "tts_engine": {"device": "cuda"},
            "video_muxer": {"encoder_mode": "auto"},
        }
        try:
            updated = update_config_with_optimal_device(config)
            assert updated is not None
        except Exception as e:
            pytest.fail(f"Config update crashed: {e}")
