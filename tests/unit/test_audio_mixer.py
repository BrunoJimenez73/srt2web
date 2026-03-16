"""
Unit tests for AudioMixer module.
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

from modules.audio_mixer import AudioMixer
from core.module_base import PipelineData, ModuleState

class TestAudioMixer:
    """Tests for AudioMixer class."""

    @patch("modules.audio_mixer.ensure_ffmpeg")
    @patch("os.makedirs")
    @patch("os.listdir")
    def test_start(self, mock_listdir, mock_makedirs, mock_ensure):
        """Test module startup and cleanup of old files."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_listdir.return_value = ["old.wav", "readme.txt"]
        
        with patch("os.remove") as mock_remove:
            mixer = AudioMixer(output_dir="/tmp")
            mixer.start()
            
            assert mixer.state == ModuleState.RUNNING
            assert mixer._ffmpeg_path == "/bin/ffmpeg"
            # Should have removed exactly one WAV file
            mock_remove.assert_called_once_with(os.path.join("/tmp", "temp_mix", "old.wav"))

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_do_process_both_available(self, mock_exists, mock_run):
        """Test mixing when both original and TTS audio are present."""
        mixer = AudioMixer(output_dir="/tmp")
        mixer._ffmpeg_path = "/bin/ffmpeg"
        mixer._mixer_dir = "/tmp/mix"
        
        def side_effect(path):
            if path in ["/orig.wav", "/tts.wav"]: return True
            if "mix_000001.wav" in path: return True
            return False
        mock_exists.side_effect = side_effect
        mock_run.return_value = MagicMock(returncode=0)
        
        data = PipelineData(chunk_index=1, audio_chunk_path="/orig.wav")
        data.dubbed_audio_path = "/tts.wav"
        
        result = mixer._do_process(data)
        
        assert result.mixed_audio_path == os.path.join("/tmp/mix", "mix_000001.wav")
        mock_run.assert_called_once()
        
        # Verify FFmpeg command structure
        cmd = mock_run.call_args[0][0]
        assert "-filter_complex" in cmd
        assert "amix=inputs=2" in str(cmd)
        assert "volume=0.15" in str(cmd) # Default original volume

    @patch("os.path.exists")
    def test_do_process_only_original(self, mock_exists):
        """Test processing when only original audio is available."""
        mixer = AudioMixer()
        mock_exists.side_effect = lambda p: p == "/orig.wav"
        
        data = PipelineData(audio_chunk_path="/orig.wav", dubbed_audio_path=None)
        result = mixer._do_process(data)
        
        assert result.mixed_audio_path == "/orig.wav"

    @patch("os.path.exists")
    def test_do_process_missing_original(self, mock_exists):
        """Test processing when original audio is missing (should return unchanged)."""
        mixer = AudioMixer()
        mock_exists.return_value = False
        
        data = PipelineData(audio_chunk_path="/missing.wav", dubbed_audio_path="/tts.wav")
        result = mixer._do_process(data)
        
        assert result.mixed_audio_path is None

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_ffmpeg_error_handling(self, mock_exists, mock_run):
        """Test handling of FFmpeg errors during mixing."""
        mixer = AudioMixer(output_dir="/tmp")
        mixer._ffmpeg_path = "/bin/ffmpeg"
        mixer._mixer_dir = "/tmp/mix"
        
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stderr="Mix error")
        
        data = PipelineData(chunk_index=1, audio_chunk_path="/orig.wav", dubbed_audio_path="/tts.wav")
        result = mixer._do_process(data)
        
        # Should return data without mixed_audio_path set
        assert result.mixed_audio_path is None
