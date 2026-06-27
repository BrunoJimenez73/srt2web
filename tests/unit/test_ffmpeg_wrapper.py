"""
Tests for core.ffmpeg_wrapper — FFmpeg process management.

F165: Covers FFmpegProcess lifecycle (init, start, stop, is_alive),
FFmpegWrapper initialization, and pool integration.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.ffmpeg_pool import FFmpegPool
from core.ffmpeg_wrapper import FFmpegProcess, FFmpegWrapper


@pytest.mark.unit
class TestFFmpegProcess:
    """Unit tests for FFmpegProcess."""

    def test_init_defaults(self):
        proc = FFmpegProcess(["ffmpeg", "-version"], name="test")
        assert proc.name == "test"
        assert proc.args == ["ffmpeg", "-version"]
        assert proc.is_alive is False
        assert proc.returncode is None

    def test_init_with_stderr_callback(self):
        cb = MagicMock()
        proc = FFmpegProcess(["ffmpeg"], on_stderr=cb)
        assert proc.on_stderr is cb

    def test_stop_without_start(self):
        proc = FFmpegProcess(["ffmpeg"], name="test")
        proc.stop()
        assert proc.is_alive is False

    def test_stop_releases_pool(self):
        pool = MagicMock(spec=FFmpegPool)
        proc = FFmpegProcess(["ffmpeg"], name="test")
        proc._pool_ref = pool
        proc._pool_job_id = "job-1"
        proc.stop()
        pool.release.assert_called_once_with("job-1")
        assert proc._pool_job_id is None

    @patch("core.ffmpeg_wrapper.subprocess.Popen")
    def test_start_and_stop(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stderr = None
        mock_popen.return_value = mock_proc

        proc = FFmpegProcess(["ffmpeg", "-i", "test"], name="test")
        proc.start()
        assert proc._process is mock_proc
        mock_popen.assert_called_once()

        proc.stop(timeout=0.5)
        mock_proc.terminate.assert_called_once()
        assert proc._process is None


@pytest.mark.unit
class TestFFmpegWrapper:
    """Unit tests for FFmpegWrapper."""

    def test_init(self):
        wrapper = FFmpegWrapper(name="test_wrapper")
        assert wrapper.name == "test_wrapper"
        assert wrapper.ffmpeg_path is not None
        assert wrapper.ffprobe_path is not None

    def test_init_with_pool(self):
        pool = FFmpegPool(max_size=2)
        wrapper = FFmpegWrapper(pool=pool)
        assert wrapper._pool is pool

    @patch("core.ffmpeg_wrapper.subprocess.run")
    def test_run_command_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)
        wrapper = FFmpegWrapper()
        result = wrapper.run_command(["-version"])
        assert result.returncode == 0

    @patch("core.ffmpeg_wrapper.subprocess.run")
    def test_run_probe(self, mock_run):
        mock_run.return_value = MagicMock(stdout="probe_data", stderr="", returncode=0)
        wrapper = FFmpegWrapper()
        result = wrapper.run_probe(["-show_format", "test.ts"])
        assert result.returncode == 0
