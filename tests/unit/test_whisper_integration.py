"""
Integration tests for Whisper transcriber with real audio processing.
Note: These tests require faster-whisper to be installed.
"""
import os
import tempfile
import pytest
from pathlib import Path

# Add project root to path
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.transcriber import Transcriber
from core.module_base import PipelineData, ModuleState


@pytest.mark.unit
class TestWhisperIntegration:
    """Integration tests for Whisper transcriber with real audio processing."""
    
    def test_transcriber_cpu_configuration(self) -> None:
        pass
        """Test Whisper transcriber configuration for CPU."""
        # Skip if faster-whisper is not available
        faster_whisper = pytest.importorskip("faster_whisper")
        
        # Initialize transcriber with CPU device and tiny model for speed
        transcriber = Transcriber({
            "model": "tiny",
            "device": "cpu",
            "language": "en"
        })
        
        # Verify initial configuration
        assert transcriber._model_size == "tiny"
        assert transcriber._language == "en"
        assert transcriber._device_config == "cpu"
        
        # Start the transcriber
        transcriber.start()
        assert transcriber.state == ModuleState.RUNNING
        
        # Verify the device that was actually used
        assert transcriber._device == "cpu"
        assert transcriber._compute_type == "int8"
        
        # Cleanup
        transcriber.stop()
        assert transcriber.state == ModuleState.IDLE
    
    def test_transcriber_gpu_configuration(self) -> None:
        pass
        """Test Whisper transcriber configuration for GPU (simulated)."""
        # Skip if faster-whisper is not available
        faster_whisper = pytest.importorskip("faster_whisper")
        
        # Initialize transcriber with GPU device
        transcriber = Transcriber({
            "model": "tiny",
            "device": "cuda",  # Request GPU
            "language": "en"
        })
        
        # Verify initial configuration
        assert transcriber._model_size == "tiny"
        assert transcriber._language == "en"
        assert transcriber._device_config == "cuda"
        
        # Start the transcriber (will fall back to CPU if CUDA not available)
        transcriber.start()
        assert transcriber.state == ModuleState.RUNNING
        
        # Verify the device that was actually used
        # This will be "cpu" if CUDA is not available, which is correct behavior
        assert transcriber._device in ["cpu", "cuda"]
        if transcriber._device == "cuda":
            assert transcriber._compute_type == "float16"
        else:
            assert transcriber._compute_type == "int8"
        
        # Cleanup
        transcriber.stop()
        assert transcriber.state == ModuleState.IDLE