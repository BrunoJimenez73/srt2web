"""
Unit tests for AudioMixer module (numpy-based mixing).
"""

import os
import sys
import tempfile
import wave
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.module_base import ModuleState, PipelineData
from modules.audio_mixer import AudioMixer


def create_wav(path, duration_s=4.0, sample_rate=16000):  # type: ignore
    """Create a valid WAV file with silence."""
    num_samples = int(duration_s * sample_rate)
    samples = b"\x00\x00" * num_samples
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples)


@pytest.fixture
def temp_dir():  # type: ignore
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestAudioMixer:
    def test_start(self, temp_dir) -> None:
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = Path(temp_dir) / "temp_mix"
        mixer._mixer_dir.mkdir(parents=True, exist_ok=True)
        mixer._state = ModuleState.RUNNING
        assert mixer.state == ModuleState.RUNNING

    def test_do_process_missing_original(self, temp_dir) -> None:
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = Path(temp_dir) / "temp_mix"
        mixer._mixer_dir.mkdir(parents=True, exist_ok=True)
        data = PipelineData(
            audio_chunk_path=os.path.join(temp_dir, "missing.wav"), dubbed_audio_path=os.path.join(temp_dir, "tts.wav")
        )
        result = mixer._do_process(data)
        assert result.mixed_audio_path is None

    def test_do_process_only_original(self, temp_dir) -> None:
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = Path(temp_dir) / "temp_mix"
        mixer._mixer_dir.mkdir(parents=True, exist_ok=True)
        orig_path = os.path.join(temp_dir, "orig.wav")
        create_wav(orig_path, duration_s=4.0)
        data = PipelineData(audio_chunk_path=orig_path, dubbed_audio_path=None)
        result = mixer._do_process(data)
        assert result.mixed_audio_path == orig_path
        assert result.duration == pytest.approx(4.0, abs=0.1)

    def test_do_process_both_available(self, temp_dir) -> None:
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = Path(temp_dir) / "temp_mix"
        mixer._mixer_dir.mkdir(parents=True, exist_ok=True)
        orig_path = os.path.join(temp_dir, "orig.wav")
        tts_path = os.path.join(temp_dir, "tts.wav")
        create_wav(orig_path, duration_s=4.0, sample_rate=16000)
        create_wav(tts_path, duration_s=3.0, sample_rate=22050)
        expected_mix = mixer._mixer_dir / "mix_000001.wav"
        data = PipelineData(chunk_index=1, audio_chunk_path=orig_path, dubbed_audio_path=tts_path, duration=4.0)
        result = mixer._do_process(data)
        assert result.mixed_audio_path == expected_mix
        assert expected_mix.exists()
        assert result.duration == pytest.approx(4.0, abs=0.1)

    def test_do_process_tts_longer_than_original(self, temp_dir) -> None:
        mixer = AudioMixer(output_dir=temp_dir)
        mixer._mixer_dir = Path(temp_dir) / "temp_mix"
        mixer._mixer_dir.mkdir(parents=True, exist_ok=True)
        orig_path = os.path.join(temp_dir, "orig.wav")
        tts_path = os.path.join(temp_dir, "tts.wav")
        create_wav(orig_path, duration_s=2.0, sample_rate=16000)
        create_wav(tts_path, duration_s=5.0, sample_rate=22050)
        data = PipelineData(chunk_index=1, audio_chunk_path=orig_path, dubbed_audio_path=tts_path, duration=2.0)
        result = mixer._do_process(data)
        assert result.duration == pytest.approx(2.0, abs=0.1)

    def test_last_measured_duration(self, temp_dir) -> None:
        mixer = AudioMixer(output_dir=temp_dir)
        assert mixer.last_measured_duration == 0.0
        mixer._last_measured_duration = 4.5
        assert mixer.last_measured_duration == 4.5
