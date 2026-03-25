"""
Unit tests for AudioMixer module.
"""

import os
import sys
import subprocess
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.audio_mixer import AudioMixer
from core.module_base import PipelineData, ModuleState


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


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
            mixer = AudioMixer(output_dir=tempfile.mkdtemp())
            mixer.start()

            assert mixer.state == ModuleState.RUNNING
            assert mixer._ffmpeg_path == "/bin/ffmpeg"

    def test_do_process_missing_original(self, temp_dir):
        """Test processing when original audio is missing."""
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = os.path.join(temp_dir, "temp_mix")
        os.makedirs(mixer._mixer_dir, exist_ok=True)

        data = PipelineData(
            audio_chunk_path=os.path.join(temp_dir, "missing.wav"),
            dubbed_audio_path=os.path.join(temp_dir, "tts.wav")
        )
        result = mixer._do_process(data)

        assert result.mixed_audio_path is None

    def test_do_process_only_original(self, temp_dir):
        """Test processing when only original audio is available."""
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = os.path.join(temp_dir, "temp_mix")
        os.makedirs(mixer._mixer_dir, exist_ok=True)

        orig_path = os.path.join(temp_dir, "orig.wav")
        with open(orig_path, "wb") as f:
            f.write(b"fake wav data")

        with patch.object(mixer, '_get_audio_duration', return_value=4.0):
            data = PipelineData(audio_chunk_path=orig_path, dubbed_audio_path=None)
            result = mixer._do_process(data)

        assert result.mixed_audio_path == orig_path

    def test_do_process_both_available(self, temp_dir):
        """Test mixing when both original and TTS audio are present."""
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._ffmpeg_path = "ffmpeg"
        mixer._mixer_dir = os.path.join(temp_dir, "temp_mix")
        os.makedirs(mixer._mixer_dir, exist_ok=True)

        orig_path = os.path.join(temp_dir, "orig.wav")
        tts_path = os.path.join(temp_dir, "tts.wav")
        with open(orig_path, "wb") as f:
            f.write(b"fake wav")
        with open(tts_path, "wb") as f:
            f.write(b"fake wav")

        def mock_duration(path):
            return 4.0

        with patch.object(mixer, '_get_audio_duration', side_effect=mock_duration):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                # Create the expected output file
                expected_mix = os.path.join(mixer._mixer_dir, "mix_000001.wav")

                def run_side_effect(*args, **kwargs):
                    # Create the output file when ffmpeg runs
                    with open(expected_mix, "wb") as f:
                        f.write(b"mixed audio")
                    return MagicMock(returncode=0)

                mock_run.side_effect = run_side_effect

                data = PipelineData(
                    chunk_index=1,
                    audio_chunk_path=orig_path,
                    duration=4.0
                )
                data.dubbed_audio_path = tts_path
                result = mixer._do_process(data)

                assert result.mixed_audio_path == expected_mix

    def test_ffmpeg_error_handling(self, temp_dir):
        """Test handling of FFmpeg errors during mixing."""
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._ffmpeg_path = "ffmpeg"
        mixer._mixer_dir = os.path.join(temp_dir, "temp_mix")
        os.makedirs(mixer._mixer_dir, exist_ok=True)

        orig_path = os.path.join(temp_dir, "orig.wav")
        tts_path = os.path.join(temp_dir, "tts.wav")
        with open(orig_path, "wb") as f:
            f.write(b"fake wav")
        with open(tts_path, "wb") as f:
            f.write(b"fake wav")

        with patch.object(mixer, '_get_audio_duration', return_value=4.0):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="Mix error")

                data = PipelineData(
                    chunk_index=1,
                    audio_chunk_path=orig_path,
                    duration=4.0
                )
                data.dubbed_audio_path = tts_path
                result = mixer._do_process(data)

                # Should return data with original audio path as fallback
                assert result.mixed_audio_path == orig_path

    def test_duration_cache(self, temp_dir):
        """Test that duration cache works correctly."""
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._ffmpeg_path = "ffmpeg"

        test_file = os.path.join(temp_dir, "test.wav")
        with open(test_file, "wb") as f:
            f.write(b"fake audio")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="2.5\n", returncode=0)

            dur1 = mixer._get_audio_duration(test_file)
            assert dur1 == 2.5

            dur2 = mixer._get_audio_duration(test_file)
            assert dur2 == 2.5
            # Should use cache, no additional subprocess call
            assert mock_run.call_count == 1

    def test_last_measured_duration(self, temp_dir):
        """Test that last_measured_duration property works."""
        mixer = AudioMixer(output_dir=temp_dir)
        assert mixer.last_measured_duration == 0.0

        mixer._last_measured_duration = 4.5
        assert mixer.last_measured_duration == 4.5
