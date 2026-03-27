"""
Unit tests for VideoMuxer module.
"""

import os
import sys
import glob
import subprocess
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.video_muxer import VideoMuxer
from core.module_base import PipelineData, ModuleState


class TestableVideoMuxer(VideoMuxer):
    """Concrete VideoMuxer subclass for testing (implements abstract _do_process)."""

    def _do_process(self, data):
        return data


class TestVideoMuxer:
    """Tests for VideoMuxer class."""

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_start(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure):
        """Test module startup and initialization."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {
            "nvenc": True,
            "qsv": False,
            "amf": False,
            "vaapi": False,
            "videotoolbox": False,
        }
        mock_glob.return_value = []

        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()

        assert muxer.state == ModuleState.RUNNING
        assert muxer._ffmpeg_path == "/bin/ffmpeg"
        assert muxer._gpu_info["nvenc"] is True
        assert muxer._hls_dir == os.path.join("/tmp", "hls")

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_write_calls_process(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure):
        """Test that write() delegates to process()."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        mock_glob.return_value = []

        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()

        with patch.object(muxer, 'process') as mock_process:
            data = PipelineData(chunk_index=0, video_chunk_path="/tmp/chunk_0.ts")
            muxer.write(data)
            mock_process.assert_called_once_with(data)

    @patch("os.path.exists")
    def test_write_missing_input(self, mock_exists):
        """Test graceful handling of missing input chunk."""
        muxer = TestableVideoMuxer()
        mock_exists.return_value = False

        data = PipelineData(video_chunk_path="/missing.ts")
        result = muxer.write(data)
        assert result is None

    @patch("glob.glob")
    @patch("os.path.exists")
    def test_update_manifest(self, mock_exists, mock_glob):
        """Test HLS manifest generation."""
        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer._hls_dir = "/tmp/hls"
        muxer._segment_durations = {0: 4.123}

        mock_glob.return_value = ["/tmp/hls/seg_000000.ts"]

        def exists_side_effect(path):
            if "subs.vtt" in path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        with patch("builtins.open", mock_open()) as mocked_file:
            muxer._update_manifest()

            assert mocked_file.call_count >= 2

            all_writes = "".join(
                call.args[0] for call in mocked_file().write.call_args_list
            )
            assert "#EXTM3U" in all_writes
            assert "#EXTINF:4.123," in all_writes
            assert "seg_000000.ts" in all_writes

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_get_status_extra(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure):
        """Test that get_status includes GPU encoder info."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": True, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        mock_glob.return_value = []

        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()

        status = muxer.get_status()
        assert "encoder_mode" in status.extra
        assert "using_gpu" in status.extra
        assert "gpu_available" in status.extra

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_gpu_nvenc_detection(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure):
        """Test that NVENC GPU is detected correctly."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": True, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        mock_glob.return_value = []

        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()

        status = muxer.get_status()
        assert status.extra["using_gpu"] is True
        assert status.extra["encoder_mode"] == "gpu_nvenc"

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_cpu_fallback(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure):
        """Test CPU fallback when no GPU available."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        mock_glob.return_value = []

        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()

        status = muxer.get_status()
        assert status.extra["using_gpu"] is False
        assert status.extra["encoder_mode"] == "cpu"

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_stop(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure):
        """Test module stop."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        mock_glob.return_value = []

        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()
        muxer.stop()

        assert muxer.state == ModuleState.IDLE
