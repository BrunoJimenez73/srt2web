"""
Unit tests for Transcriber module.
"""

import concurrent.futures
import sys
from unittest.mock import MagicMock

import pytest

# Add project root to path

# Mock faster_whisper and torch before importing Transcriber
mock_fw = MagicMock()
sys.modules["faster_whisper"] = mock_fw
mock_torch = MagicMock()
sys.modules["torch"] = mock_torch

from core.module_base import ModuleState, PipelineData
from modules.transcriber import Transcriber


@pytest.mark.unit
class TestTranscriber:
    """Tests for Transcriber class."""

    def setup_method(self) -> None:
        """Reset mocks before each test."""
        mock_fw.WhisperModel.reset_mock()
        mock_torch.cuda.is_available.reset_mock()

    def test_init(self) -> None:
        """Test initialization and config."""
        trans = Transcriber({"model": "base", "language": "auto"})
        assert trans._model_size == "base"
        assert trans._language is None  # "auto" maps to None

    def test_start_auto_cpu(self) -> None:
        """Test model loading with CPU fallback."""
        mock_torch.cuda.is_available.return_value = False
        trans = Transcriber()

        trans.start()

        assert trans.state == ModuleState.RUNNING
        assert trans._device == "cpu"
        assert trans._compute_type == "int8"
        mock_fw.WhisperModel.assert_called_once()

        # Verify arguments to WhisperModel
        args, kwargs = mock_fw.WhisperModel.call_args
        assert kwargs["device"] == "cpu"
        assert kwargs["compute_type"] == "int8"

    def test_start_auto_gpu(self) -> None:
        """Test model loading with GPU."""
        mock_torch.cuda.is_available.return_value = True
        trans = Transcriber()

        trans.start()

        assert trans._device == "cuda"
        assert trans._compute_type == "float16"

        args, kwargs = mock_fw.WhisperModel.call_args
        assert kwargs["device"] == "cuda"
        assert kwargs["compute_type"] == "float16"

    def test_stop(self) -> None:
        """Test cleanup."""
        trans = Transcriber()
        trans._model = MagicMock()
        trans._device = "cuda"

        trans.stop()

        assert trans._model is None
        assert trans.state == ModuleState.IDLE
        mock_torch.cuda.empty_cache.assert_called_once()

    def test_do_process(self) -> None:
        """Test transcription processing."""
        trans = Transcriber()
        mock_model = MagicMock()
        trans._model = mock_model

        # Mock transcribe result: (segments_iterator, info)
        mock_seg = MagicMock()
        mock_seg.text = " Hello world "
        mock_seg.start = 0.5
        mock_seg.end = 2.5

        mock_info = MagicMock()
        mock_info.language = "en"

        mock_model.transcribe.return_value = ([mock_seg], mock_info)

        data = PipelineData(chunk_index=5, audio_chunk_path="/tmp/audio.wav")
        result = trans._do_process(data)

        # Verify results
        assert result.transcript == "Hello world"
        assert result.detected_language == "en"
        assert len(result.transcript_segments) == 1
        assert result.transcript_segments[0]["text"] == "Hello world"
        assert result.transcript_segments[0]["start"] == 0.5

        # Verify model call
        mock_model.transcribe.assert_called_once()
        args, kwargs = mock_model.transcribe.call_args
        assert args[0] == "/tmp/audio.wav"
        assert kwargs["vad_filter"] is True

    def test_do_process_no_model(self) -> None:
        """Test processing when model is not loaded."""
        trans = Transcriber()
        trans._model = None

        data = PipelineData(audio_chunk_path="/tmp/audio.wav")
        result = trans._do_process(data)

        assert result.transcript is None

    def test_do_process_error_handling(self) -> None:
        """Test error handling during transcription."""
        trans = Transcriber()
        mock_model = MagicMock()
        trans._model = mock_model
        mock_model.transcribe.side_effect = RuntimeError("Whisper error")

        data = PipelineData(audio_chunk_path="/tmp/audio.wav")
        result = trans._do_process(data)

        # Should return data unchanged (or at least not crash)
        assert result.transcript is None

    def test_transcription_cache_reuses_identical_audio_content(self, tmp_path) -> None:
        """Identical audio bytes in different files should hit the cache."""
        trans = Transcriber({"model": "tiny", "language": "en", "beam_size": 2})
        mock_model = MagicMock()
        trans._model = mock_model

        audio_a = tmp_path / "chunk-a.wav"
        audio_b = tmp_path / "chunk-b.wav"
        audio_a.write_bytes(b"same audio bytes")
        audio_b.write_bytes(b"same audio bytes")

        mock_seg = MagicMock()
        mock_seg.text = " Cached text "
        mock_seg.start = 0.0
        mock_seg.end = 1.0

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_model.transcribe.return_value = ([mock_seg], mock_info)

        first = trans._do_process(PipelineData(chunk_index=1, audio_chunk_path=str(audio_a)))
        second = trans._do_process(PipelineData(chunk_index=2, audio_chunk_path=str(audio_b)))

        assert first.transcript == "Cached text"
        assert second.transcript == "Cached text"
        assert second.detected_language == "en"
        mock_model.transcribe.assert_called_once()

    def test_transcription_cache_misses_when_audio_content_changes(self, tmp_path) -> None:
        """Different audio bytes should not reuse a cached transcript."""
        trans = Transcriber({"model": "tiny", "language": "en", "beam_size": 2})
        mock_model = MagicMock()
        trans._model = mock_model

        audio_a = tmp_path / "chunk-a.wav"
        audio_b = tmp_path / "chunk-b.wav"
        audio_a.write_bytes(b"first audio")
        audio_b.write_bytes(b"second audio")

        mock_seg = MagicMock()
        mock_seg.text = " Text "
        mock_seg.start = 0.0
        mock_seg.end = 1.0

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_model.transcribe.return_value = ([mock_seg], mock_info)

        trans._do_process(PipelineData(chunk_index=1, audio_chunk_path=str(audio_a)))
        trans._do_process(PipelineData(chunk_index=2, audio_chunk_path=str(audio_b)))

        assert mock_model.transcribe.call_count == 2

    def test_transcription_timeout_does_not_wait_for_executor_shutdown(self, monkeypatch) -> None:
        """Timeout should skip the chunk without blocking on executor shutdown."""
        trans = Transcriber({"timeout_sec": 10.0})
        trans._model = MagicMock()

        class TimeoutFuture:
            def __init__(self) -> None:
                self.cancelled = False

            def result(self, timeout=None):
                assert timeout == 10.0
                raise concurrent.futures.TimeoutError()

            def cancel(self) -> bool:
                self.cancelled = True
                return True

        class FakeExecutor:
            instances = []

            def __init__(self, max_workers: int) -> None:
                self.max_workers = max_workers
                self.future = TimeoutFuture()
                self.shutdown_kwargs = None
                FakeExecutor.instances.append(self)

            def submit(self, fn):
                self.submitted = fn
                return self.future

            def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
                self.shutdown_kwargs = {"wait": wait, "cancel_futures": cancel_futures}

        monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", FakeExecutor)

        data = PipelineData(chunk_index=7, audio_chunk_path="/tmp/stuck.wav")
        result = trans._transcribe_impl(data)

        executor = FakeExecutor.instances[0]
        assert result is None
        assert executor.max_workers == 1
        assert executor.future.cancelled is True
        assert executor.shutdown_kwargs == {"wait": False, "cancel_futures": True}
