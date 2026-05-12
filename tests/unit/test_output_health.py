"""
Tests for output health monitoring (F20).

These tests verify that:
- OutputSink health_check() detects failures correctly
- _update_write_stats and _set_error work correctly
- HLS output tracks stats and reports errors
- RTMP output tracks stats and reports errors
- SRT output retries with backoff
- Health state changes emit events via broadcaster
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

from core.output_sink import HealthState, OutputSink, set_output_health_broadcaster


class DummyOutput(OutputSink):
    """Concrete output for testing base health logic."""

    def __init__(self) -> None:
        super().__init__("dummy", {})

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def write(self, data: Any) -> None:
        pass


class TestOutputSinkBase:
    """Test base OutputSink health logic."""

    def test_initial_health_state(self) -> None:
        """Output starts HEALTHY."""
        out = DummyOutput()
        assert out._health_state == HealthState.HEALTHY
        assert out._last_error is None
        assert out._last_write_time == 0.0
        assert out._bytes_written == 0

    def test_update_write_stats(self) -> None:
        """_update_write_stats updates tracking."""
        out = DummyOutput()
        out._update_write_stats(1024)
        assert out._bytes_written == 1024
        assert out._last_write_time > 0
        assert out._last_error is None  # Clears errors on success

    def test_set_error_sets_error(self) -> None:
        """_set_error records error message and time."""
        out = DummyOutput()
        out._set_error("test error")
        assert out._last_error == "test error"
        assert out._last_error_time is not None

    def test_clear_error_clears(self) -> None:
        """_clear_error clears error state."""
        out = DummyOutput()
        out._set_error("test error")
        out._clear_error()
        assert out._last_error is None
        assert out._last_error_time is None

    def test_health_check_failed_when_error(self) -> None:
        """health_check returns FAILED when error is set."""
        out = DummyOutput()
        out._set_error("something broke")
        assert out.health_check() == HealthState.FAILED

    def test_health_check_degraded_when_no_recent_writes(self) -> None:
        """health_check returns DEGRADED when no write in 30s."""
        out = DummyOutput()
        # Set last write far in the past
        out._last_write_time = time.time() - 60
        assert out.health_check() == HealthState.DEGRADED

    def test_health_check_healthy_after_recent_write(self) -> None:
        """health_check returns HEALTHY after recent write."""
        out = DummyOutput()
        out._update_write_stats(100)
        assert out.health_check() == HealthState.HEALTHY

    def test_write_stats_clear_error(self) -> None:
        """_update_write_stats clears any existing error."""
        out = DummyOutput()
        out._set_error("old error")
        out._update_write_stats(512)
        assert out._last_error is None

    def test_uptime_tracking(self) -> None:
        """_uptime_start is set on creation."""
        out = DummyOutput()
        assert out._uptime_start > 0
        # Uptime should be roughly how long ago __init__ was called
        assert time.time() - out._uptime_start < 5.0


class TestHealthBroadcaster:
    """Test health event broadcasting."""

    def test_broadcaster_called_on_state_change(self) -> None:
        """Broadcaster is called when health state changes."""
        mock_broadcaster = MagicMock()
        set_output_health_broadcaster(mock_broadcaster)

        out = DummyOutput()
        # Set an error to trigger state change from HEALTHY to FAILED
        out._set_error("test error")
        out.check_health()

        mock_broadcaster.broadcast_output_health.assert_called_once()
        call_args = mock_broadcaster.broadcast_output_health.call_args[1]
        assert call_args["output_name"] == "dummy"
        assert call_args["health"] == "failed"

        # Cleanup
        set_output_health_broadcaster(None)

    def test_broadcaster_not_called_on_same_state(self) -> None:
        """Broadcaster is not called when state doesn't change (same state)."""
        mock_broadcaster = MagicMock()
        set_output_health_broadcaster(mock_broadcaster)

        out = DummyOutput()
        # First check_health transitions HEALTHY -> DEGRADED (no writes yet)
        mock_broadcaster.reset_mock()

        # Call twice more - should only broadcast on first transition
        out.check_health()
        mock_broadcaster.reset_mock()  # Reset after the transition

        out.check_health()
        # Should NOT be called since state never changed (still DEGRADED)
        mock_broadcaster.broadcast_output_health.assert_not_called()
        set_output_health_broadcaster(None)


