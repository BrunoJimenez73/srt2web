"""
Tests for macOS hardware detection (Apple Silicon GPU).

These tests validate that MPS, VideoToolbox, and CoreML
detection work correctly without requiring actual Apple hardware.
Platform-specific conditions are mocked.
"""

from unittest.mock import MagicMock, patch


class TestMPSDetection:
    """Test MPS (Metal Performance Shaders) detection."""

    def test_mps_not_on_windows(self) -> None:
        """MPS should not be available on non-macOS platforms."""
        from core.hardware import detect_mps

        with patch("sys.platform", "win32"):
            result = detect_mps()
            assert result["available"] is False
            assert result["error"] == "MPS only available on macOS"

    def test_mps_detection_no_torch(self) -> None:
        """MPS detection should handle missing torch gracefully."""
        from core.hardware import detect_mps

        def _import_raiser(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("No module named torch")
            return __import__(name, *args, **kwargs)

        with patch("sys.platform", "darwin"):
            with patch("builtins.__import__", side_effect=_import_raiser):
                result = detect_mps()
                assert result["available"] is False
                assert "not installed" in (result.get("error") or "")

    def test_mps_available(self) -> None:
        """MPS detection should return available when torch MPS works."""
        from core.hardware import detect_mps

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.tensor.return_value.to.return_value.cpu.return_value = None

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                result = detect_mps()
                assert result["available"] is True
                assert result["error"] is None

    def test_mps_not_available(self) -> None:
        """MPS detection should return unavailable when torch MPS is not available."""
        from core.hardware import detect_mps

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                result = detect_mps()
                assert result["available"] is False

    def test_mps_tensor_creation_fails(self) -> None:
        """MPS detection should handle tensor creation failure."""
        from core.hardware import detect_mps

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.tensor.return_value.to.side_effect = RuntimeError("MPS device error")

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                result = detect_mps()
                assert result["available"] is False
                assert "MPS device error" in (result.get("error") or "")

    def test_get_optimal_device_mps(self) -> None:
        """get_optimal_device should return mps when MPS is available."""
        from core.hardware import get_optimal_device

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.tensor.return_value.to.return_value.cpu.return_value = None

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                device = get_optimal_device("auto")
                assert device == "mps"

    def test_get_optimal_device_mps_fallback(self) -> None:
        """get_optimal_device should fall back to cpu when MPS requested but unavailable."""
        from core.hardware import get_optimal_device

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                device = get_optimal_device("mps")
                assert device == "cpu"


class TestVideoToolboxDetection:
    """Test VideoToolbox hardware acceleration detection."""

    def test_videotoolbox_no_ffmpeg(self) -> None:
        """check_videotoolbox_support should return False when ffmpeg not found."""
        from core.ffmpeg_utils import check_videotoolbox_support

        with patch("core.ffmpeg_utils.find_ffmpeg", return_value=None):
            assert check_videotoolbox_support() is False

    def test_videotoolbox_supported(self) -> None:
        """check_videotoolbox_support should return True when h264_videotoolbox found."""
        from core.ffmpeg_utils import check_videotoolbox_support

        mock_run = MagicMock()
        mock_run.stdout = "h264_videotoolbox  - H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (VideoToolbox)"

        with patch("core.ffmpeg_utils.find_ffmpeg", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", return_value=mock_run):
                assert check_videotoolbox_support() is True

    def test_videotoolbox_not_supported(self) -> None:
        """check_videotoolbox_support should return False when h264_videotoolbox not found."""
        from core.ffmpeg_utils import check_videotoolbox_support

        mock_run = MagicMock()
        mock_run.stdout = "h264_libx264  - H.264/AVC (libx264)"

        with patch("core.ffmpeg_utils.find_ffmpeg", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", return_value=mock_run):
                assert check_videotoolbox_support() is False

    def test_videotoolbox_timeout(self) -> None:
        """check_videotoolbox_support should handle subprocess timeout."""
        from core.ffmpeg_utils import check_videotoolbox_support

        with patch("core.ffmpeg_utils.find_ffmpeg", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", side_effect=TimeoutError):
                assert check_videotoolbox_support() is False


class TestHardwareMonitorMacOS:
    """Test HardwareMonitor behavior on macOS."""

    def test_hardware_monitor_macos_no_pynvml(self) -> None:
        """HardwareMonitor should use sysctl fallback on macOS when pynvml missing."""

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"pynvml": None}):
                # Force reimport by creating fresh instance
                import importlib

                import core.hardware_monitor

                importlib.reload(core.hardware_monitor)
                mon = core.hardware_monitor.HardwareMonitor()

                # On macOS without pynvml, should still report GPU available via sysctl
                metrics = mon.get_system_metrics()
                assert metrics["gpu_available"] is True

    def test_hardware_monitor_windows_no_pynvml(self) -> None:
        """HardwareMonitor should report GPU unavailable on non-macOS without pynvml."""

        with patch("sys.platform", "win32"):
            with patch.dict("sys.modules", {"pynvml": None}):
                import importlib

                import core.hardware_monitor

                importlib.reload(core.hardware_monitor)
                mon = core.hardware_monitor.HardwareMonitor()

                metrics = mon.get_system_metrics()
                assert metrics["gpu_available"] is False


class TestOptimalDeviceConfig:
    """Test automatic device configuration."""

    def test_update_config_with_optimal_mps(self) -> None:
        """Config should be updated to use mps on macOS with MPS."""
        from core.hardware import update_config_with_optimal_device

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.tensor.return_value.to.return_value.cpu.return_value = None

        config = {
            "transcriber": {"device": "auto"},
            "tts_engine": {"device": "auto"},
        }

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                updated = update_config_with_optimal_device(config)
                assert updated["transcriber"]["device"] == "mps"
                assert updated["tts_engine"]["device"] == "mps"

    def test_update_config_preserves_explicit_device(self) -> None:
        """Config should preserve explicitly set device."""
        from core.hardware import update_config_with_optimal_device

        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.tensor.return_value.to.return_value.cpu.return_value = None

        config = {
            "transcriber": {"device": "cpu"},  # Explicit CPU
            "tts_engine": {"device": "auto"},
        }

        with patch("sys.platform", "darwin"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                updated = update_config_with_optimal_device(config)
                assert updated["transcriber"]["device"] == "cpu"  # Preserved
                assert updated["tts_engine"]["device"] == "mps"  # Auto-set
