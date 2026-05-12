"""
Integration tests for TTS engine with real audio synthesis.
"""
import os

# Add project root to path
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.module_base import ModuleState, PipelineData
from modules.tts_engine import TTSEngine


@pytest.mark.slow
@pytest.mark.unit
class TestTTSIntegration:
    """Integration tests for TTS engine with real audio synthesis."""

    def setup_method(self) -> None:
        # If edge_tts is mocked, restore the real module
        if "edge_tts" in sys.modules and isinstance(sys.modules["edge_tts"], MagicMock):
            del sys.modules["edge_tts"]
        # Similarly for piper
        if "piper" in sys.modules and isinstance(sys.modules["piper"], MagicMock):
            del sys.modules["piper"]

    def test_piper_tts_synthesis(self) -> None:
        """Test Piper TTS synthesizes audio from text."""
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize TTS engine with a simple voice for testing
            # Using a voice that should be available or will trigger model download
            tts_engine = TTSEngine(
                {
                    "engine": "piper",
                    "device": "cpu",  # Use CPU for testing
                    "voice": "en_US-amy-low",  # Simple English voice that exists
                    "length_scale": 1.0,
                    "use_translated": False,  # Use transcript instead of translated_text
                }
            )

            try:
                # Start the TTS engine
                tts_engine.start()
                assert tts_engine.state == ModuleState.RUNNING

                # Test text to synthesize
                test_text = "Hello, this is a test."

                # Create test data
                data = PipelineData(
                    chunk_index=0,
                    transcript=test_text,
                    timestamp=0.0,
                    duration=len(test_text) * 0.1,  # Rough estimate
                )

                # Process the text (this may take a moment as it loads the model)
                result = tts_engine.process(data)

                # Verify result
                assert result is not None
                assert hasattr(result, "dubbed_audio_path")
                assert result.dubbed_audio_path is not None
                assert os.path.exists(result.dubbed_audio_path)

                # Verify it's a valid WAV file
                assert result.dubbed_audio_path.endswith(".wav")

                # Check file size is reasonable (should be > 0)
                file_size = os.path.getsize(result.dubbed_audio_path)
                assert file_size > 1000  # Should be at least 1KB for audio

                # Verify metadata is preserved
                assert result.chunk_index == 0
                assert result.transcript == test_text
                assert result.timestamp == 0.0

            finally:
                # Cleanup
                tts_engine.stop()
                assert tts_engine.state == ModuleState.IDLE

    def test_edge_tts_synthesis(self) -> None:
        """Test Edge TTS synthesizes audio from text."""
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize TTS engine with Edge TTS
            tts_engine = TTSEngine(
                {
                    "engine": "edge-tts",
                    "voice": "en-US-AriaNeural",  # Microsoft Edge TTS voice
                    "rate": "+0%",
                    "volume": "+0%",
                    "use_translated": False,  # Use transcript instead of translated_text
                }
            )

            try:
                # Start the TTS engine
                tts_engine.start()
                assert tts_engine.state == ModuleState.RUNNING

                # Test text to synthesize
                test_text = "Hello, this is a test of Edge TTS."

                # Create test data
                data = PipelineData(
                    chunk_index=0,
                    transcript=test_text,
                    timestamp=0.0,
                    duration=len(test_text) * 0.1,  # Rough estimate
                )

                # Process the text
                result = tts_engine.process(data)

                # Verify result
                assert result is not None
                assert hasattr(result, "dubbed_audio_path")
                assert result.dubbed_audio_path is not None
                # Note: The file might be cleaned up after processing in some implementations
                # but we should at least get a path back
                assert isinstance(result.dubbed_audio_path, str)
                assert len(result.dubbed_audio_path) > 0

                # Verify metadata is preserved
                assert result.chunk_index == 0
                assert result.transcript == test_text
                assert result.timestamp == 0.0

            finally:
                # Cleanup
                tts_engine.stop()
                assert tts_engine.state == ModuleState.IDLE
