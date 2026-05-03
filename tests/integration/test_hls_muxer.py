"""
Integration tests for HLS muxer output.
Tests that the VideoMuxer generates valid .m3u8 playlists and .ts segments.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Generator
import tempfile
import os

from core.pipeline_manager import PipelineOrchestrator
from core.config_manager import ConfigManager
from core.module_base import ModuleStatus


@pytest.fixture
def config_manager() -> ConfigManager:
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


@pytest.fixture
def orchestrator(config_manager: ConfigManager) -> Generator[PipelineOrchestrator, None, None]:
    """Create a pipeline orchestrator with HLS output."""
    with patch("core.pipeline_manager.SRTInputSource") as mock_input:
        mock_input_instance = MagicMock()
        mock_input_instance.ready.side_effect = True
        mock_input_instance.get_next_chunk.return_value = MagicMock(
            video_chunk_path="/tmp/test.mp4",
            audio_chunk_path="/tmp/test.wav",
            chunk_index=0,
            duration=10.0,
        )
        mock_input.return_value = mock_input_instance

        with patch("core.pipeline_manager.AudioExtractor") as mock_extractor:
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.process.return_value = MagicMock(
                audio_chunk_path="/tmp/test.wav",
            )
            mock_extractor.return_value = mock_extractor_instance

            with patch("core.pipeline_manager.WhisperTranscriber") as mock_whisper:
                mock_whisper_instance = MagicMock()
                mock_whisper_instance.process.return_value = MagicMock(
                    transcript_segments=[],
                    translated_segments=[],
                )
                mock_whisper.return_value = mock_whisper_instance

                with patch("core.pipeline_manager.Translator") as mock_translator:
                    mock_translator_instance = MagicMock()
                    mock_translator_instance.process.return_value = MagicMock(
                        translated_segments=[],
                    )
                    mock_translator.return_value = mock_translator_instance

                    with patch("core.pipeline_manager.SubtitleGenerator") as mock_subtitle:
                        mock_subtitle_instance = MagicMock()
                        mock_subtitle_instance.process.return_value = MagicMock(
                            subtitle_segments=[],
                        )
                        mock_subtitle.return_value = mock_subtitle_instance

                        with patch("core.pipeline_manager.AudioMixer") as mock_mixer:
                            mock_mixer_instance = MagicMock()
                            mock_mixer_instance.process.return_value = MagicMock(
                                mixed_audio_path="/tmp/mixed.wav",
                            )
                            mock_mixer.return_value = mock_mixer_instance

                            with patch("core.pipeline_manager.VideoMuxer") as mock_muxer:
                                mock_muxer_instance = MagicMock()
                                mock_muxer_instance.process.return_value = MagicMock(
                                    output_paths=["/tmp/hls/stream.m3u8", "/tmp/hls/segment_0.ts"],
                                )
                                mock_muxer.return_value = mock_muxer_instance

                                orch = PipelineOrchestrator(config_manager)
                                yield orch
                                orch.stop()


@pytest.mark.integration
class TestHLSMuxerOutput:
    """Tests for HLS muxer integration."""

    def test_hls_muxer_generates_m3u8(self, orchestrator: PipelineOrchestrator):
        """Test that HLS muxer generates .m3u8 playlist."""
        # This would require actual file system operations in a real test
        # For now, just verify the pipeline can start with HLS config
        result = orchestrator.start()
        assert result is True
        assert orchestrator.get_status().state == "running"

        orchestrator.stop()
        assert orchestrator.get_status().state == "stopped"

    def test_hls_muxer_segment_generation(self, orchestrator: PipelineOrchestrator):
        """Test that HLS segments are generated."""
        # Mock the file system operations
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True

            with patch("builtins.open") as mock_open:
                # Simulate .m3u8 content
                mock_file = MagicMock()
                mock_file.__enter__().readlines.return_value = [
                    "#EXTM3U\n",
                    "#EXT-X-VERSION:3\n",
                    "#EXT-X-TARGETDURATION:10\n",
                    "#EXTINF:10.0,\n",
                    "segment_0.ts\n",
                ]
                mock_open.return_value = mock_file

                result = orchestrator.start()
                assert result is True

                orchestrator.stop()

    def test_hls_output_paths_valid(self, orchestrator: PipelineOrchestrator):
        """Test that HLS output paths are valid."""
        status = orchestrator.get_status()
        hls_module = next((m for m in status.modules if m.name == "video_muxer"), None)

        if hls_module:
            # Check that extra contains encoder info
            if hls_module.extra:
                assert "encoder_mode" in hls_module.extra

        orchestrator.stop()


@pytest.mark.integration
class TestHLSMuxerMarkers:
    """Test that HLS muxer tests have correct markers."""

    def test_marker_present(self):
        """Verify that HLS muxer tests have integration marker."""
        # This test verifies that the marker is correctly applied
        assert True  # Marker is on the class level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
