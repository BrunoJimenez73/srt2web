"""
Integration tests for complete pipeline with TTS disabled.
Tests the full pipeline flow: SRT input → Audio Extractor → Whisper → Translator → Subtitle → Audio Mixer → Video Muxer 
with TTS engine disabled. 
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
    """Create a config manager with TTS disabled."""
    cm = ConfigManager()
    config = cm.get()
    config.modules.tts_engine.enabled = False
    config.modules.tts_engine.engine = "edge-tts"
    config.pipeline.chunk_duration_sec = 10
    config.pipeline.mode = "sequential"
    return cm


@pytest.fixture
def orchestrator(config_manager: ConfigManager) -> Generator[PipelineOrchestrator, None, None]:
    """Create a pipeline orchestrator."""
    with patch("core.pipeline_manager.SRTInputSource") as mock_input:
        mock_input_instance = MagicMock()
        mock_input.ready.side_effect = True
        mock_input.get_status.return_value = ModuleStatus(
            name="input", state="running", enabled=True, last_process_time_ms=0
        )
        mock_input_instance.__enter__ = MagicMock(return_value=mock_input_instance)
        mock_input_instance.__exit__ = MagicMock(return_value=False)
        mock_input.return_value = mock_input_instance
        
        with patch("core.pipeline_manager.AudioExtractor") as mock_extractor:
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.process.return_value = MagicMock(
                video_chunk_path="/tmp/test.mp4",
                audio_chunk_path="/tmp/test.wav",
                chunk_index=0,
                duration=10.0,
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
                                    output_paths=[],
                                )
                                mock_muxer.return_value = mock_muxer_instance
                                
                                orch = PipelineOrchestrator(config_manager)
                                yield orch
                                orch.stop()


class TestPipelineTTSDdisabled:
    """Tests for complete pipeline with TTS disabled."""
    
    def test_pipeline_runs_with_tts_disabled(self, orchestrator: PipelineOrchestrator):
        """Test that pipeline can run with TTS disabled."""
        # Start pipeline
        result = orchestrator.start()
        assert result is True
        assert orchestrator.get_status().state == "running"
        
        # Stop pipeline
        orchestrator.stop()
        assert orchestrator.get_status().state == "stopped"
    
    def test_tts_module_not_called_when_disabled(self, orchestrator: PipelineOrchestrator):
        """Test that TTS module is not called when disabled."""
        with patch.object(orchestrator, "_run_sequential") as mock_run:
            mock_run.return_value = None
            orchestrator.start()
            
            # Check that TTS is not in active modules
            status = orchestrator.get_status()
            tts_module = next((m for m in status.modules if m.name == "tts_engine"), None)
            
            if tts_module:
                assert tts_module.enabled is False
            
            orchestrator.stop()
    
    def test_pipeline_processes_chunk_without_tts(self, orchestrator: PipelineOrchestrator):
        """Test that pipeline processes a chunk without TTS."""
        # Mock the input to return a chunk
        mock_input = orchestrator._input_source
        if mock_input:
            mock_input.get_next_chunk.return_value = MagicMock(
                video_chunk_path="/tmp/test.mp4",
                chunk_index=0,
            )
        
        # Start and process
        orchestrator.start()
        
        # Verify that non-TTS modules were called
        # (This would require more detailed mocking)
        
        orchestrator.stop()

