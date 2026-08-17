"""
Regression tests for F183-F187 (diagnosed 2026-08-10 from user session logs).

F183 - Startup latency:
  - POST /api/start blocked the event loop (~40s, argos import 31.7s +
    Piper warm-up) → dashboard lost fetches ("failed to fetch outputs").
    Fix: pipeline.start() runs via asyncio.to_thread; core/warmup prewarms
    the expensive one-time imports at server startup; TTSEngine warms the
    Piper subprocess in a background thread.

F184 — Parallel-worker races (audio echoed/repeated + subtitles vanished):
  - TTSEngine lazy-load had no lock → two workers spawned two Piper
    subprocesses (log showed double load at 23:06:05/23:06:06).
  - SubtitleGenerator wrote chunks in arrival order → rolling playlist
    skipped fragments (subtitles disappeared).
  - AudioMixer crossfade _prev_end_sample read/written without a lock →
    later chunk's tail bled into an earlier chunk's head.

F185 — SRT stream froze after watchdog restart: FFmpeg renumbers
  chunk_%06d.ts from 0 on every fresh process, but srt_input kept a high
  _last_chunk_index → new chunks ignored until the counter caught up.

F187 — stop() port check raised WinError 10042 (WSAEOPNOTSUPP) on
  setsockopt(SO_LINGER) for UDP sockets → bind skipped → "port still in
  use" x3 + aggressive taskkill.
"""

import sys
import threading
import time
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.module_base import PipelineData


