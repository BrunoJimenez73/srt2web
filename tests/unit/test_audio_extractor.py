"""
Unit tests for AudioExtractor module.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.module_base import ModuleState, PipelineData
from modules.audio_extractor import AudioExtractor


@pytest.mark.unit
class TestAudioExtractor:
    """Tests for AudioExtractor class."""

    def test_initialization(self, temp_dir: str) -> None:
        """Test module initialization."""
        extractor = AudioExtractor(output_dir=temp_dir)

        assert extractor.name == "audio_extractor"
        assert extractor.enabled is True

    def test_start(self, temp_dir: str) -> None:
        """Test module can be started."""
        extractor = AudioExtractor(output_dir=temp_dir)
        extractor.start()

        assert extractor.state in (ModuleState.STARTING, ModuleState.RUNNING)

    def test_stop(self, temp_dir: str) -> None:
        """Test module can be stopped."""
        extractor = AudioExtractor(output_dir=temp_dir)
        extractor.stop()

        assert extractor.state == ModuleState.IDLE

    def test_process_with_none_input(self, temp_dir: str) -> None:
        """Test processing with None input returns None."""
        extractor = AudioExtractor(output_dir=temp_dir)

        data = PipelineData(chunk_index=1, video_chunk_path=None)
        result = extractor._do_process(data)

        assert result.audio_chunk_path is None

    def test_get_status(self, temp_dir: str) -> None:
        """Test status reporting."""
        extractor = AudioExtractor(output_dir=temp_dir)
        status = extractor.get_status()

        assert status.name == "audio_extractor"

    def test_module_enabled_by_default(self, temp_dir: str) -> None:
        """Test that module is enabled by default."""
        extractor = AudioExtractor(output_dir=temp_dir)

        assert extractor.enabled is True
