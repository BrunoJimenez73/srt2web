"""
Transcriber Module — speech-to-text using faster-whisper.

Takes extracted audio chunks and produces transcripts with timestamps.
"""

import os
import logging
import asyncio
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState, ModuleStatus
from core.model_cache import ModelCache

logger = logging.getLogger("srt2web.module.transcriber")


class Transcriber(BaseModule):
    """
    Transcribes audio chunks using the faster-whisper model.
    Performance is heavily dependent on the chosen model size and hardware (CPU vs GPU).
    """

    def __init__(self, config: Optional[dict] = None):
        self._model_size = "small"
        self._language = "es"
        self._device_config = "auto"
        self._model = None
        self._device = "cpu"
        self._compute_type = "int8"
        self._model_cache = ModelCache()
        super().__init__("transcriber", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._model_size = config.get("model", self._model_size)
        
        lang = config.get("language", self._language)
        self._language = None if lang.lower() == "auto" else lang
        
        self._device_config = config.get("device", self._device_config)

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
                f"Loading Whisper '{self._model_size}' model "
                f"on {self._device.upper()} ({self._compute_type})..."
            )
            
            # Avoid downloading logs spam
            os.environ["CT2_VERBOSE"] = "-1"
            
            # Use ModelCache for shared model instances
            self._model = self._model_cache.get_whisper_model(
                model_size=self._model_size,
                device=self._device,
                compute_type=self._compute_type
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
        Transcribe the audio chunk.
        """
        if not self._model or not data.audio_chunk_path:
            return data

        try:
            # Transcribe
            segments_iter, info = self._model.transcribe(
                data.audio_chunk_path,
                language=self._language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            # Extract text and store segment timing
            full_text = []
            segment_list = []
            
            for segment in segments_iter:
                text = segment.text.strip()
                if text:
                    full_text.append(text)
                    segment_list.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": text
                    })

            if full_text:
                data.transcript = " ".join(full_text)
                data.transcript_segments = segment_list
                data.detected_language = info.language
                
                logger.debug(f"Transcript: {data.transcript}")
                
                # Send to websocket logs if requested
                self.logger.info(f"[{info.language}] {data.transcript}")

        except Exception as e:
            logger.error(f"Transcription error: {e}")

        return data

    def get_status(self) -> ModuleStatus:
        """Get current status including device info."""
        status = super().get_status()
        status.extra["device"] = self._device
        status.extra["compute_type"] = self._compute_type
        status.extra["using_gpu"] = self._device == "cuda"
        return status