def _mk_wav(path: Path, seconds: float = 0.5, sr: int = 24000) -> Path:
    """Write a tiny mono 16-bit WAV for mixer tests."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * int(sr * seconds))
    return path


def _subtitle_data(chunk_index: int, cumulative: float, text: str | None = None) -> PipelineData:
    return PipelineData(
        chunk_index=chunk_index,
        duration=10.0,
        cumulative_duration=cumulative,
        translated_text=text if text is not None else f"texto {chunk_index}",
        translated_segments=[{"start": 0.0, "end": 9.0, "text": f"cue {chunk_index}"}],
        metadata={},
    )


# ── F183: model warm-up ────────────────────────────────────────────────


class TestModelWarmup:
    def test_prewarm_skipped_in_testing_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.warmup as warmup

        monkeypatch.setenv("SRT2WEB_TESTING", "1")
        monkeypatch.setattr(warmup, "_warmup_started", False)
        fake_thread = MagicMock()
        monkeypatch.setattr(warmup.threading, "Thread", fake_thread)

        warmup.prewarm_models(service="srt2web")

        fake_thread.assert_not_called()

    def test_prewarm_starts_daemon_background_thread(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.warmup as warmup

        monkeypatch.delenv("SRT2WEB_TESTING", raising=False)
        monkeypatch.setattr(warmup, "_warmup_started", False)
        fake_thread = MagicMock()
        monkeypatch.setattr(warmup.threading, "Thread", fake_thread)

        warmup.prewarm_models(service="srt2web")

        fake_thread.assert_called_once()
        _, kwargs = fake_thread.call_args
        assert kwargs.get("daemon") is True
        assert "warmup" in kwargs.get("name", "")
        fake_thread.return_value.start.assert_called_once()

    def test_prewarm_idempotent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.warmup as warmup

        monkeypatch.delenv("SRT2WEB_TESTING", raising=False)
        monkeypatch.setattr(warmup, "_warmup_started", False)
        fake_thread = MagicMock()
        monkeypatch.setattr(warmup.threading, "Thread", fake_thread)

        warmup.prewarm_models(service="srt2web")
        warmup.prewarm_models(service="srt2web")

        fake_thread.assert_called_once()


# ── F183/F184: TTS warm thread + single-subprocess guarantee ───────────


class StubThread:
    """Thread stand-in that records target/daemon/name and never runs."""

    def __init__(self, target=None, name="", daemon=False, **kwargs) -> None:
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self) -> None:
        self.started = True


@pytest.fixture
def stub_thread(monkeypatch: pytest.MonkeyPatch):
    from modules import tts_engine

    monkeypatch.setattr(tts_engine.threading, "Thread", StubThread)


class TestTTSWarmThread:
    def test_warm_thread_registered(self, tmp_path: Path) -> None:
        from modules import tts_engine
        from modules.tts_engine import TTSEngine

        created: list[StubThread] = []

        class RecordingThread(StubThread):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                created.append(self)

        original = tts_engine.threading.Thread
        try:
            tts_engine.threading.Thread = RecordingThread
            engine = TTSEngine({"engine": "piper", "voice": "es_MX-claude-high"}, output_dir=str(tmp_path))
            engine.start()
        finally:
            tts_engine.threading.Thread = original

        assert len(created) == 1
        thread = created[0]
        assert thread.daemon is True
        assert "tts-warmup" in thread.name
        assert thread.started is True

    def test_concurrent_lazy_load_single_subprocess(self, tmp_path: Path) -> None:
        """Two workers racing on first chunk must produce exactly ONE subprocess."""
        from modules.tts_engine import TTSEngine

        engine = TTSEngine({"engine": "piper"}, output_dir=str(tmp_path))
        engine._voice_loaded = False
        engine._stopped = False

        entered = threading.Event()
        release = threading.Event()
        calls = 0

        def fake_init_piper() -> None:
            nonlocal calls
            calls += 1
            entered.set()
            release.wait(timeout=10)
            engine._piper_manager = MagicMock()
            engine._piper_manager.using_cuda = False

        with patch.object(engine, "_init_piper", side_effect=fake_init_piper):
            results: list[bool] = []
            errors: list[Exception] = []

            def worker() -> None:
                try:
                    engine._ensure_piper_loaded()
                    results.append(engine._voice_loaded)
                except Exception as exc:
                    errors.append(exc)

            ta = threading.Thread(target=worker)
            tb = threading.Thread(target=worker)
            ta.start()
            tb.start()
            entered.wait(timeout=10)
            time.sleep(0.2)  # let the second worker reach the lock
            release.set()
            ta.join(timeout=10)
            tb.join(timeout=10)

        assert not errors, f"errors: {errors}"
        assert calls == 1, f"_init_piper called {calls} times — double subprocess bug"
        assert results == [True, True]

    def test_stop_during_warmup_discards_manager(self, tmp_path: Path) -> None:
        """If stop() runs while the warm thread is loading, the fresh
        subprocess must be killed and the voice not marked loaded."""
        from modules.tts_engine import TTSEngine

        engine = TTSEngine({"engine": "piper"}, output_dir=str(tmp_path))
        engine._stopped = False
        loading = threading.Event()
        loaded = threading.Event()

        def fake_init_piper() -> None:
            loading.set()
            loaded.wait(timeout=10)
            engine._piper_manager = MagicMock()
            engine._piper_manager.using_cuda = False

        with patch.object(engine, "_init_piper", side_effect=fake_init_piper):
            thread = threading.Thread(target=engine._ensure_piper_loaded, daemon=True)
            thread.start()
            loading.wait(timeout=10)
            engine.stop()
            loaded.set()
            thread.join(timeout=10)

        assert engine._voice_loaded is False
        assert engine._piper_manager is None


# ── F184: SubtitleGenerator ordered buffer ─────────────────────────────


@pytest.fixture
def subtitle_gen(tmp_path: Path):
    from modules.subtitle_generator_pkg import SubtitleGenerator

    gen = SubtitleGenerator(
        {"use_translated": True, "chunk_duration": 10, "hls_list_size": 10},
        output_dir=str(tmp_path),
    )
    gen.start()
    yield gen
    gen.stop()


class TestSubtitleOrderedBuffer:
    def test_out_of_order_chunks_buffered_and_flushed_in_order(self, subtitle_gen) -> None:
        # Chunk 3 arrives before 0/1/2 → buffered, nothing written yet
        subtitle_gen._do_process(_subtitle_data(3, 30.0))
        assert list(subtitle_gen._pending) == [3]
        assert subtitle_gen._last_chunk_index == -1
        assert subtitle_gen._fragment_writer.fragments == []

        # Chunk 2 arrives → still buffered (expected is 0)
        subtitle_gen._do_process(_subtitle_data(2, 20.0))
        assert sorted(subtitle_gen._pending) == [2, 3]
        assert subtitle_gen._fragment_writer.fragments == []

        # Chunk 1 arrives → still before baseline
        subtitle_gen._do_process(_subtitle_data(1, 10.0))

        # Chunk 0 arrives → baseline 0 written, then drain 1, 2, 3 in order
        subtitle_gen._do_process(_subtitle_data(0, 0.0))
        assert subtitle_gen._pending == {}
        indexes = [f["chunk_index"] for f in subtitle_gen._fragment_writer.fragments]
        assert indexes == [0, 1, 2, 3], f"fragments must be strictly ordered, got {indexes}"

    def test_duplicate_chunk_skipped(self, subtitle_gen) -> None:
        subtitle_gen._do_process(_subtitle_data(0, 0.0))
        subtitle_gen._do_process(_subtitle_data(0, 0.0))  # duplicate of baseline
        subtitle_gen._do_process(_subtitle_data(2, 20.0))  # buffered
        subtitle_gen._do_process(_subtitle_data(1, 10.0))  # writes + drains 2
        subtitle_gen._do_process(_subtitle_data(1, 10.0))  # duplicate now stale
        indexes = [f["chunk_index"] for f in subtitle_gen._fragment_writer.fragments]
        assert indexes == [0, 1, 2], f"duplicates must be dropped, got {indexes}"

    def test_in_order_start_written_immediately(self, subtitle_gen) -> None:
        """A perfectly ordered first chunk must not stall behind the buffer
        (regression guard for the f108 single-chunk artifact test)."""
        subtitle_gen._do_process(_subtitle_data(0, 0.0))
        assert subtitle_gen._pending == {}
        indexes = [f["chunk_index"] for f in subtitle_gen._fragment_writer.fragments]
        assert indexes == [0]

    def test_stale_chunk_after_write_skipped(self, subtitle_gen) -> None:
        subtitle_gen._do_process(_subtitle_data(0, 0.0))
        subtitle_gen._do_process(_subtitle_data(3, 30.0))  # buffered
        subtitle_gen._do_process(_subtitle_data(2, 20.0))  # buffered
        subtitle_gen._do_process(_subtitle_data(1, 10.0))  # writes + drains 2, 3
        subtitle_gen._do_process(_subtitle_data(1, 10.0))  # stale now
        indexes = [f["chunk_index"] for f in subtitle_gen._fragment_writer.fragments]
        assert indexes == [0, 1, 2, 3]

    def test_huge_gap_written_anyway(self, subtitle_gen) -> None:
        # expected=0, chunk 130 exceeds expected + MAX_PENDING → escape hatch
        subtitle_gen._do_process(_subtitle_data(130, 1300.0))
        subtitle_gen._do_process(_subtitle_data(130, 1300.0))
        indexes = [f["chunk_index"] for f in subtitle_gen._fragment_writer.fragments]
        assert indexes == [130]

    def test_concurrent_out_of_order_produces_ordered_fragments(self, subtitle_gen) -> None:
        errors: list[Exception] = []

        def worker(idx: int, cumulative: float) -> None:
            try:
                subtitle_gen._do_process(_subtitle_data(idx, cumulative))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(0, 0.0)),
            threading.Thread(target=worker, args=(1, 10.0)),
            threading.Thread(target=worker, args=(2, 20.0)),
            threading.Thread(target=worker, args=(3, 30.0)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"errors: {errors}"
        indexes = [f["chunk_index"] for f in subtitle_gen._fragment_writer.fragments]
        assert indexes == sorted(indexes) and indexes == [0, 1, 2, 3], f"got {indexes}"


# ── F184: AudioMixer crossfade lock ────────────────────────────────────


class TestAudioMixerCrossfadeLock:
    def test_concurrent_mix_does_not_crash(self, tmp_path: Path) -> None:
        from modules.audio_mixer import AudioMixer

        mixer = AudioMixer({"original_volume": 0.7, "tts_volume": 1.0}, output_dir=str(tmp_path))
        mixer.start()

        orig = _mk_wav(tmp_path / "orig.wav")
        tts = _mk_wav(tmp_path / "tts.wav", sr=22050)

        errors: list[Exception] = []

        def worker(idx: int) -> None:
            data = PipelineData(
                chunk_index=idx,
                duration=0.5,
                audio_chunk_path=str(orig),
                dubbed_audio_path=str(tts),
            )
            try:
                out = mixer._do_process(data)
                assert out.mixed_audio_path is not None
                assert Path(out.mixed_audio_path).exists()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 9)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"errors: {errors}"

    def test_crossfade_uses_previous_chunk_tail_atomically(self, tmp_path: Path) -> None:
        """With the lock, sequential chunks crossfade against the correct
        previous tail (content-level check)."""
        import numpy as np

        from modules.audio_mixer import AudioMixer

        mixer = AudioMixer({}, output_dir=str(tmp_path))
        mixer.start()

        directory = tmp_path / "wavs"
        directory.mkdir()

        for i in (1, 2):
            _mk_wav(directory / f"o{i}.wav", seconds=0.5)
            _mk_wav(directory / f"t{i}.wav", seconds=0.5)

        # Pre-seed a known previous tail (crossfade window = 0.04s * 24kHz)
        crossfade_samples = int(0.04 * 24000)
        mixer._prev_end_sample = np.full(crossfade_samples, 1000.0)

        data1 = PipelineData(
            chunk_index=0,
            duration=0.5,
            audio_chunk_path=str(directory / "o1.wav"),
            dubbed_audio_path=str(directory / "t1.wav"),
        )
        out1 = mixer._do_process(data1)
        assert out1.mixed_audio_path is not None
        with wave.open(str(out1.mixed_audio_path), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        mixed1 = np.frombuffer(raw, dtype=np.int16)

        # The first crossfade_samples of chunk 1 blend the seeded tail with
        # the chunk's own (silent) head: head == tail * fade_out.
        cf = crossfade_samples
        fade_out = np.linspace(1.0, 0.0, cf)
        assert np.allclose(mixed1[:cf].astype(np.float64), 1000.0 * fade_out, atol=1.0)

        # Cleanup
        mixer.stop()


# ── F185: SRT watchdog restart resets chunk index ──────────────────────


class TestSRTChunkIndexReset:
    def test_restart_resets_index_and_purges_stale_chunks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from modules.inputs import srt_input

        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        for name in ("chunk_000000.ts", "chunk_000010.ts", "chunk_000011.ts"):
            (chunks_dir / name).write_bytes(b"stale")

        src = srt_input.SRTInput({"listen_port": 9999, "mode": "listener"})
        src._chunks_dir = str(chunks_dir)
        src._ffmpeg_path = "ffmpeg"
        src._last_chunk_index = 11

        fake_proc = MagicMock()
        fake_proc.pid = 4242
        monkeypatch.setattr(srt_input.subprocess, "Popen", lambda *a, **k: fake_proc)

        class NoopThread:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def start(self) -> None:
                pass

        monkeypatch.setattr(srt_input.threading, "Thread", NoopThread)

        src._start_ffmpeg_process()

        assert src._last_chunk_index == -1, "index must reset so new chunks are consumed"
        assert list(chunks_dir.glob("chunk_*.ts")) == [], "stale chunks must be purged"


# ── F187: stop() port check survives SO_LINGER failure ─────────────────


class TestSRTStopPortCheck:
    def test_so_linger_wsaenotsupp_does_not_break_port_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import socket as real_socket

        from modules.inputs import srt_input

        so_linger = 13

        class FakeSocket:
            def __init__(self, *args, **kwargs) -> None:
                self.closed = False

            def setsockopt(self, level: int, optname: int, *args) -> None:
                if optname == so_linger:
                    raise OSError(10042, "WSAEOPNOTSUPP - SO_LINGER not supported on UDP")

            def bind(self, addr) -> None:
                pass

            def close(self) -> None:
                self.closed = True

        class FakeSocketModule:
            AF_INET = real_socket.AF_INET
            SOCK_DGRAM = real_socket.SOCK_DGRAM
            SOL_SOCKET = real_socket.SOL_SOCKET
            SO_REUSEADDR = real_socket.SO_REUSEADDR
            SO_LINGER = so_linger

            def socket(self, *args, **kwargs):
                return FakeSocket()

        fake_subprocess = MagicMock()
        fake_subprocess.run.return_value = MagicMock(returncode=1)
        monkeypatch.setitem(sys.modules, "socket", FakeSocketModule())
        monkeypatch.setitem(sys.modules, "subprocess", fake_subprocess)
        monkeypatch.setattr(srt_input.time, "sleep", lambda *a: None)

        src = srt_input.SRTInput({"listen_port": 9998, "mode": "listener"})
        src._watchdog = None
        src._ffmpeg_proc = None

        with caplog.at_level("INFO"):
            src.stop()

        assert "is now FREE" in caplog.text, "port check must succeed despite SO_LINGER raising"
        assert "still in use" not in caplog.text, "no aggressive taskkill loop for a free port"

    def test_so_linger_still_used_when_supported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Regression guard: when setsockopt works, behaviour is unchanged."""
        from modules.inputs import srt_input

        calls: list[tuple] = []

        class FakeSocket:
            def setsockopt(self, *args) -> None:
                calls.append(args)

            def bind(self, addr) -> None:
                pass

            def close(self) -> None:
                pass

        class FakeSocketModule:
            AF_INET = 2
            SOCK_DGRAM = 2
            SOL_SOCKET = 1
            SO_REUSEADDR = 2
            SO_LINGER = 13

            def socket(self, *args, **kwargs):
                return FakeSocket()

        fake_subprocess = MagicMock()
        fake_subprocess.run.return_value = MagicMock(returncode=1)
        monkeypatch.setitem(sys.modules, "socket", FakeSocketModule())
        monkeypatch.setitem(sys.modules, "subprocess", fake_subprocess)
        monkeypatch.setattr(srt_input.time, "sleep", lambda *a: None)

        src = srt_input.SRTInput({"listen_port": 9997, "mode": "listener"})
        src._watchdog = None
        src._ffmpeg_proc = None

        with caplog.at_level("INFO"):
            src.stop()

        sockets = [c for c in calls if c[0] == 1 and c[1] == 13]
        assert sockets, "SO_LINGER must still be set when supported"
        assert "is now FREE" in caplog.text
