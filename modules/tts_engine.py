"""
TTS Engine Module — generates synthetic voice from text.

Supports 'edge-tts' for ultra-natural cloud AI voices (free, requires internet),
and 'piper' for fast, offline, and natural-sounding text-to-speech.
"""

import os
import json
import asyncio
import logging
import urllib.request
import threading
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState

logger = logging.getLogger("srt2web.module.tts_engine")


class TTSEngine(BaseModule):
    """
    Synthesizes speech from translated text (or original transcript).
    Provides natural AI voices.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._output_dir = output_dir
        self._tts_dir = ""
        self._engine = "edge-tts"  # "edge-tts" (online) or "piper" (offline)
        self._device = "auto"  # "auto", "cuda", or "cpu" (for piper)
        self._voice_model = "en-US-AriaNeural"  # Very natural female AI voice
        self._use_translated = True
        self._speed = 1.0  # TTS speech rate multiplier

        # Piper specific
        self._piper_voice = None

        super().__init__("tts_engine", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._engine = config.get("engine", self._engine)
        self._device = config.get("device", self._device)
        self._voice_model = config.get("voice", self._voice_model)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._speed = config.get("speed", self._speed)
        logger.info(
            f"TTS configured: voice={self._voice_model}, speed={self._speed}, engine={self._engine}, device={self._device}"
        )

    def start(self) -> None:
        """Initialize TTS engine."""
        self._state = ModuleState.STARTING

        self._tts_dir = os.path.join(self._output_dir, "temp_tts")
        os.makedirs(self._tts_dir, exist_ok=True)

        # Clean old TTS audio
        for f in os.listdir(self._tts_dir):
            if f.endswith(".wav"):
                try:
                    os.remove(os.path.join(self._tts_dir, f))
                except OSError:
                    pass

        try:
            if self._engine == "piper":
                self._init_piper()
            elif self._engine == "edge-tts":
                import edge_tts

                # Edge-TTS is a cloud service, no heavy local model to load,
                # but we verify the import.
                logger.info(
                    f"Edge-TTS ready to use voice '{self._voice_model}' (Online, ultra-natural)"
                )
            else:
                raise ValueError(f"Unknown TTS engine: {self._engine}")

            self._state = ModuleState.RUNNING
            logger.info("TTS Engine ready")

        except ImportError as e:
            self._state = ModuleState.ERROR
            self._error_message = f"TTS package not installed: {e}"
            logger.error(self._error_message)
            self.enabled = False
        except Exception as e:
            self._state = ModuleState.ERROR
            self._error_message = f"Failed to init TTS: {e}"
            logger.error(self._error_message)
            self.enabled = False

    def _init_piper(self):
        """Load offline Piper TTS model."""
        from piper import PiperVoice
        import onnxruntime
        import warnings

        model_path, config_path = self._ensure_piper_model(self._voice_model)

        logger.info(f"Loading Piper TTS voice: {self._voice_model} (Offline)...")

        providers = ["CPUExecutionProvider"]
        use_cuda = False

        if self._device == "cuda":
            if "CUDAExecutionProvider" in onnxruntime.get_available_providers():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                        self._piper_voice = PiperVoice.load(
                            model_path, config_path, use_cuda=True
                        )
                        use_cuda = True
                        logger.info("Using CUDA for Piper TTS (forced by config)")
                        return
                    except Exception as e:
                        logger.info("CUDA not available, falling back to CPU")
                        use_cuda = False
            else:
                logger.info("CUDA requested but not available, using CPU")
        elif self._device == "cpu":
            logger.info("Using CPU for Piper TTS (forced by config)")
        else:  # auto
            if "CUDAExecutionProvider" in onnxruntime.get_available_providers():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                        self._piper_voice = PiperVoice.load(
                            model_path, config_path, use_cuda=True
                        )
                        use_cuda = True
                        logger.info("Using CUDA for Piper TTS (auto-detected)")
                        return
                    except Exception as e:
                        logger.info(
                            "CUDA auto-detected but failed, falling back to CPU"
                        )
                        use_cuda = False

        self._piper_voice = PiperVoice.load(model_path, config_path, use_cuda=False)

    def stop(self) -> None:
        """Cleanup TTS resources."""
        self._state = ModuleState.STOPPING
        if self._piper_voice:
            self._piper_voice = None
        self._state = ModuleState.IDLE

    def _ensure_piper_model(self, voice_name: str) -> tuple[str, str]:
        """Download Piper ONNX model and JSON config if they don't exist."""
        models_dir = os.path.abspath(os.path.join(".", "models", "piper"))
        os.makedirs(models_dir, exist_ok=True)

        model_path = os.path.join(models_dir, f"{voice_name}.onnx")
        config_path = os.path.join(models_dir, f"{voice_name}.onnx.json")

        if os.path.exists(model_path) and os.path.exists(config_path):
            return model_path, config_path

        logger.info(
            f"Downloading Piper TTS model '{voice_name}' (this happens only once)..."
        )

        parts = voice_name.split("-")
        if len(parts) >= 3:
            lang_family = parts[0].split("_")[0]
            lang_code = parts[0]
            speaker = parts[1]
            quality = parts[2]

            base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{lang_family}/{lang_code}/{speaker}/{quality}/{voice_name}"

            try:
                urllib.request.urlretrieve(f"{base_url}.onnx", model_path)
                urllib.request.urlretrieve(f"{base_url}.onnx.json", config_path)
                logger.info("Piper model downloaded successfully")
                return model_path, config_path
            except Exception as e:
                # Clean up partial downloads
                if os.path.exists(model_path):
                    os.remove(model_path)
                if os.path.exists(config_path):
                    os.remove(config_path)
                raise RuntimeError(
                    f"Failed to download Piper model from {base_url}: {e}"
                )
        else:
            raise ValueError(f"Invalid Piper voice name format: {voice_name}")

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Synthesize text into speech.
        """
        text = data.translated_text if self._use_translated else data.transcript

        if not text:
            return data

        output_wav = os.path.join(self._tts_dir, f"tts_{data.chunk_index:06d}.wav")

        try:
            if self._engine == "edge-tts":
                self._run_edge_tts(text, output_wav)
            elif self._engine == "piper":
                self._run_piper_tts(text, output_wav)

            data.dubbed_audio_path = output_wav
            logger.debug(
                f"Generated {self._engine.upper()} for chunk {data.chunk_index}"
            )

        except Exception as e:
            logger.error(f"TTS generation error: {e}")

        return data

    def _format_speed(self, speed: float) -> str:
        """Convert speed multiplier to edge-tts rate format (+X% or -X%)."""
        delta = (speed - 1.0) * 100
        sign = "+" if delta >= 0 else ""
        return f"{sign}{delta:.0f}%"

    def _run_edge_tts(self, text: str, output_wav: str):
        """Run edge-tts to get highly natural audio."""
        import edge_tts

        temp_mp3 = output_wav.replace(".wav", ".mp3")
        rate = self._format_speed(self._speed)
        logger.debug(f"Generating TTS with rate={rate} (speed={self._speed})")

        async def _generate():
            communicate = edge_tts.Communicate(text, self._voice_model, rate=rate)
            await communicate.save(temp_mp3)

        # Use asyncio.run() which creates and manages event loop efficiently
        # This is more efficient than manually creating/closing loops
        asyncio.run(_generate())

        # Edge-TTS outputs MP3, but our mixer expects WAV.
        # We use FFmpeg to convert MP3 to WAV 16kHz
        import subprocess
        from core.ffmpeg_utils import ensure_ffmpeg

        ffmpeg = ensure_ffmpeg()

        cmd = [ffmpeg, "-y", "-i", temp_mp3, "-ar", "24000", "-ac", "1", output_wav]
        subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)

    def _run_piper_tts(self, text: str, output_wav: str):
        """Run local Piper TTS generation."""
        import wave
        import os
        from piper.config import SynthesisConfig

        if not self._piper_voice:
            logger.error("Piper voice not initialized")
            return

        try:
            length_scale = 1.0 / self._speed
            logger.debug(
                f"Synthesizing text with Piper: '{text[:50]}...' ({len(text)} chars), "
                f"speed={self._speed}, length_scale={length_scale:.2f}"
            )

            syn_config = SynthesisConfig(length_scale=length_scale)

            with wave.open(output_wav, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self._piper_voice.config.sample_rate)

                audio_chunks = self._piper_voice.synthesize(text, syn_config=syn_config)
                for chunk in audio_chunks:
                    wav_file.writeframes(chunk.audio_int16_bytes)

            if os.path.exists(output_wav):
                file_size = os.path.getsize(output_wav)
                logger.debug(
                    f"Piper TTS generated audio file: {output_wav} ({file_size} bytes)"
                )
                if file_size < 44:
                    logger.warning(
                        f"Generated WAV file is too small ({file_size} bytes), likely empty"
                    )
            else:
                logger.error(f"Piper TTS failed to generate output file: {output_wav}")

        except Exception as e:
            logger.error(f"Error during Piper TTS synthesis: {e}", exc_info=True)
