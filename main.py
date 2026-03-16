"""
SRT2Web - Modular SRT Stream Processor

Entry point: starts the FastAPI server, initializes the pipeline,
and opens the browser to the dashboard.
"""

import os
import sys
import asyncio
import atexit
import logging
import webbrowser
import threading
import signal
from pathlib import Path

import uvicorn

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import ConfigManager
from core.pipeline import Pipeline
from core.ffmpeg_utils import find_ffmpeg, ensure_ffmpeg
from core.io_factory import InputFactory, OutputFactory, auto_discover
from modules.audio_extractor import AudioExtractor
from modules.transcriber import Transcriber
from modules.translator import Translator
from modules.subtitle_generator import SubtitleGenerator
from modules.tts_engine import TTSEngine
from modules.audio_mixer import AudioMixer
from server.app import create_app
from server.ws_routes import log_broadcaster

# Global references for cleanup
_app_context = None


def _cleanup_orphan_processes():
    """Cleanup any orphan FFmpeg processes on unexpected shutdown."""
    import subprocess
    import platform

    logger = logging.getLogger("srt2web.cleanup")
    logger.info("Cleaning up orphan processes...")

    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/IM", "ffmpeg.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
        else:
            subprocess.run(["pkill", "-f", "ffmpeg"], capture_output=True)
    except Exception as e:
        logger.debug(f"Cleanup note: {e}")


def _shutdown():
    """Graceful shutdown handler."""
    global _app_context
    logger = logging.getLogger("srt2web.main")

    if _app_context:
        try:
            pipeline = _app_context.get("pipeline")

            if pipeline:
                pipeline.stop()

            logger.info("Pipeline shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    _cleanup_orphan_processes()


def setup_logging():
    """Configure logging with both console and broadcaster output."""

    class BroadcastHandler(logging.Handler):
        """Custom handler that sends logs to WebSocket subscribers."""

        def emit(self, record):
            try:
                msg = self.format(record)
                log_broadcaster.broadcast(record.levelname.lower(), msg)
            except Exception:
                pass

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    # Broadcast handler (sends to WebSocket clients)
    broadcast = BroadcastHandler()
    broadcast.setLevel(logging.INFO)
    broadcast.setFormatter(
        logging.Formatter("%(levelname)-5s │ %(name)s │ %(message)s")
    )

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(broadcast)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def build_pipeline(config: ConfigManager, output_dir: str):
    """
    Build the processing pipeline with modular input/output.

    Returns (pipeline, input_source).
    """
    # Auto-discover available inputs and outputs
    auto_discover()

    # Get input configuration
    input_config = config.get_section("input")
    input_type = input_config.get("type", "srt")
    type_config = input_config.get(input_type, {})
    type_config["chunk_duration_sec"] = config.get("pipeline.chunk_duration_sec", 15)

    # Create input source
    logger = logging.getLogger("srt2web.main")
    logger.info(f"Creating input source: {input_type}")
    input_source = InputFactory.create(input_type, type_config)
    input_source.set_output_dir(output_dir)

    # Get output configuration
    output_config = config.get_section("output")
    output_type = output_config.get("type", "web")
    type_config = output_config.get(output_type, {})

    # Create output sink
    logger.info(f"Creating output sink: {output_type}")
    output_sink = OutputFactory.create(output_type, type_config)
    output_sink.set_output_dir(output_dir)

    # Create pipeline with input/output
    pipeline = Pipeline(input_source, output_sink)

    # Register processing modules (Execution Order Matters!)

    # 1. Extract audio from the video chunk
    audio_extractor_config = config.get_module_config("audio_extractor")
    audio_extractor = AudioExtractor(
        config=audio_extractor_config, output_dir=output_dir
    )
    pipeline.register_module(audio_extractor)

    # 2. Transcribe the audio
    transcriber_config = config.get_module_config("transcriber")
    transcriber = Transcriber(config=transcriber_config)
    pipeline.register_module(transcriber)

    # 3. Translate the transcript
    translator_config = config.get_module_config("translator")
    translator = Translator(config=translator_config)
    pipeline.register_module(translator)

    # 4. Generate subtitles
    subs_config = config.get_module_config("subtitle_generator")
    subtitle_generator = SubtitleGenerator(config=subs_config, output_dir=output_dir)
    pipeline.register_module(subtitle_generator)

    # 5. Generate Text-to-Speech audio
    tts_config = config.get_module_config("tts_engine")
    tts_engine = TTSEngine(config=tts_config, output_dir=output_dir)
    pipeline.register_module(tts_engine)

    # 6. Mix original audio with TTS audio (ducking)
    mixer_config = config.get_module_config("audio_mixer")
    audio_mixer = AudioMixer(config=mixer_config, output_dir=output_dir)
    pipeline.register_module(audio_mixer)

    # Note: Output is now handled by the OutputSink, not a module

    return pipeline, input_source


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger("srt2web.main")

    print()
    print("  +====================================+")
    print("  |      SRT2Web - Stream Processor   |")
    print("  |         v0.4.0 - Modular          |")
    print("  +====================================+")
    print()

    # Load configuration
    config_path = str(PROJECT_ROOT / "config.yaml")
    config = ConfigManager(config_path)
    logger.info("Configuration loaded")

    # Ensure output directory exists
    output_dir = config.get("output_dir.directory", "./output")
    if not os.path.isabs(output_dir):
        output_dir = str(PROJECT_ROOT / output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Check FFmpeg
    logger.info("Checking FFmpeg availability...")
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        logger.info(f"✓ FFmpeg found: {ffmpeg_path}")
    else:
        logger.warning("FFmpeg not found. Will attempt download on first use.")

    # Build pipeline
    pipeline, input_source = build_pipeline(config, output_dir)

    # Create shared context
    global _app_context
    app_context = {
        "config": config,
        "pipeline": pipeline,
        "input_source": input_source,
        "log_broadcast": log_broadcaster.broadcast,
    }
    _app_context = app_context

    # Register atexit handler for cleanup
    atexit.register(_shutdown)

    # Create FastAPI app
    app = create_app(app_context)

    # Server configuration
    host = config.get("server.host", "0.0.0.0")
    port = config.get("server.port", 9999)

    # Open browser after a short delay
    def open_browser():
        import time

        time.sleep(1.5)
        url = f"http://localhost:{port}"
        logger.info(f"Opening browser at {url}")
        webbrowser.open(url)

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Register signal handlers for graceful shutdown
    def handle_exit(signum, frame):
        logger.info("Shutdown signal received. Cleaning up...")
        _shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Get connection info for logging
    input_info = input_source.get_connection_info()
    input_url = input_info.get("url", f"port {input_info.get('port', 'N/A')}")

    # Start server
    logger.info(f"Dashboard: http://localhost:{port}")
    logger.info(f"Input:    {input_info.get('type', 'unknown').upper()} ({input_url})")
    logger.info(f"Stream:   http://localhost:{port}/hls/stream.m3u8")
    print()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
