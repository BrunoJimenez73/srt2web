"""
SRT2Web - Modular SRT Stream Processor

Entry point: starts the FastAPI server, initializes the pipeline,
and opens the browser to the dashboard.
"""

import logging
import os
import signal
import sys
import threading
import webbrowser
from types import FrameType
from typing import Any

import uvicorn

from core import SERVER_HOST, SERVER_PORT_DEFAULT, get_config_path, get_project_root
from core.config_manager import ConfigManager
from core.cuda_paths import setup_cuda_environment
from core.io_factory import InputFactory, OutputFactory, auto_discover
from core.unified_pipeline import PipelineMode, UnifiedPipeline
from modules.audio_extractor import AudioExtractor
from modules.audio_mixer import AudioMixer
from modules.subtitle_generator import SubtitleGenerator
from modules.transcriber import Transcriber
from modules.translator import Translator
from modules.tts_engine import TTSEngine
from server.app import create_app

# Setup CUDA paths - must be called before any GPU-related imports
setup_cuda_environment()

# Define PROJECT_ROOT after import
PROJECT_ROOT = get_project_root()

# No global state - use function parameters


def _cleanup_orphan_processes() -> None:
    """Cleanup any orphan FFmpeg processes on unexpected shutdown."""
    from core.ffmpeg_utils import cleanup_ffmpeg_processes
    from core.security import cleanup_temporary_files

    logger = logging.getLogger("srt2web.cleanup")
    logger.info("Cleaning up orphan processes and temporary files...")

    try:
        # Clean up FFmpeg processes
        cleanup_ffmpeg_processes()

        # Clean up temporary files
        output_dir = "./output"
        cleanup_temporary_files(output_dir)

        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")


