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
        }
        mock_glob.return_value = []

        muxer = VideoMuxer(output_dir="/tmp")
        muxer.start()

        assert muxer.state == ModuleState.RUNNING
        assert muxer._ffmpeg_path == "/bin/ffmpeg"
        assert muxer._gpu_info["nvenc"] is True
        assert muxer._hls_dir == os.path.join("/tmp", "hls")

    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("modules.video_muxer.VideoMuxer._update_manifest")
    @patch("os.remove")
    def test_do_process_success(self, mock_remove, mock_update, mock_exists, mock_run):
        """Test successful muxing of a video chunk."""
        muxer = VideoMuxer(output_dir="/tmp")
        muxer._ffmpeg_path = "/bin/ffmpeg"
        muxer._hls_dir = "/tmp/hls"
        muxer._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}

        def side_effect(path):
            if path == "/tmp/chunk_0.ts":
                return True
            if "seg_000000.ts" in path:
                return True
            return False

        mock_exists.side_effect = side_effect
        mock_run.return_value = MagicMock(returncode=0)

        data = PipelineData(
            chunk_index=0, video_chunk_path="/tmp/chunk_0.ts", duration=4.0
        )
        result = muxer._do_process(data)

        assert result.output_hls_path == os.path.join("/tmp/hls", "master.m3u8")
        assert muxer._segment_index == 1
        assert muxer._total_duration_emitted == 4.0
        mock_update.assert_called_once()
        # Input chunk should be removed
        mock_remove.assert_called_with("/tmp/chunk_0.ts")

        # Verify FFmpeg command
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "/bin/ffmpeg"
        assert "-output_ts_offset" in cmd
        assert "0.000" in cmd

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_do_process_gpu_nvenc(self, mock_exists, mock_run):
        """Test that GPU encoder is used when available."""
        muxer = VideoMuxer(output_dir="/tmp")
        muxer._ffmpeg_path = "/bin/ffmpeg"
        muxer._hls_dir = "/tmp/hls"
        muxer._gpu_info = {"nvenc": True, "qsv": False, "amf": False, "vaapi": False}

        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        data = PipelineData(chunk_index=0, video_chunk_path="/tmp/chunk_0.ts")
        muxer._do_process(data)

        cmd = mock_run.call_args[0][0]
        assert "h264_nvenc" in cmd
        assert "-preset" in cmd
        # With default gpu_preset='p3', which maps to balanced preset for NVENC
        assert "p3" in cmd

    @patch("glob.glob")
    @patch("os.path.exists")
    def test_update_manifest(self, mock_exists, mock_glob):
        """Test HLS manifest generation."""
        muxer = VideoMuxer(output_dir="/tmp")
        muxer._hls_dir = "/tmp/hls"
        muxer._segment_durations = {0: 4.123}

        mock_glob.return_value = ["/tmp/hls/seg_000000.ts"]

        # Side effect for os.path.exists: subs.vtt exists
        def exists_side_effect(path):
            if "subs.vtt" in path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        with patch("builtins.open", mock_open()) as mocked_file:
            muxer._update_manifest()

            # Should open stream.m3u8 and master.m3u8
            assert mocked_file.call_count >= 2

            # Verify stream.m3u8 content
            # Get all write calls across all file handles
            all_writes = "".join(
                call.args[0] for call in mocked_file().write.call_args_list
            )
            assert "#EXTM3U" in all_writes
            assert "#EXTINF:4.123," in all_writes
            assert "seg_000000.ts" in all_writes

            # Verify master.m3u8 content (since subs.vtt "exists")
            assert 'SUBTITLES="subs"' in all_writes
            assert 'NAME="Spanish"' in all_writes

    @patch("os.path.exists")
    def test_do_process_missing_input(self, mock_exists):
        """Test graceful handling of missing input chunk."""
        muxer = VideoMuxer()
        mock_exists.return_value = False

        data = PipelineData(video_chunk_path="/missing.ts")
        result = muxer._do_process(data)

        assert result.output_hls_path is None
        assert muxer._segment_index == 0
