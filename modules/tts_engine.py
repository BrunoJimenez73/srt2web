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
        self._voice_model = "en-US-AriaNeural"  # Very natural female AI voice
        self._use_translated = True
        self._speed = 1.0  # TTS speed multiplier (1.0 = normal, 2.0 = 2x faster)

        # Piper specific
        self._piper_voice = None

        super().__init__("tts_engine", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._engine = config.get("engine", self._engine)
        self._voice_model = config.get("voice", self._voice_model)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._speed = float(config.get("speed", self._speed))
        logger.debug(f"TTSEngine configured: speed={self._speed}")

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

        model_path, config_path = self._ensure_piper_model(self._voice_model)

        logger.info(f"Loading Piper TTS voice: {self._voice_model} (Offline)...")
        providers = ["CPUExecutionProvider"]
        if "CUDAExecutionProvider" in onnxruntime.get_available_providers():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        self._piper_voice = PiperVoice.load(
            model_path, config_path, use_cuda=("CUDAExecutionProvider" in providers)
        )

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

    def _run_edge_tts(self, text: str, output_wav: str):
        """Run edge-tts to get highly natural audio."""
        import edge_tts

        temp_mp3 = output_wav.replace(".wav", ".mp3")

        # Calculate rate for Edge-TTS: speed is multiplier (1.0=normal, 2.0=faster)
        # Edge-TTS rate: +50% means 50% faster, so rate = (speed - 1) * 100
        rate_percent = int((self._speed - 1.0) * 100)
        rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        async def _generate():
            communicate = edge_tts.Communicate(text, self._voice_model, rate=rate_str)
            await communicate.save(temp_mp3)

        # We need a new event loop to run async from a sync background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_generate())
        finally:
            loop.close()

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

        if not self._piper_voice:
            return

        with wave.open(output_wav, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self._piper_voice.config.sample_rate)
            self._piper_voice.synthesize(text, wav_file)
