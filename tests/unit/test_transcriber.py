"""
Unit tests for Transcriber module.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Mock faster_whisper and torch before importing Transcriber
# This handles the case where these are not installed in the test environment
mock_fw = MagicMock()
sys.modules["faster_whisper"] = mock_fw
mock_torch = MagicMock()
sys.modules["torch"] = mock_torch

from modules.transcriber import Transcriber
from core.module_base import PipelineData, ModuleState

class TestTranscriber:
    """Tests for Transcriber class."""

    def setup_method(self) -> None:
        """Reset mocks before each test."""
        mock_fw.WhisperModel.reset_mock()
        mock_torch.cuda.is_available.reset_mock()

    def test_init(self) -> None:
        """Test initialization and config."""
        trans = Transcriber({"model": "base", "language": "auto"})
        assert trans._model_size == "base"
        assert trans._language is None  # "auto" maps to None

    def test_start_auto_cpu(self) -> None:
        """Test model loading with CPU fallback."""
        mock_torch.cuda.is_available.return_value = False
        trans = Transcriber()
        
        trans.start()
        
        assert trans.state == ModuleState.RUNNING
        assert trans._device == "cpu"
        assert trans._compute_type == "int8"
        mock_fw.WhisperModel.assert_called_once()
        
        # Verify arguments to WhisperModel
        args, kwargs = mock_fw.WhisperModel.call_args
        assert kwargs["device"] == "cpu"
        assert kwargs["compute_type"] == "int8"

    def test_start_auto_gpu(self) -> None:
        """Test model loading with GPU."""
        mock_torch.cuda.is_available.return_value = True
        trans = Transcriber()
        
        trans.start()
        
        assert trans._device == "cuda"
        assert trans._compute_type == "float16"
        
        args, kwargs = mock_fw.WhisperModel.call_args
        assert kwargs["device"] == "cuda"
        assert kwargs["compute_type"] == "float16"

    def test_stop(self) -> None:
        """Test cleanup."""
        trans = Transcriber()
        trans._model = MagicMock()
        trans._device = "cuda"
        
        trans.stop()
        
        assert trans._model is None
        assert trans.state == ModuleState.IDLE
        mock_torch.cuda.empty_cache.assert_called_once()

    def test_do_process(self) -> None:
        """Test transcription processing."""
        trans = Transcriber()
        mock_model = MagicMock()
        trans._model = mock_model
        
        # Mock transcribe result: (segments_iterator, info)
        mock_seg = MagicMock()
        mock_seg.text = " Hello world "
        mock_seg.start = 0.5
        mock_seg.end = 2.5
        
        mock_info = MagicMock()
        mock_info.language = "en"
        
        mock_model.transcribe.return_value = ([mock_seg], mock_info)
        
        data = PipelineData(chunk_index=5, audio_chunk_path="/tmp/audio.wav")
        result = trans._do_process(data)
        
        # Verify results
        assert result.transcript == "Hello world"
        assert result.detected_language == "en"
        assert len(result.transcript_segments) == 1
        assert result.transcript_segments[0]["text"] == "Hello world"
        assert result.transcript_segments[0]["start"] == 0.5
        
        # Verify model call
        mock_model.transcribe.assert_called_once()
        args, kwargs = mock_model.transcribe.call_args
        assert args[0] == "/tmp/audio.wav"
        assert kwargs["vad_filter"] is True

    def test_do_process_no_model(self) -> None:
        """Test processing when model is not loaded."""
        trans = Transcriber()
        trans._model = None
        
        data = PipelineData(audio_chunk_path="/tmp/audio.wav")
        result = trans._do_process(data)
        
        assert result.transcript is None

    def test_do_process_error_handling(self) -> None:
        """Test error handling during transcription."""
        trans = Transcriber()
        mock_model = MagicMock()
        trans._model = mock_model
        mock_model.transcribe.side_effect = RuntimeError("Whisper error")
        
        data = PipelineData(audio_chunk_path="/tmp/audio.wav")
        result = trans._do_process(data)
        
        # Should return data unchanged (or at least not crash)
        assert result.transcript is None
