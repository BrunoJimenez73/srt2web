"""
Transcriber Module — speech-to-text using faster-whisper.

Takes extracted audio chunks and produces transcripts with timestamps.
Includes LRU cache for duplicate chunks (F68) and timeout protection (F67).
"""

import concurrent.futures
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Optional

from core.cache import LRUCache
from core.model_cache import ModelCache
from core.module_base import BaseModule, ModuleState, ModuleStatus, PipelineData

logger = logging.getLogger("srt2web.module.transcriber")


class Transcriber(BaseModule):
    """
    Transcribes audio chunks using the faster-whisper model.
    Performance is heavily dependent on the chosen model size and hardware (CPU vs GPU).

    Features:
    - LRU cache (F68): avoids re-transcribing identical chunks (e.g. silence, repeats)
    - Timeout protection (F67): prevents pipeline hangs on corrupted audio
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self._model_size = "small"
        self._language: str | None = "es"
        self._device_config = "auto"
        self._beam_size = 5
        self._timeout_sec = 120.0  # Default timeout for transcription
        self._model = None
        self._device = "cpu"
        self._compute_type = "int8"
        self._model_cache = ModelCache()
        # LRU cache for transcription results (F68)
        self._transcript_cache = LRUCache(maxsize=100, ttl_seconds=300)
        super().__init__("transcriber", config)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)
        self._model_size = config.get("model", self._model_size)

        lang = config.get("language", self._language)
        new_language = None if (lang or "").lower() == "auto" else lang

        # Check if language changed - needs model reload for proper detection
        model_needs_reload = False
        if new_language != self._language:
            model_needs_reload = True

        self._language = new_language
        self._device_config = config.get("device", self._device_config)
        self._beam_size = config.get("beam_size", self._beam_size)
        self._timeout_sec = config.get("timeout_sec", self._timeout_sec)

        # Reload model if language changed (hot-reload)
        if model_needs_reload and self._state == ModuleState.RUNNING:
            logger.info(f"Language changed from {self._language} to {new_language}, reloading Whisper model...")
            self.stop()
            self.start()

    def start(self) -> None:
        """Initialize and load the Whisper model using ModelCache."""
        self._state = ModuleState.STARTING

        try:
            import torch

            # Determine device and compute type
            if self._device_config == "auto":
                if torch.cuda.is_available():
                    self._device = "cuda"
                    self._compute_type = "float16"
                else:
                    self._device = "cpu"
                    self._compute_type = "int8"
            else:
                self._device = self._device_config
                self._compute_type = "float16" if self._device == "cuda" else "int8"

            logger.info(
                f"Loading Whisper '{self._model_size}' model " f"on {self._device.upper()} ({self._compute_type})..."
            )

            # Avoid downloading logs spam
            os.environ["CT2_VERBOSE"] = "-1"

            # Use ModelCache for shared model instances
            self._model = self._model_cache.get_whisper_model(
                model_size=self._model_size, device=self._device, compute_type=self._compute_type
            )

            self._state = ModuleState.RUNNING
            logger.info(f"Whisper model '{self._model_size}' loaded successfully on {self._device.upper()} (cached)")

        except ImportError:
            self._state = ModuleState.ERROR
            self._error_message = "faster-whisper package not installed"
            logger.error(self._error_message)
            self.enabled = False
        except Exception as e:
            self._state = ModuleState.ERROR
            self._error_message = f"Failed to load Whisper model: {e}"
            logger.error(self._error_message)
            self.enabled = False

    def stop(self) -> None:
        """Cleanup model resources and clear cache."""
        self._state = ModuleState.STOPPING
        if self._model:
            del self._model
            self._model = None

            # Force CUDA memory cleanup if applicable
            try:
                if self._device == "cuda":
                    import torch

                    torch.cuda.empty_cache()
            except ImportError:
                pass

        self._transcript_cache.clear()
        self._state = ModuleState.IDLE

    def _audio_cache_identity(self, data: PipelineData) -> str:
        """
        Return a stable identity for the audio chunk.
        Prefer content hashing so duplicated chunks in different files share cache entries.
        """
        path = data.audio_chunk_path or ""
        if path:
            try:
                digest = hashlib.sha256()
                with Path(path).open("rb") as audio_file:
                    for chunk in iter(lambda: audio_file.read(1024 * 1024), b""):
                        digest.update(chunk)
                return f"content:{digest.hexdigest()}"
            except OSError:
                logger.debug("Could not hash audio chunk for cache key: %s", path, exc_info=True)

        return f"metadata:{path}:{data.timestamp}:{data.duration}"

    def _make_cache_key(self, data: PipelineData) -> str:
        """
        Build a deterministic cache key from chunk attributes.
        Two chunks with the same audio bytes and transcription settings produce the same key,
        avoiding re-transcription of duplicate content (e.g. silence segments).
        """
        identity = self._audio_cache_identity(data)
        raw = f"{identity}:{self._language}:{self._model_size}:{self._beam_size}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _transcribe_impl(self, data: PipelineData) -> Optional[PipelineData]:
        """
        Actual transcription logic (uncached).
        Returns None if transcription should be skipped (timeout).
        """
        timeout_sec = self._timeout_sec

        def _transcribe_sync() -> tuple[Any, ...]:
            """Run transcription in a thread pool to allow timeout."""
            if self._model is None:
                raise RuntimeError("Whisper model not loaded")
            return self._model.transcribe(
                data.audio_chunk_path,
                language=self._language,
                beam_size=self._beam_size,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

        # Run transcription with timeout via thread pool
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_transcribe_sync)
        timed_out = False
        try:
            segments_iter, info = future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            timed_out = True
            future.cancel()
            logger.warning(
                f"Transcription timeout after {timeout_sec}s for chunk "
                f"{data.chunk_index} ({data.audio_chunk_path}) — skipping"
            )
            return None
        finally:
            executor.shutdown(wait=not timed_out, cancel_futures=timed_out)

        # Extract text and store segment timing
        full_text = []
        segment_list = []

        for segment in segments_iter:
            text = segment.text.strip()
            if text:
                full_text.append(text)
                segment_list.append({"start": segment.start, "end": segment.end, "text": text})

        if full_text:
            data.transcript = " ".join(full_text)
            data.transcript_segments = segment_list
            data.detected_language = info.language
            logger.debug(f"Transcript: {data.transcript}")
            self.logger.info(f"[{info.language}] {data.transcript}")

        return data

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Transcribe the audio chunk with LRU cache (F68) and timeout protection (F67).

        Cache hit (F68): returns cached transcript immediately, no GPU time wasted.
        Cache miss: runs transcription with timeout, stores result in cache.
        Timeout (F67): logs warning, returns data unchanged, pipeline continues.
        """
        if not self._model or not data.audio_chunk_path:
            return data

        # F68: Check LRU cache first
        cache_key = self._make_cache_key(data)
        cached = self._transcript_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Transcription cache hit for chunk {data.chunk_index} ({data.audio_chunk_path})")
            # Restore cached transcript fields without re-running the model
            data.transcript = cached.get("transcript")
            data.transcript_segments = cached.get("segments", [])
            data.detected_language = cached.get("language")
            return data

        # Cache miss: run actual transcription
        try:
            result = self._transcribe_impl(data)
        except Exception as e:
            logger.error(f"Transcription error for chunk {data.chunk_index}: {e}")
            return data

        if result is None:
            # Timeout — return data as-is (no transcript)
            return data

        # F68: Store in LRU cache for future hits
        self._transcript_cache.set(
            cache_key,
            {
                "transcript": result.transcript,
                "segments": result.transcript_segments,
                "language": result.detected_language,
            },
        )

        return result

    def get_status(self) -> ModuleStatus:
        """Get current status including device info."""
        status = super().get_status()
        status.extra["device"] = self._device
        status.extra["compute_type"] = self._compute_type
        status.extra["using_gpu"] = self._device == "cuda"
        return status
