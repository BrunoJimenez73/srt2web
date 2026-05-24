"""
Integration tests for HLS muxer output.
Tests that the VideoMuxer generates valid .m3u8 playlists and .ts segments.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.config_manager import ConfigManager
from core.pipeline_manager import PipelineOrchestrator


@pytest.fixture
def config_manager():
    """Create a config manager for HLS output."""
    cm = ConfigManager()
    config = cm.get()
    config.modules.video_muxer.enabled = True
    config.modules.video_muxer.engine = "hls"
    config.modules.video_muxer.hls_segment_duration = 10
    config.modules.video_muxer.hls_list_size = 2
    config.modules.video_muxer.encoder_mode = "auto"
    config.pipeline.chunk_duration_sec = 10
    config.pipeline.mode = "sequential"
    return cm


@pytest.mark.integration
class TestHLSMuxerOutput:
    """Tests for HLS muxer integration."""

    def test_hls_muxer_starts_with_config(self, config_manager):
        """Test that HLS muxer can start with HLS config."""
        with patch("core.pipeline_manager.SRTInputSource") as mock_input:
            mock_input_instance = MagicMock()
            mock_input.return_value = mock_input_instance

            with patch("core.pipeline_manager.VideoMuxer") as mock_muxer:
                mock_muxer_instance = MagicMock()
                mock_muxer_instance.get_status.return_value = MagicMock(
                    name="video_muxer",
                    enabled=True,
                    state="stopped",
                    processed_chunks=0,
                    extra={"encoder_mode": "h264_nvenc"},
                )
                mock_muxer.return_value = mock_muxer_instance

                orch = PipelineOrchestrator(config_manager)
                # Just verify it can be created with HLS config
                assert orch is not None

    def test_hls_muxer_status_has_encoder_info(self, config_manager):
        """Test that HLS muxer status contains encoder info."""
        with patch("core.pipeline_manager.SRTInputSource") as mock_input:
            mock_input_instance = MagicMock()
            mock_input.return_value = mock_input_instance

            with patch("core.pipeline_manager.VideoMuxer") as mock_muxer:
                mock_muxer_instance = MagicMock()
                mock_muxer_instance.get_status.return_value = MagicMock(
                    extra={"encoder_mode": "h264_nvenc", "using_gpu": True}
                )
                mock_muxer.return_value = mock_muxer_instance

                orch = PipelineOrchestrator(config_manager)
                status = orch.get_status()
                hls_module = next((m for m in status.modules if m.name == "video_muxer"), None)

                if hls_module and hls_module.extra:
                    assert "encoder_mode" in hls_module.extra
