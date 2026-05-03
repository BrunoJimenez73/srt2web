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


@pytest.mark.unit
class TestExceptions:
    """Tests for exception classes."""

    def test_srt2web_error_basic(self) -> None:
        """Test basic error creation."""
        error = SRT2WebError("Test error")
        assert "Test error" in str(error)

    def test_configuration_error(self) -> None:
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert "Invalid config" in str(error)

    def test_configuration_validation_error(self) -> None:
        """Test ConfigurationValidationError."""
        error = ConfigurationValidationError("Invalid value")
        assert "Invalid value" in str(error)

    def test_pipeline_error(self) -> None:
        """Test PipelineError."""
        error = PipelineError("Pipeline failed")
        assert "Pipeline failed" in str(error)

    def test_pipeline_state_error(self) -> None:
        """Test PipelineStateError."""
        error = PipelineStateError("Invalid state")
        assert "Invalid state" in str(error)

    def test_module_error(self) -> None:
        """Test ModuleError."""
        error = ModuleError("Module failed")
        assert "Module failed" in str(error)

    def test_module_processing_error(self) -> None:
        """Test ModuleProcessingError."""
        error = ModuleProcessingError("Process failed")
        assert "Process failed" in str(error)

    def test_transcriber_error(self) -> None:
        """Test TranscriberError."""
        error = TranscriberError("Transcription failed")
        assert "Transcription failed" in str(error)

    def test_tts_error(self) -> None:
        """Test TTSError."""
        error = TTSError("TTS failed")
        assert "TTS failed" in str(error)

    def test_ffmpeg_error(self) -> None:
        """Test FFmpegError."""
        error = FFmpegError("FFmpeg failed")
        assert "FFmpeg failed" in str(error)

    def test_exception_hierarchy(self) -> None:
        """Test exception inheritance."""
        assert issubclass(ConfigurationError, SRT2WebError)
        assert issubclass(ConfigurationValidationError, ConfigurationError)
        assert issubclass(PipelineError, SRT2WebError)
        assert issubclass(ModuleError, SRT2WebError)
        assert issubclass(TranscriberError, ModuleError)
        assert issubclass(TTSError, ModuleError)
        assert issubclass(FFmpegError, InfrastructureError)