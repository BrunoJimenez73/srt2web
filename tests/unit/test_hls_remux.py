"""
Tests for HLS output remux path.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import os
import tempfile
import time
from dataclasses import dataclass

from core.module_base import PipelineData


@dataclass
class HLSOutputFixture:
    output: object
    mock_run: MagicMock


@pytest.fixture
def hls_output_with_mocks():
    """Create HLSOutput with active patches. Yields fixture object with output + mock_run."""
    with (
        patch("modules.outputs.hls_output.subprocess.run") as mock_run,
        patch("modules.outputs.hls_output.get_creation_flags", return_value=0),
        patch("modules.outputs.hls_output.filter_command", side_effect=lambda x: x),
        patch("modules.outputs.hls_output.os.path.exists", return_value=True),
        patch("modules.outputs.hls_output.os.path.getsize", return_value=1024),
    ):
        from modules.outputs.hls_output import HLSOutput

        config = {
            "hls_dir": tempfile.mkdtemp(),
            "segment_duration": 10,
            "encoder_mode": "auto",
            "audio_bitrate": "128k",
            "audio_codec": "aac",
            "audio_sample_rate": 44100,
        }
        out = HLSOutput(config)
        out._hls_dir = config["hls_dir"]
        yield HLSOutputFixture(output=out, mock_run=mock_run)


class TestIsH264:
    def test_ffprobe_returns_h264(self):
        from modules.outputs.hls_output import HLSOutput

        with patch("modules.outputs.hls_output.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "h264\n"
            mock_run.return_value.returncode = 0
            result = HLSOutput._is_h264("/path/to/video.ts")
            assert result is True

    def test_ffprobe_returns_hevc(self):
        from modules.outputs.hls_output import HLSOutput

        with patch("modules.outputs.hls_output.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "hevc\n"
            mock_run.return_value.returncode = 0
            result = HLSOutput._is_h264("/path/to/video.ts")
            assert result is False

    def test_ffprobe_fails_gracefully(self):
        from modules.outputs.hls_output import HLSOutput

        with patch("modules.outputs.hls_output.subprocess.run", side_effect=Exception("ffprobe not found")):
            result = HLSOutput._is_h264("/path/to/video.ts")
            assert result is False

    def test_ffprobe_timeout(self):
        from modules.outputs.hls_output import HLSOutput

        with patch("modules.outputs.hls_output.subprocess.run", side_effect=TimeoutError("timeout")):
            result = HLSOutput._is_h264("/path/to/video.ts")
            assert result is False


class TestWriteRemux:
    def test_remux_passthrough_encoder_mode(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        fx.output._encoder_config.encoder_mode = "passthrough"

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)

        assert fx.mock_run.called
        cmd = fx.mock_run.call_args[0][0]
        assert "-c:v" in cmd
        assert cmd[cmd.index("-c:v") + 1] == "copy"

    def test_remux_auto_with_h264_input(self, hls_output_with_mocks):
        from modules.outputs.hls_output import HLSOutput

        fx = hls_output_with_mocks

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(HLSOutput, "_is_h264", return_value=True),
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)

        assert fx.mock_run.called
        cmd = fx.mock_run.call_args[0][0]
        assert "-c:v" in cmd
        assert cmd[cmd.index("-c:v") + 1] == "copy"

    def test_reencode_auto_with_non_h264_input(self, hls_output_with_mocks):
        from modules.outputs.hls_output import HLSOutput

        fx = hls_output_with_mocks

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(HLSOutput, "_is_h264", return_value=False),
            patch.object(fx.output, "_get_encoder_config", return_value=("libx264", "medium", [])),
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)

        assert fx.mock_run.called
        cmd = fx.mock_run.call_args[0][0]
        if "-c:v" in cmd:
            assert cmd[cmd.index("-c:v") + 1] != "copy"

    def test_skip_when_disabled(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        fx.output._enabled = False
        data = PipelineData(video_chunk_path="/tmp/test.ts")
        fx.output.write(data)
        fx.mock_run.assert_not_called()

    def test_skip_when_no_input_path(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        data = PipelineData(video_chunk_path=None)
        fx.output.write(data)
        fx.mock_run.assert_not_called()

    def test_skip_when_input_missing(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        with patch("modules.outputs.hls_output.os.path.exists", return_value=False):
            data = PipelineData(video_chunk_path="/tmp/missing.ts")
            fx.output.write(data)
            fx.mock_run.assert_not_called()


class TestRemuxWithMixedAudio:
    def test_remux_with_mixed_audio_copies_video_encodes_audio(self, hls_output_with_mocks):
        from modules.outputs.hls_output import HLSOutput

        fx = hls_output_with_mocks
        fx.output._encoder_config.encoder_mode = "passthrough"

        data = PipelineData(
            video_chunk_path="/tmp/test.ts",
            mixed_audio_path="/tmp/mixed.wav",
            chunk_index=0,
            duration=10.0,
        )

        with (
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)

        assert fx.mock_run.called
        cmd = fx.mock_run.call_args[0][0]
        assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "copy"
        assert "-c:a" in cmd

    def test_remux_sets_output_hls_path(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        fx.output._encoder_config.encoder_mode = "passthrough"
        fx.mock_run.return_value.returncode = 0

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)

        assert data.output_hls_path is not None
        assert data.output_hls_path.endswith("master.m3u8")

    def test_remux_updates_segment_index(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        fx.output._encoder_config.encoder_mode = "passthrough"
        fx.mock_run.return_value.returncode = 0

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)

        assert fx.output._segment_index == 1

    def test_ffmpeg_nonzero_returncode(self, hls_output_with_mocks):
        fx = hls_output_with_mocks
        fx.output._encoder_config.encoder_mode = "passthrough"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        fx.mock_run.return_value = mock_result

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(fx.output, "_set_error") as mock_error,
            patch.object(fx.output, "_update_manifest"),
            patch.object(fx.output, "_clear_error"),
            patch.object(fx.output, "_update_write_stats"),
        ):
            fx.output.write(data)
            mock_error.assert_called_once()

    def test_ffmpeg_timeout(self, hls_output_with_mocks):
        import subprocess

        fx = hls_output_with_mocks
        fx.output._encoder_config.encoder_mode = "passthrough"

        fx.mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=60)

        data = PipelineData(video_chunk_path="/tmp/test.ts", chunk_index=0, duration=10.0)

        with (
            patch.object(fx.output, "_set_error") as mock_error,
        ):
            fx.output.write(data)
            mock_error.assert_called_once()
