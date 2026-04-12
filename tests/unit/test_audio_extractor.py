"""
Unit tests for AudioExtractor module.
"""

import os
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.audio_extractor import AudioExtractor
from core.module_base import PipelineData, ModuleState


class TestAudioExtractor:
    """Tests for AudioExtractor class."""

    def test_initialization(self):
        """Test module initialization."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        
        assert extractor.name == "audio_extractor"
        assert extractor.enabled is True

    def test_start(self):
        """Test module can be started."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor.start()
        
        assert extractor.state in (ModuleState.STARTING, ModuleState.RUNNING)

    def test_stop(self):
        """Test module can be stopped."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor.stop()
        
        assert extractor.state == ModuleState.IDLE

    def test_process_with_none_input(self):
        """Test processing with None input returns None."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        
        data = PipelineData(chunk_index=1, video_chunk_path=None)
        result = extractor._do_process(data)
        
        assert result.audio_chunk_path is None

    def test_get_status(self):
        """Test status reporting."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        status = extractor.get_status()
        
        assert status.name == "audio_extractor"

    def test_module_enabled_by_default(self):
        """Test that module is enabled by default."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        
        assert extractor.enabled is True