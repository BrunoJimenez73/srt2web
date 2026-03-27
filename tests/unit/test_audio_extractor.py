"""
Unit tests for AudioExtractor module.
"""

import os
import sys
import subprocess
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.audio_extractor import AudioExtractor
from core.module_base import PipelineData, ModuleState

class TestAudioExtractor:
    """Tests for AudioExtractor class."""

    @patch("modules.audio_extractor.ensure_ffmpeg")
    @patch("os.makedirs")
    def test_start(self, mock_makedirs, mock_ensure_ffmpeg):
        """Test module startup."""
        mock_ensure_ffmpeg.return_value = "/bin/ffmpeg"
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor.start()
        
        assert extractor.state == ModuleState.RUNNING
        assert extractor._ffmpeg_path == "/bin/ffmpeg"
        assert extractor._audio_dir == os.path.join("/tmp/output", "temp_audio")
        mock_makedirs.assert_called_once_with(os.path.join("/tmp/output", "temp_audio"), exist_ok=True)

    @patch("os.listdir")
    @patch("os.remove")
    def test_stop(self, mock_remove, mock_listdir):
        """Test module shutdown and cleanup."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor._audio_dir = "/tmp/output/temp_audio"
        mock_listdir.return_value = ["audio_000001.wav", "other_file.txt"]
        
        extractor.stop()
        
        assert extractor.state == ModuleState.IDLE
        mock_remove.assert_called_once_with(os.path.join("/tmp/output/temp_audio", "audio_000001.wav"))

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_do_process_success(self, mock_exists, mock_run):
        """Test successful audio extraction."""
        # Setup
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor._ffmpeg_path = "/bin/ffmpeg"
        extractor._audio_dir = "/tmp/output/temp_audio"
        
        # We need mock_exists to return True for the input video chunk
        # and also for the output audio chunk (after it's "created")
        def side_effect(path):
            if path == "/tmp/input.ts": return True
            if "audio_000001.wav" in path: return True
            return False
        mock_exists.side_effect = side_effect
        
        mock_run.return_value = MagicMock(returncode=0)
        
        data = PipelineData(chunk_index=1, video_chunk_path="/tmp/input.ts")
        result = extractor._do_process(data)
        
        assert result.audio_chunk_path == os.path.join("/tmp/output/temp_audio", "audio_000001.wav")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "/bin/ffmpeg"
        assert "-i" in cmd
        assert "/tmp/input.ts" in cmd

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_do_process_missing_input(self, mock_exists, mock_run):
        """Test processing with missing input file."""
        extractor = AudioExtractor()
        mock_exists.return_value = False
        
        data = PipelineData(chunk_index=1, video_chunk_path="/nonexistent.ts")
        result = extractor._do_process(data)
        
        assert result.audio_chunk_path is None
        mock_run.assert_not_called()

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_do_process_ffmpeg_error(self, mock_exists, mock_run):
        """Test handling of FFmpeg errors."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor._ffmpeg_path = "/bin/ffmpeg"
        extractor._audio_dir = "/tmp/output/temp_audio"
        
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stderr="FFmpeg error")
        
        data = PipelineData(chunk_index=1, video_chunk_path="/tmp/input.ts")
        result = extractor._do_process(data)
        
        assert result.audio_chunk_path is None

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_do_process_timeout(self, mock_exists, mock_run):
        """Test handling of FFmpeg timeout."""
        extractor = AudioExtractor(output_dir="/tmp/output")
        extractor._ffmpeg_path = "/bin/ffmpeg"
        extractor._audio_dir = "/tmp/output/temp_audio"
        
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=10)
        
        data = PipelineData(chunk_index=1, video_chunk_path="/tmp/input.ts")
        result = extractor._do_process(data)
        
        assert result.audio_chunk_path is None
