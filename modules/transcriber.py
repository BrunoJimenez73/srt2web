"""
Transcriber Module — speech-to-text using faster-whisper.

Takes extracted audio chunks and produces transcripts with timestamps.
"""

import logging
import os
from typing import Optional

from core.model_cache import ModelCache
from core.module_base import BaseModule, ModuleState, ModuleStatus, PipelineData

logger = logging.getLogger("srt2web.module.transcriber")


class Transcriber(BaseModule):
    """
    Transcribes audio chunks using the faster-whisper model.
    Performance is heavily dependent on the chosen model size and hardware (CPU vs GPU).
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self._model_size = "small"
        self._language = "es"
        self._device_config = "auto"
        self._beam_size = 5
        self._timeout_sec = 120.0  # Default timeout for transcription
        self._model = None
        self._device = "cpu"
        self._compute_type = "int8"
        self._model_cache = ModelCache()
        super().__init__("transcriber", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._model_size = config.get("model", self._model_size)

        lang = config.get("language", self._language)
        new_language = None if lang.lower() == "auto" else lang

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
        """Cleanup model resources."""
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

        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Transcribe the audio chunk with timeout protection.

        If transcription exceeds timeout_sec (configurable via config.yaml,
        default 120s), the chunk is skipped with a warning log instead of
        hanging the pipeline indefinitely.
        """
        if not self._model or not data.audio_chunk_path:
            return data

        timeout_sec = self._timeout_sec

        try:
            import concurrent.futures

            def _transcribe_sync() -> tuple:
                """Run transcription in a thread pool to allow timeout."""
                return self._model.transcribe(
                    data.audio_chunk_path,
                    language=self._language,
                    beam_size=self._beam_size,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )

            # Run transcription with timeout via thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_transcribe_sync)
                try:
                    segments_iter, info = future.result(timeout=timeout_sec)
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        f"Transcription timeout after {timeout_sec}s for chunk "
                        f"{data.chunk_index} ({data.audio_chunk_path}) — skipping"
                    )
                    return data

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

                # Send to websocket logs if requested
                self.logger.info(f"[{info.language}] {data.transcript}")

        except Exception as e:
            logger.error(f"Transcription error for chunk {data.chunk_index}: {e}")

        return data

    def get_status(self) -> ModuleStatus:
        """Get current status including device info."""
        status = super().get_status()
        status.extra["device"] = self._device
        status.extra["compute_type"] = self._compute_type
        status.extra["using_gpu"] = self._device == "cuda"
        return status