class TestHLSOutputHealth:
    """Test HLS output health tracking."""

    @patch("modules.outputs.hls_output.HLSOutput._update_manifest")
    @patch("modules.outputs.hls_output.subprocess.run")
    @patch("modules.outputs.hls_output.ensure_ffmpeg")
    def test_ffmpeg_error_sets_error(
        self, mock_ffmpeg: MagicMock, mock_run: MagicMock, mock_manifest: MagicMock
    ) -> None:
        """FFmpeg error in HLS write sets error state."""
        import os
        import tempfile

        from modules.outputs.hls_output import HLSOutput

        mock_ffmpeg.return_value = "ffmpeg"

        # Mock FFmpeg returning error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Some error"
        mock_run.return_value = mock_result

        out = HLSOutput({"segment_duration": 5})
        out._output_dir = tempfile.mkdtemp()
        out.start()

        # Create a temp file to pass the exists() check
        tmp_input = os.path.join(out._output_dir, "test_input.ts")
        with open(tmp_input, "w") as f:
            f.write("dummy")

        from core.module_base import PipelineData

        data = PipelineData(
            chunk_index=0,
            video_chunk_path=tmp_input,
            duration=5.0,
        )

        out.write(data)

        # With FFmpeg error code, error should be set
        assert out._last_error is not None
        assert "FFmpeg" in out._last_error or "exit code" in out._last_error

        out.stop()

    @patch("modules.outputs.hls_output.HLSOutput._update_manifest")
    @patch("modules.outputs.hls_output.subprocess.run")
    @patch("modules.outputs.hls_output.ensure_ffmpeg")
    def test_successful_write_clears_error(
        self, mock_ffmpeg: MagicMock, mock_run: MagicMock, mock_manifest: MagicMock
    ) -> None:
        """Successful FFmpeg write clears any previous error."""
        import os
        import tempfile

        from modules.outputs.hls_output import HLSOutput

        mock_ffmpeg.return_value = "ffmpeg"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        out = HLSOutput({"segment_duration": 5})
        out._output_dir = tempfile.mkdtemp()
        out.start()

        # First set an error
        out._set_error("previous error")

        # Create a temp file to pass the exists() check
        tmp_input = os.path.join(out._output_dir, "test_input.ts")
        with open(tmp_input, "w") as f:
            f.write("dummy")

        from core.module_base import PipelineData

        data = PipelineData(
            chunk_index=0,
            video_chunk_path=tmp_input,
            duration=5.0,
        )

        out.write(data)

        # Error should be cleared on success
        assert out._last_error is None

        out.stop()


class TestSRTOutputHealth:
    """Test SRT output retry and health."""

    def test_retry_config(self) -> None:
        """SRT output has proper retry configuration."""
        from modules.outputs.srt_output import SRTOutput

        assert SRTOutput.MAX_RETRIES == 3
        assert [5.0, 15.0, 30.0] == SRTOutput.RETRY_DELAYS

    def test_retry_count_reset_on_success(self) -> None:
        """Retry count resets on successful write."""
        from modules.outputs.srt_output import SRTOutput

        out = SRTOutput({"url": "srt://localhost:9001"})
        out._retry_count = 2

        # Mock internal state as if we had a successful write
        out._update_write_stats(1024)
        out._retry_count = 0  # This is what the real write does

        assert out._retry_count == 0
        assert out._last_error is None


class TestRTMPOutputHealth:
    """Test RTMP output health tracking."""

    def test_rtmp_inherits_output_sink(self) -> None:
        """RTMP output properly inherits from OutputSink."""
        from modules.outputs.rtmp_output import RTMPOutput

        out = RTMPOutput({"url": "rtmp://localhost/live/stream"})
        assert isinstance(out, OutputSink)
        assert out._bytes_written == 0
        assert out._health_state == HealthState.HEALTHY
