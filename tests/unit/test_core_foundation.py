"""
Unit tests for core exceptions.
"""

import pytest
from core.exceptions import (
    SRT2WebError,
    ConfigurationError,
    ConfigurationValidationError,
    PipelineError,
    PipelineStateError,
    ModuleProcessingError,
    ModuleError,
    TranscriberError,
    TTSError,
    FFmpegError,
    InfrastructureError,
)


class TestExceptions:
    """Tests for exception classes."""

    def test_srt2web_error_basic(self):
        """Test basic error creation."""
        error = SRT2WebError("Test error")
        assert "Test error" in str(error)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert "Invalid config" in str(error)

    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError."""
        error = ConfigurationValidationError("Invalid value")
        assert "Invalid value" in str(error)

    def test_pipeline_error(self):
        """Test PipelineError."""
        error = PipelineError("Pipeline failed")
        assert "Pipeline failed" in str(error)

    def test_pipeline_state_error(self):
        """Test PipelineStateError."""
        error = PipelineStateError("Invalid state")
        assert "Invalid state" in str(error)

    def test_module_error(self):
        """Test ModuleError."""
        error = ModuleError("Module failed")
        assert "Module failed" in str(error)

    def test_module_processing_error(self):
        """Test ModuleProcessingError."""
        error = ModuleProcessingError("Process failed")
        assert "Process failed" in str(error)

    def test_transcriber_error(self):
        """Test TranscriberError."""
        error = TranscriberError("Transcription failed")
        assert "Transcription failed" in str(error)

    def test_tts_error(self):
        """Test TTSError."""
        error = TTSError("TTS failed")
        assert "TTS failed" in str(error)

    def test_ffmpeg_error(self):
        """Test FFmpegError."""
        error = FFmpegError("FFmpeg failed")
        assert "FFmpeg failed" in str(error)

    def test_exception_hierarchy(self):
        """Test exception inheritance."""
        assert issubclass(ConfigurationError, SRT2WebError)
        assert issubclass(ConfigurationValidationError, ConfigurationError)
        assert issubclass(PipelineError, SRT2WebError)
        assert issubclass(ModuleError, SRT2WebError)
        assert issubclass(TranscriberError, ModuleError)
        assert issubclass(TTSError, ModuleError)
        assert issubclass(FFmpegError, InfrastructureError)