def _shutdown(app_context: dict) -> None:
    """Graceful shutdown handler."""
    logger = logging.getLogger("srt2web.main")

    if app_context:
        try:
            pipeline = app_context.get("pipeline")

            if pipeline:
                pipeline.stop()

            logger.info("Pipeline shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    _cleanup_orphan_processes()


def setup_logging() -> None:
    """Configure logging - delegates to core.logging_setup."""
    from core.logging_setup import setup_logging as _setup
    from server.ws_routes import log_broadcaster

    _setup(log_broadcaster=log_broadcaster)
    logging.getLogger("srt2web.main").info("Logging initialized")


def build_pipeline(config: ConfigManager, output_dir: str) -> tuple[UnifiedPipeline, Any]:
    """
    Build the processing pipeline with modular input/output.

    Returns (pipeline, input_source).
    """
    # Auto-discover available inputs and outputs
    auto_discover()

    # Get chunk_duration_sec from pipeline (single source of truth)
    chunk_duration = config.get("pipeline.chunk_duration_sec")

    # Get input configuration
    input_config = config.get_section("input")
    input_type = input_config.get("type", "srt")
    type_config = input_config.get(input_type, {})
    type_config["chunk_duration_sec"] = chunk_duration

    # Create input source
    logger = logging.getLogger("srt2web.main")
    logger.info(f"Creating input source: {input_type} (chunk_duration={chunk_duration})")
    input_source = InputFactory.create(input_type, type_config)
    input_source.set_output_dir(output_dir)

    # Get output configuration
    output_config = config.get_section("output")
    output_type = output_config.get("type", "web")
    type_config = output_config.get(output_type, {})

    # Siempre crear un CompositeOutput como sink principal.
    # Esto permite agregar/quitar salidas en caliente desde la API
    # sin reiniciar el pipeline.
    from modules.outputs.composite_output import CompositeOutput

    composite_sink = CompositeOutput({})
    composite_sink.set_output_dir(output_dir)

    # La lista `outputs` es la fuente de verdad.
    # Si existe, crearla toda. Si está vacía, crear el legacy default (backward compat).
    named_outputs = output_config.get("outputs", [])

    if named_outputs:
        # Usar la lista completa — nombres tal como están en el YAML
        for entry in named_outputs:
            out_name = entry.get("name", "")
            out_type = entry.get("type", "")
            out_cfg = entry.get("config", {}) or {}
            if not out_name or not out_type:
                logger.warning(f"Skipping invalid output entry: {entry}")
                continue
            try:
                output = OutputFactory.create(out_type, out_cfg)
                output.name = out_name
                output.set_output_dir(output_dir)
                composite_sink.add_output(out_name, output)
                logger.info(f"Created output '{out_name}' ({out_type})")
            except Exception as e:
                logger.warning(f"Failed to create output '{out_name}': {e}")
    else:
        # Fallback legacy: un solo output por defecto
        logger.info(f"Creating default output sink: {output_type}")
        default_output = OutputFactory.create(output_type, type_config)
        default_output.name = f"{output_type}_1"
        default_output.set_output_dir(output_dir)
        composite_sink.add_output(default_output.name, default_output)

    # Create unified pipeline with parallel processing (THREAD_PARALLEL mode)
    pipeline = UnifiedPipeline(
        mode=PipelineMode.THREAD_PARALLEL,
        max_concurrent_chunks=2,
        buffer_size=2,
        retry_attempts=2,
        retry_delay=1.0,
    )
    pipeline.set_input_source(input_source)
    pipeline.set_output_sink(composite_sink)

    # Register processing modules (Execution Order Matters!)

    # 1. Extract audio from the video chunk
    audio_extractor_config = config.get_module_config("audio_extractor")
    audio_extractor = AudioExtractor(config=audio_extractor_config, output_dir=output_dir)
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
    subs_config["chunk_duration"] = chunk_duration  # Override module's chunk_duration with pipeline value
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

    # Log actual configuration values
    buffer_size = config.get("pipeline.buffer_size", 5)
    num_workers = config.get("pipeline.max_concurrent_chunks", 3)
    logger.info(f"Pipeline created: buffer_size={buffer_size}, num_workers={num_workers}")
    logger.info(f"Parallel processing enabled - expected {num_workers-1}x throughput improvement")

    return pipeline, input_source


def main() -> None:
    """Main entry point."""
    logger = logging.getLogger("srt2web.main")

    # Load config for server settings
    config_manager = ConfigManager(get_config_path())
    config = config_manager._config

    host = config.get("server", {}).get("host", SERVER_HOST)
    port = config.get("server", {}).get("port", SERVER_PORT_DEFAULT)
    ssl_config = config.get("server", {}).get("ssl", {})
    ssl_enabled = ssl_config.get("enabled", False)

    # Initialize components
    input_type = config.get("pipeline", {}).get("input_type", "srt")
    input_source = InputFactory.create(input_type, config)
    modules = [
        AudioExtractor(),
        Transcriber(),
        Translator(),
        TTSEngine(),
        SubtitleGenerator(),
        AudioMixer(),
    ]
    output_type = config.get("pipeline", {}).get("output_type", "web")
    output_sink = OutputFactory.create(output_type, config)

    pipeline = UnifiedPipeline(mode=PipelineMode.SEQUENTIAL)
    pipeline.set_input_source(input_source)
    pipeline.set_output_sink(output_sink)
    for module in modules:
        pipeline.register_module(module)

    # Get log_broadcaster for app_context
    from server.ws_routes import log_broadcaster

    app_context = {
        "pipeline": pipeline,
        "config": config_manager,
        "config_manager": config_manager,
        "log_broadcast": log_broadcaster.broadcast,
    }

    # Setup browser opener
    def open_browser() -> None:
        url = f"http{'s' if ssl_enabled else ''}://{host}:{port}"
        logger.info(f"Opening browser: {url}")
        webbrowser.open(url)

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Register signal handlers for graceful shutdown
    def handle_exit(signum: int, frame: FrameType | None) -> None:
        logger.info("Shutdown signal received. Cleaning up...")
        _shutdown(app_context)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Get connection info for logging
    input_info = input_source.get_connection_info()
    input_url = input_info.get("url", f"port {input_info.get('port', 'N/A')}")

    # Start server
    protocol = "https" if ssl_enabled else "http"
    logger.info(f"Dashboard: {protocol}://{host}:{port}")
    logger.info(f"Input:    {input_info.get('type', 'unknown').upper()} ({input_url})")
    logger.info(f"Stream:   {protocol}://{host}:{port}/hls/stream.m3u8")
    print()

    # Create the app once
    app = create_app(app_context)

    # SSL context if enabled
    ssl_context = None
    if ssl_enabled:
        cert_file = ssl_config.get("cert_file", "certs/cert.pem")
        key_file = ssl_config.get("key_file", "certs/key.pem")

        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            logger.warning(f"SSL cert/key not found: {cert_file}, {key_file}")
            logger.warning("Run: python scripts/generate_ssl_certs.py")
            logger.warning("Falling back to HTTP")
        else:
            import ssl

            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(cert_file, key_file)
            logger.info(f"SSL enabled: {cert_file}")
        uvicorn_config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            ssl_certfile=cert_file,
            ssl_keyfile=key_file,
        )
    else:
        uvicorn_config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
        )
    server = uvicorn.Server(uvicorn_config)
    server.run()


if __name__ == "__main__":
    main()
