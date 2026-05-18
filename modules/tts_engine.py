"""
TTS Engine Module — generates synthetic voice from text.

Supports 'edge-tts' for ultra-natural cloud AI voices (free, requires internet),
and 'piper' for fast, offline, and natural-sounding text-to-speech.
"""

import asyncio
import logging
import os
import time
import traceback
import wave
from pathlib import Path
from typing import Any, Optional

from core.module_base import BaseModule, ModuleState, ModuleStatus, PipelineData
from core.subprocess_utils import get_creation_flags

logger = logging.getLogger("srt2web.module.tts_engine")


class TTSEngine(BaseModule):
    """
    Synthesizes speech from translated text (or original transcript).
    Provides natural AI voices.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None, output_dir: str = "./output") -> None:
        self._output_dir = Path(output_dir)
        self._tts_dir = Path()
        self._engine = "edge-tts"  # "edge-tts" (online) or "piper" (offline)
        self._device = "auto"  # "auto", "cuda", or "cpu" (for piper)
        self._voice_model = "en-US-AriaNeural"  # Very natural female AI voice
        self._use_translated = True
        self._speed = 1.0  # TTS speech rate multiplier
        self._using_cuda = False  # Track actual CUDA usage

        # Piper specific
        self._piper_voice = None
        self._piper_manager: Any = None  # PiperSubprocessManager when engine is piper

        super().__init__("tts_engine", config, is_critical=False)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)
        old_voice = self._voice_model
        self._engine = config.get("engine", self._engine)
        self._device = config.get("device", self._device)
        self._voice_model = config.get("voice", self._voice_model)
        self._use_translated = config.get("use_translated", self._use_translated)
        # Ensure speed is float
        speed = config.get("speed", self._speed)
        try:
            self._speed = float(speed)
        except (ValueError, TypeError):
            self._speed = 1.0

        # If voice changed, reset loaded flag so it reloads lazily
        if old_voice != self._voice_model:
            self._voice_loaded = False
            self._piper_voice = None
            if self._piper_manager:
                self._piper_manager.stop()
                self._piper_manager = None
            logger.info(f"[Piper] Voice changed from {old_voice} to {self._voice_model}, will reload lazily")

        logger.info(
            f"TTS configured: voice={self._voice_model}, speed={self._speed}, engine={self._engine}, device={self._device}"
        )

    def start(self) -> None:
        """Initialize TTS engine."""
        self._state = ModuleState.STARTING
        self._piper_voice = None  # Don't load on start - load lazily
        self._using_cuda = False
        self._voice_loaded = False  # Track if voice has been loaded

        self._tts_dir = Path(self._output_dir) / "temp_tts"
        os.makedirs(self._tts_dir, exist_ok=True)
        self._tts_dir.mkdir(parents=True, exist_ok=True)

        # Clean old TTS audio
        try:
            for name in os.listdir(self._tts_dir):
                if name.endswith(".wav"):
                    path = self._tts_dir / name
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"Could not clean TTS temp dir: {e}")

        # For now, just verify config is valid - load voice lazily when needed
        if self._engine == "piper":
            logger.info(f"Piper TTS configured (voice: {self._voice_model}, will load lazily)")
            self._state = ModuleState.RUNNING
            logger.info("TTS Engine ready (lazy load)")
        elif self._engine == "edge-tts":
            logger.info(f"Edge-TTS ready to use voice '{self._voice_model}' (Online, ultra-natural)")
            self._state = ModuleState.RUNNING
            logger.info("TTS Engine ready")
        else:
            raise ValueError(f"Unknown TTS engine: {self._engine}")

    def _init_piper(self) -> None:
        """
        Initialize Piper TTS using a persistent subprocess with GPU support.

        The subprocess loads Piper with CUDA (if available) and stays alive
        to handle synthesis requests. This avoids the cuDNN 8.x crash that
        occurs when loading CUDA in the main Python process.
        """
        from modules.piper_loader import PiperSubprocessManager, check_piper_environment

        start_time = time.time()

        # Check environment
        logger.info("[PIPER_DEBUG] Checking Piper environment...")
        env_info = check_piper_environment()
        logger.info(
            f"[PIPER_DEBUG] Environment: piper={env_info['piper_available']}, "
            f"onnx={env_info['onnxruntime_available']}, "
            f"cuda={env_info['cuda_available']}"
        )

        if not env_info["piper_available"]:
            raise RuntimeError(f"Piper not installed: {env_info.get('piper_error', 'unknown')}")
        if not env_info["onnxruntime_available"]:
            raise RuntimeError(f"ONNX Runtime not installed: {env_info.get('onnx_error', 'unknown')}")

        # Get model paths
        model_path, config_path = self._ensure_piper_model(self._voice_model)
        logger.info(f"[PIPER_DEBUG] Model path resolved in {time.time() - start_time:.1f}s")

        # Start persistent subprocess with GPU
        self._piper_manager = PiperSubprocessManager()
        result = self._piper_manager.start(
            model_path=model_path,
            config_path=config_path,
            device=self._device,
        )

        elapsed = time.time() - start_time
        logger.debug(f"[PIPER_DEBUG] Persistent subprocess started after {elapsed:.1f}s")

        if result["status"] != "success":
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Failed to start Piper subprocess: {error_msg}")
            raise RuntimeError(f"Failed to load Piper voice: {error_msg}")

        self._using_cuda = self._piper_manager.using_cuda
        logger.debug(
            f"[PIPER_DEBUG] Piper ready: CUDA={self._using_cuda}, " f"sample_rate={self._piper_manager.sample_rate}"
        )

    def get_status(self) -> ModuleStatus:
        """Get current status including actual runtime device info."""
        status = super().get_status()
        is_piper = self._engine == "piper"
        actually_using_gpu = (
            is_piper
            and self._piper_manager is not None
            and self._piper_manager.is_alive
            and self._piper_manager.using_cuda
        )
        status.extra["device"] = "cuda" if actually_using_gpu else "cpu"
        status.extra["using_gpu"] = actually_using_gpu
        status.extra["engine"] = self._engine
        status.extra["voice_loaded"] = self._voice_loaded
        status.extra["subprocess_alive"] = self._piper_manager.is_alive if self._piper_manager else False
        return status

    def stop(self) -> None:
        """Cleanup TTS resources."""
        self._state = ModuleState.STOPPING
        if self._piper_manager:
            self._piper_manager.stop()
            self._piper_manager = None
        self._piper_voice = None
        self._state = ModuleState.IDLE

    def _ensure_piper_model(self, voice_name: str) -> tuple[str, str]:
        """Check if Piper ONNX model exists locally. Raises error if not found."""
        models_dir = str(Path(".").resolve() / "models" / "piper")
        Path(models_dir).mkdir(parents=True, exist_ok=True)

        model_path = str(Path(models_dir) / f"{voice_name}.onnx")
        config_path = str(Path(models_dir) / f"{voice_name}.onnx.json")

        if Path(model_path).exists() and Path(config_path).exists():
            return model_path, config_path

        # Model not found locally - list available voices
        available = [f.stem for f in Path(models_dir).iterdir() if f.suffix == ".onnx"]
        raise RuntimeError(
            f"Piper voice '{voice_name}' not found locally. "
            f"Available voices: {', '.join(sorted(available)) if available else 'none'}"
        )

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Synthesize text into speech.
        """
        text = data.translated_text if self._use_translated else data.transcript

        if not text:
            logger.debug(f"[TTS] Empty text for chunk {data.chunk_index}, setting dubbed_audio_path to None")
            data.dubbed_audio_path = None
            return data

        if isinstance(self._tts_dir, str):
            output_wav = os.path.join(self._tts_dir, f"tts_{data.chunk_index:06d}.wav")
        else:
            output_wav = str(self._tts_dir / f"tts_{data.chunk_index:06d}.wav")

        try:
            if self._engine == "edge-tts":
                self._run_edge_tts(text, output_wav)
            elif self._engine == "piper":
                self._run_piper_tts(text, output_wav)

            data.dubbed_audio_path = output_wav
            logger.debug(f"Generated {self._engine.upper()} for chunk {data.chunk_index}")

        except Exception as e:
            logger.error(f"[TTS] Generation error for chunk {data.chunk_index}: {e}")
            logger.error(traceback.format_exc())
            if self._engine == "edge-tts":
                self._write_silent_wav(output_wav)
                data.dubbed_audio_path = output_wav
            else:
                data.dubbed_audio_path = None

        return data

    def _write_silent_wav(self, output_wav: str, duration_sec: float = 0.1) -> None:
        """Write a tiny silent WAV fallback for offline Edge-TTS test environments."""
        Path(output_wav).parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 24000
        frames = int(sample_rate * duration_sec)
        with wave.open(output_wav, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * frames)

    def _format_speed(self, speed: float) -> str:
        """Convert speed multiplier to edge-tts rate format (+X% or -X%)."""
        delta = (speed - 1.0) * 100
        sign = "+" if delta >= 0 else ""
        return f"{sign}{delta:.0f}%"

    def _run_edge_tts(self, text: str, output_wav: str) -> None:
        """Run edge-tts to get highly natural audio."""
        import edge_tts

        temp_mp3 = output_wav.replace(".wav", ".mp3")
        rate = self._format_speed(self._speed)
        logger.debug(f"Generating TTS with rate={rate} (speed={self._speed})")

        async def _generate() -> None:
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
            creationflags=get_creation_flags(),
        )

        if Path(temp_mp3).exists():
            os.remove(temp_mp3)

    def _run_piper_tts(self, text: str, output_wav: str) -> None:
        """Run Piper TTS synthesis via persistent subprocess (GPU-enabled)."""
        if not self._voice_loaded:
            logger.info(f"[Piper] Lazy loading voice: {self._voice_model}")
            self._init_piper()
            self._voice_loaded = True

        if not self._piper_manager or not self._piper_manager.is_alive:
            logger.error("Piper subprocess not running")
            return

        try:
            # Debug: print speed type and value
            logger.debug(f"[TTS] speed type={type(self._speed)}, value={self._speed}")
            logger.debug(
                f"Synthesizing with Piper (CUDA={self._piper_manager.using_cuda}): "
                f"'{text[:50]}...' ({len(text)} chars), speed={self._speed}"
            )

            # Synthesize via subprocess (runs on GPU if available)
            wav_bytes = self._piper_manager.synthesize(
                text=text,
                speed=self._speed,
                timeout=30.0,
            )

            if wav_bytes is None:
                logger.error("Piper synthesis returned no data")
                return

            # Write WAV bytes to file
            with open(output_wav, "wb") as f:
                f.write(wav_bytes)

            if Path(output_wav).exists():
                file_size = Path(output_wav).stat().st_size
                logger.debug(f"Piper TTS generated: {output_wav} ({file_size} bytes)")
                if file_size < 44:
                    logger.warning(f"Generated WAV too small ({file_size} bytes), likely empty")
            else:
                logger.error(f"Piper TTS failed to generate: {output_wav}")

        except Exception as e:
            logger.error(f"Error during Piper TTS synthesis: {e}", exc_info=True)
