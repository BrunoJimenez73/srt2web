"""
Tests for Pipeline Validator module.
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.module_base import PipelineData
from core.pipeline_validator import (
    AudioValidator,
    TranscriptValidator,
    TranslationValidator,
    TTSValidator,
    MixValidator,
    PipelineValidator,
    ValidationResult,
)


def _make_data(**overrides: dict) -> PipelineData:
    """Factory for PipelineData test instances."""
    defaults: dict = {
        "chunk_index": 0,
        "timestamp": 1000.0,
        "duration": 4.0,
        "video_chunk_path": "/tmp/test.ts",
        "audio_chunk_path": None,
        "dubbed_audio_path": None,
        "transcript": None,
        "translated_text": None,
    }

    data = PipelineData()
    for k, v in defaults.items():
        setattr(data, k, v)
    for k, v in overrides.items():
        setattr(data, k, v)
    return data


class TestAudioValidator:
    def test_no_audio_path(self) -> None:
        v = AudioValidator()
        data = _make_data(audio_chunk_path=None, dubbed_audio_path=None)
        result = v.validate(data)
        assert result.passed

    def test_invalid_audio_path(self) -> None:
        v = AudioValidator()
        data = _make_data(audio_chunk_path="/nonexistent/file.wav")
        result = v.validate(data)
        assert result.passed  # no path = passthrough, don't fail

    def test_corrupt_small_file(self) -> None:
        v = AudioValidator()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"x" * 10)  # smaller than 44 byte WAV header
            path = f.name
        data = _make_data(audio_chunk_path=path)
        result = v.validate(data)
        os.unlink(path)
        assert not result.passed


class TestTranscriptValidator:
    def test_empty_transcript(self) -> None:
        v = TranscriptValidator()
        data = _make_data(transcript=None)
        data.transcript_segments = []
        result = v.validate(data)
        assert not result.passed

    def test_valid_transcript(self) -> None:
        v = TranscriptValidator()
        data = _make_data(transcript="Hello world")
        data.transcript_segments = [{"start": 0, "end": 1, "text": "Hello"}]
        result = v.validate(data)
        assert result.passed

    def test_low_confidence(self) -> None:
        v = TranscriptValidator()
        data = _make_data(transcript="maybe?")
        data.transcript_segments = [{"start": 0, "end": 1, "text": "maybe?", "confidence": 0.1}]
        result = v.validate(data, {"min_confidence": 0.3})
        assert not result.passed


class TestTranslationValidator:
    def test_no_translation(self) -> None:
        v = TranslationValidator()
        data = _make_data()
        data.translated_text = None
        result = v.validate(data)
        assert not result.passed

    def test_valid_translation(self) -> None:
        v = TranslationValidator()
        data = _make_data(transcript="Hello")
        data.translated_text = "Hola"
        result = v.validate(data)
        assert result.passed


class TestPipelineValidator:
    def test_unknown_stage(self) -> None:
        v = PipelineValidator()
        data = _make_data()
        result = v.validate(data, "nonexistent")
        assert result.passed

    def test_orchestrates_correctly(self) -> None:
        v = PipelineValidator()
        data = _make_data(transcript="Hello")
        data.translated_text = "Hola"
        data.transcript_segments = [{"start": 0, "end": 1, "text": "Hello"}]
        results = v.validate_all(data)
        assert len(results) > 0

    def test_should_continue_critical_fail(self) -> None:
        v = PipelineValidator()
        r = ValidationResult(stage="test", passed=False, is_critical=True)
        assert not v.should_continue(r)

    def test_should_continue_low_score(self) -> None:
        v = PipelineValidator()
        r = ValidationResult(stage="test", passed=False, score=0.1, is_critical=False)
        assert not v.should_continue(r)
