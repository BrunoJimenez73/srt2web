"""
Application Context - Factory for pipeline and dependencies.

Creates the processing pipeline with all modules, input sources,
and output sinks based on configuration.
"""

import logging
from typing import Any

from core.config_manager import ConfigManager
from core.io_factory import InputFactory, OutputFactory, auto_discover
from core.unified_pipeline import PipelineMode, UnifiedPipeline
from server.ws_routes import log_broadcaster

logger = logging.getLogger("srt2web.app_context")


def create_app_context(
    config_manager: ConfigManager,
    output_dir: str,
) -> dict[str, Any]:
    """
    Create application context with pipeline and dependencies.

    Returns dict with:
        - pipeline: UnifiedPipeline instance
        - config: ConfigManager instance
        - config_manager: ConfigManager instance (alias)
        - log_broadcast: Log broadcast function
        - input_source: Input source instance
    """
    auto_discover()
    chunk_duration = config_manager.get("pipeline.chunk_duration_sec", 15)

    # Input source
    input_config = config_manager.get_section("input")
    input_type = input_config.get("type", "srt")
    type_config = input_config.get(input_type, {})
    type_config["chunk_duration_sec"] = chunk_duration

    input_source = InputFactory.create(input_type, type_config)
    input_source.set_output_dir(output_dir)

    # Composite output sink
    from modules.outputs.composite_output import CompositeOutput

    composite_sink = CompositeOutput({})
    composite_sink.set_output_dir(output_dir)

    output_config = config_manager.get_section("output")
    named_outputs = output_config.get("outputs", [])

    if named_outputs:
        for entry in named_outputs:
            out_name = entry.get("name", "")
            out_type = entry.get("type", "")
            out_cfg = entry.get("config", {}) or {}
            if not out_name or not out_type:
                logger.warning(f"Skipping invalid output entry: {entry}")
                continue
            try:
                # Merge with video_muxer module config so enabled/encoder settings propagate from init
                video_muxer_cfg = config_manager.get_section("modules.video_muxer")
                if video_muxer_cfg:
                    out_cfg = {**out_cfg, **video_muxer_cfg}
                output = OutputFactory.create(out_type, out_cfg)
                output.name = out_name
                output.set_output_dir(output_dir)
                composite_sink.add_output(out_name, output)
                logger.info(f"Created output '{out_name}' ({out_type})")
            except Exception as e:
                logger.warning(f"Failed to create output '{out_name}': {e}")
    else:
        output_type = output_config.get("type", "web")
        type_config = output_config.get(output_type, {})
        # Merge with video_muxer module config so enabled/encoder settings propagate from init
        video_muxer_cfg = config_manager.get_section("modules.video_muxer")
        if video_muxer_cfg:
            type_config = {**type_config, **video_muxer_cfg}
        default_output = OutputFactory.create(output_type, type_config)
        default_output.name = f"{output_type}_1"
        default_output.set_output_dir(output_dir)
        composite_sink.add_output(default_output.name, default_output)

    # Pipeline
    pipeline = UnifiedPipeline(
        mode=PipelineMode.THREAD_PARALLEL,
        max_concurrent_chunks=2,
        buffer_size=20,
        retry_attempts=2,
        retry_delay=1.0,
    )
    pipeline.set_input_source(input_source)
    pipeline.set_output_sink(composite_sink)

    # Register modules
    _register_modules(pipeline, config_manager, output_dir, chunk_duration)

    return {
        "pipeline": pipeline,
        "config": config_manager,
        "config_manager": config_manager,
        "log_broadcast": log_broadcaster.broadcast,
        "input_source": input_source,
    }


def _register_modules(
    pipeline: UnifiedPipeline,
    config_manager: ConfigManager,
    output_dir: str,
    chunk_duration: int,
) -> None:
    """Register all processing modules with the pipeline."""
    from core.subtitle_sync_monitor import SubtitleSyncMonitor
    from modules.audio_extractor import AudioExtractor
    from modules.audio_mixer import AudioMixer
    from modules.subtitle_generator import SubtitleGenerator
    from modules.transcriber import Transcriber
    from modules.translator import Translator
    from modules.tts_engine import TTSEngine

    modules_config = {
        "audio_extractor": (AudioExtractor, True),
        "transcriber": (Transcriber, False),
        "translator": (Translator, False),
        "subtitle_generator": (SubtitleGenerator, True),
        "tts_engine": (TTSEngine, True),
        "audio_mixer": (AudioMixer, True),
    }

    for module_name, (module_class, needs_output_dir) in modules_config.items():
        mod_config = config_manager.get_module_config(module_name)
        if module_name == "subtitle_generator":
            mod_config["chunk_duration"] = chunk_duration

        kwargs: dict[str, Any] = {"config": mod_config}
        if needs_output_dir:
            kwargs["output_dir"] = output_dir

        module = module_class(**kwargs)
        pipeline.register_module(module)

    # Register subtitle sync monitor as a special module (doesn't process data, just monitors)
    sync_config = config_manager.get_section("subtitle_sync")
    sync_monitor = SubtitleSyncMonitor(
        threshold_ms=sync_config.get("sync_correction_threshold", 500), smoothing_factor=0.7
    )
    # Store reference in pipeline for access
    pipeline.subtitle_sync_monitor = sync_monitor  # type: ignore[attr-defined]

    # F108 — wire the drift monitor INTO the subtitle generator so the previously
    # dead `enable_drift_detection` flag actually applies a correction factor
    # on every chunk. This is the only place the two objects can meet.
    subtitle_module = pipeline.get_module("subtitle_generator")
    if subtitle_module is not None and hasattr(subtitle_module, "set_drift_monitor"):
        subtitle_module.set_drift_monitor(sync_monitor)
