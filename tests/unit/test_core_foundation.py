"""
Tests for core foundation modules (exceptions and types).

These tests verify the new exception hierarchy and type definitions
introduced in the refactoring.
"""

import pytest
from dataclasses import asdict
import time

from core.exceptions import (
    SRT2WebError,
    ConfigError,
    ValidationError,
    PipelineError,
    PipelineStateError,
    PipelineDataError,
    ModuleError,
    ModuleInitializationError,
    ModuleProcessingError,
    TranscriberError,
    TTSError,
    FFmpegError,
    GPUError,
    ResourceError,
    DependencyError,
)
from core.types import (
    PipelineState,
    ModuleState,
    LogLevel,
    InputType,
    OutputType,
    DeviceType,
    EncoderMode,
    PipelineData,
    ModuleStatus,
    PipelineStatus,
    LogMessage,
    SystemMetrics,
    ChunkInfo,
    AudioConfig,
    VideoConfig,
    HLSConfig,
)


# ============================================================================
# Tests for Exceptions
# ============================================================================

class TestExceptions:
    """Test suite for custom exceptions."""
    
    def test_srt2web_error_basic(self):
        """Test basic SRT2WebError creation."""
        error = SRT2WebError("Test error")
        assert error.message == "Test error"
        assert error.module is None
        assert error.context == {}
        assert str(error) == "Test error"
    
    def test_srt2web_error_with_module(self):
        """Test SRT2WebError with module name."""
        error = SRT2WebError("Test error", module="test_module")
        assert error.module == "test_module"
        assert str(error) == "[test_module] Test error"
    
    def test_srt2web_error_with_context(self):
        """Test SRT2WebError with context."""
        context = {"key": "value", "number": 42}
        error = SRT2WebError("Test error", context=context)
        assert error.context == context
        assert "key" in str(error)
    
    def test_config_error(self):
        """Test ConfigError."""
        error = ConfigError("Invalid config")
        assert error.module == "config"
        assert isinstance(error, SRT2WebError)
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid value")
        assert isinstance(error, ConfigError)
        assert isinstance(error, SRT2WebError)
    
    def test_pipeline_error(self):
        """Test PipelineError."""
        error = PipelineError("Pipeline failed")
        assert error.module == "pipeline"
    
    def test_pipeline_state_error(self):
        """Test PipelineStateError."""
        error = PipelineStateError("Invalid state transition")
        assert isinstance(error, PipelineError)
    
    def test_pipeline_data_error(self):
        """Test PipelineDataError."""
        error = PipelineDataError("Missing data")
        assert isinstance(error, PipelineError)
    
    def test_module_error(self):
        """Test ModuleError."""
        error = ModuleError("Module failed", module="test_module")
        assert error.module == "test_module"
    
    def test_module_initialization_error(self):
        """Test ModuleInitializationError."""
        error = ModuleInitializationError("Init failed", module="test")
        assert isinstance(error, ModuleError)
    
    def test_module_processing_error(self):
        """Test ModuleProcessingError."""
        error = ModuleProcessingError("Process failed", module="test")
        assert isinstance(error, ModuleError)
    
    def test_transcriber_error(self):
        """Test TranscriberError."""
        error = TranscriberError("Transcription failed")
        assert error.module == "transcriber"
        assert isinstance(error, ModuleError)
    
    def test_tts_error(self):
        """Test TTSError."""
        error = TTSError("TTS failed")
        assert error.module == "tts_engine"
    
    def test_ffmpeg_error(self):
        """Test FFmpegError."""
        error = FFmpegError("FFmpeg command failed")
        assert error.module == "ffmpeg"
        assert isinstance(error, DependencyError)
    
    def test_gpu_error(self):
        """Test GPUError."""
        error = GPUError("GPU not available")
        assert error.module == "resource"
        assert isinstance(error, ResourceError)
    
    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from SRT2WebError."""
        exceptions = [
            ConfigError("test"),
            ValidationError("test"),
            PipelineError("test"),
            PipelineStateError("test"),
            PipelineDataError("test"),
            ModuleError("test", module="test"),
            ModuleInitializationError("test", module="test"),
            ModuleProcessingError("test", module="test"),
            TranscriberError("test"),
            TTSError("test"),
            FFmpegError("test"),
            GPUError("test"),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, SRT2WebError), f"{type(exc).__name__} should inherit from SRT2WebError"


# ============================================================================
# Tests for Types - Enums
# ============================================================================

class TestEnums:
    """Test suite for enum types."""
    
    def test_pipeline_state_values(self):
        """Test PipelineState enum values."""
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.RUNNING.value == "running"
        assert PipelineState.ERROR.value == "error"
    
    def test_module_state_values(self):
        """Test ModuleState enum values."""
        assert ModuleState.IDLE.value == "idle"
        assert ModuleState.PROCESSING.value == "processing"
        assert ModuleState.DISABLED.value == "disabled"
    
    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.ERROR.value == "error"
    
    def test_input_type_values(self):
        """Test InputType enum values."""
        assert InputType.SRT.value == "srt"
        assert InputType.RTMP.value == "rtmp"
        assert InputType.FILE.value == "file"
    
    def test_output_type_values(self):
        """Test OutputType enum values."""
        assert OutputType.HLS.value == "hls"
        assert OutputType.WEBRTC.value == "webrtc"
    
    def test_device_type_values(self):
        """Test DeviceType enum values."""
        assert DeviceType.CPU.value == "cpu"
        assert DeviceType.CUDA.value == "cuda"
        assert DeviceType.MPS.value == "mps"
        assert DeviceType.AUTO.value == "auto"
    
    def test_encoder_mode_values(self):
        """Test EncoderMode enum values."""
        assert EncoderMode.SOFTWARE.value == "software"
        assert EncoderMode.NVENC.value == "nvenc"
        assert EncoderMode.VIDEOTOOLBOX.value == "videotoolbox"


# ============================================================================
# Tests for Types - Data Classes
# ============================================================================

class TestPipelineData:
    """Test suite for PipelineData."""
    
    def test_default_values(self):
        """Test PipelineData default values."""
        data = PipelineData()
        assert data.video_chunk_path is None
        assert data.audio_chunk_path is None
        assert data.transcript is None
        assert data.translation is None
        assert data.chunk_index == 0
        assert data.duration == 0.0
        assert data.errors == []
    
    def test_is_valid_property(self):
        """Test PipelineData is_valid property."""
        data = PipelineData()
        assert not data.is_valid
        
        data.video_chunk_path = "/path/to/video.ts"
        assert data.is_valid
        
        data.video_chunk_path = None
        data.audio_chunk_path = "/path/to/audio.wav"
        assert data.is_valid
    
    def test_has_audio_property(self):
        """Test PipelineData has_audio property."""
        data = PipelineData()
        assert not data.has_audio
        
        data.audio_chunk_path = "/path/to/audio.wav"
        assert data.has_audio
    
    def test_has_video_property(self):
        """Test PipelineData has_video property."""
        data = PipelineData()
        assert not data.has_video
        
        data.video_chunk_path = "/path/to/video.ts"
        assert data.has_video
    
    def test_has_transcript_property(self):
        """Test PipelineData has_transcript property."""
        data = PipelineData()
        assert not data.has_transcript
        
        data.transcript = "Hello world"
        assert data.has_transcript
    
    def test_has_translation_property(self):
        """Test PipelineData has_translation property."""
        data = PipelineData()
        assert not data.has_translation
        
        data.translation = "Hola mundo"
        assert data.has_translation


class TestModuleStatus:
    """Test suite for ModuleStatus."""
    
    def test_default_values(self):
        """Test ModuleStatus default values."""
        status = ModuleStatus(name="test_module")
        assert status.state == ModuleState.IDLE
        assert status.enabled is True
        assert status.processed_chunks == 0
        assert status.error_count == 0
    
    def test_is_processing_property(self):
        """Test ModuleStatus is_processing property."""
        status = ModuleStatus(name="test")
        assert not status.is_processing
        
        status.state = ModuleState.PROCESSING
        assert status.is_processing
    
    def test_is_healthy_property(self):
        """Test ModuleStatus is_healthy property."""
        status = ModuleStatus(name="test")
        assert status.is_healthy
        
        status.enabled = False
        assert not status.is_healthy
        
        status.enabled = True
        status.state = ModuleState.ERROR
        assert not status.is_healthy
    
    def test_update_processing_time(self):
        """Test ModuleStatus update_processing_time method."""
        status = ModuleStatus(name="test")
        
        status.update_processing_time(1.5)
        assert status.processed_chunks == 1
        assert status.last_processing_time == 1.5
        assert status.average_processing_time == 1.5
        
        status.update_processing_time(2.5)
        assert status.processed_chunks == 2
        assert status.last_processing_time == 2.5
        assert status.average_processing_time == 2.0  # (1.5 + 2.5) / 2


class TestPipelineStatus:
    """Test suite for PipelineStatus."""
    
    def test_default_values(self):
        """Test PipelineStatus default values."""
        status = PipelineStatus()
        assert status.state == PipelineState.IDLE
        assert status.modules == {}
        assert status.total_chunks_processed == 0
        assert not status.is_running
    
    def test_is_running_property(self):
        """Test PipelineStatus is_running property."""
        status = PipelineStatus()
        assert not status.is_running
        
        status.state = PipelineState.RUNNING
        assert status.is_running
        
        status.state = PipelineState.STARTING
        assert status.is_running
        
        status.state = PipelineState.STOPPING
        assert not status.is_running
    
    def test_all_modules_healthy_property(self):
        """Test PipelineStatus all_modules_healthy property."""
        status = PipelineStatus()
        assert status.all_modules_healthy  # No modules = healthy
        
        status.modules["module1"] = ModuleStatus(name="module1")
        assert status.all_modules_healthy
        
        status.modules["module1"].state = ModuleState.ERROR
        assert not status.all_modules_healthy


class TestLogMessage:
    """Test suite for LogMessage."""
    
    def test_default_values(self):
        """Test LogMessage default values."""
        msg = LogMessage(level=LogLevel.INFO, message="Test message")
        assert msg.module is None
        assert msg.context == {}
        assert msg.iso_timestamp is not None
    
    def test_to_dict_method(self):
        """Test LogMessage to_dict method."""
        msg = LogMessage(
            level=LogLevel.ERROR,
            message="Error occurred",
            module="test",
            context={"key": "value"}
        )
        d = msg.to_dict()
        
        assert d["level"] == "error"
        assert d["message"] == "Error occurred"
        assert d["module"] == "test"
        assert d["context"] == {"key": "value"}
        assert "timestamp" in d


class TestSystemMetrics:
    """Test suite for SystemMetrics."""
    
    def test_default_values(self):
        """Test SystemMetrics default values."""
        metrics = SystemMetrics()
        assert metrics.cpu_percent == 0.0
        assert metrics.gpu_available is False
        assert metrics.gpu_name is None
    
    def test_to_dict_method(self):
        """Test SystemMetrics to_dict method."""
        metrics = SystemMetrics(
            cpu_percent=45.2,
            memory_percent=67.8,
            gpu_available=True,
            gpu_name="NVIDIA GeForce RTX 3080"
        )
        d = metrics.to_dict()
        
        assert d["cpu_percent"] == 45.2
        assert d["memory_percent"] == 67.8
        assert d["gpu_available"] is True
        assert d["gpu_name"] == "NVIDIA GeForce RTX 3080"


class TestChunkInfo:
    """Test suite for ChunkInfo."""
    
    def test_default_values(self):
        """Test ChunkInfo default values."""
        chunk = ChunkInfo(
            index=0,
            path="/path/to/chunk.ts",
            duration=6.0,
            start_time=0.0,
            end_time=6.0
        )
        assert chunk.size_bytes == 0
        assert chunk.is_valid is True
    
    def test_is_valid_property(self):
        """Test ChunkInfo is_valid property."""
        chunk = ChunkInfo(
            index=0,
            path="/path/to/chunk.ts",
            duration=6.0,
            start_time=0.0,
            end_time=6.0
        )
        assert chunk.is_valid
        
        chunk.duration = 0
        assert not chunk.is_valid
        
        chunk.duration = 6.0
        chunk.path = None
        assert not chunk.is_valid


class TestAudioConfig:
    """Test suite for AudioConfig."""
    
    def test_default_values(self):
        """Test AudioConfig default values."""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.format == "s16le"
        assert config.bitrate is None


class TestVideoConfig:
    """Test suite for VideoConfig."""
    
    def test_default_values(self):
        """Test VideoConfig default values."""
        config = VideoConfig()
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 30.0
        assert config.codec == "h264"
        assert config.keyframe_interval == 10
        assert config.encoder_mode == EncoderMode.SOFTWARE


class TestHLSConfig:
    """Test suite for HLSConfig."""
    
    def test_default_values(self):
        """Test HLSConfig default values."""
        config = HLSConfig()
        assert config.segment_duration == 6.0
        assert config.playlist_size == 5
        assert config.allow_cache is True
        assert config.version == 3
        assert config.target_duration is None