"""
Unit tests for HLS Output module.
"""

from unittest.mock import patch

import pytest

from core.module_base import PipelineData


@pytest.fixture
def hls_config():
    return {
        "segment_duration": 10,
        "list_size": 3,
        "audio_offset_ms": 0,
        "subtitle_language": "es",
        "subtitle_language_name": "Spanish",
        "encoder_mode": "cpu",
        "video_crf": 23,
        "video_preset": "medium",
        "gpu_preset": "p4",
    }


class TestHLSOutputInit:
    """Tests for HLSOutput initialization."""

    def test_init_with_config(self, hls_config):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput(hls_config)
        assert output.name == "web"
        assert output._segment_duration == 10
        assert output._list_size == 3
        assert output._audio_offset_ms == 0

    def test_init_default_config(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({})
        assert output._segment_duration == 15
        assert output._list_size == 6
        assert output._segment_index == 0
        assert output._total_duration_emitted == 0.0

    def test_configure_updates_params(self, hls_config):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({"segment_duration": 5, "list_size": 4})
        assert output._segment_duration == 5
        assert output._list_size == 4

        output.configure(hls_config)
        assert output._segment_duration == 10
        assert output._list_size == 3


class TestHLSOutputStop:
    """Tests for HLSOutput stop (no external dependencies)."""

    def test_stop_resets_state(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({})
        output._hls_dir = "/tmp/test_hls"
        output.stop()
        assert output._hls_dir == ""

    def test_stop_calls_shutdown_pool(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({})
        with patch("modules.outputs.hls_output.shutdown_pool") as mock_shutdown:
            output.stop()
            mock_shutdown.assert_called_once()


class TestHLSOutputGetStatus:
    """Tests for HLSOutput get_status."""

    def test_get_status_idle(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({"encoder_mode": "cpu"})
        status = output.get_status()
        assert status.name == "video_muxer"
        assert status.processed_chunks == 0
        assert status.extra.get("encoder_mode") == "cpu"
        assert status.extra.get("encoder_label") == "H.264 CPU"

    def test_get_status_extra_fields(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({"encoder_mode": "cpu"})
        status = output.get_status()
        extra = status.extra
        assert "encoder_mode" in extra
        assert "actual_encoder" in extra
        assert "using_gpu" in extra
        assert "gpu_available" in extra
        assert "encoder_label" in extra


class TestHLSOutputGetStreamInfo:
    """Tests for HLSOutput get_stream_info."""

    def test_get_stream_info(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({})
        output._hls_dir = "/output/hls"
        info = output.get_stream_info()
        assert info["type"] == "web"
        assert info["hls_dir"] == "/output/hls"
        assert info["stream_url"] == "/hls/stream.m3u8"
        assert info["segment_duration"] == 15


class TestHLSOutputWrite:
    """Tests for HLSOutput write method."""

    def test_write_returns_on_none_path(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({})
        data = PipelineData(chunk_index=0, video_chunk_path=None)
        output.write(data)

    def test_write_returns_on_nonexistent_path(self):
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({})
        data = PipelineData(chunk_index=0, video_chunk_path="/nonexistent/file.ts")
        output.write(data)
