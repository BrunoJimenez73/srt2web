"""
Application Context - Factory for pipeline and dependencies.

Creates the processing pipeline with all modules, input sources,
and output sinks based on configuration.
"""

import inspect
import logging
from typing import Any

from core.config_manager import ConfigManager
from core.constants import LANGUAGE_NAMES
from core.ffmpeg_pool import FFmpegPool
from core.io_factory import InputFactory, OutputFactory, auto_discover
from core.unified_pipeline import PipelineMode, UnifiedPipeline
from server.ws_routes import log_broadcaster

logger = logging.getLogger("srt2web.app_context")


def _get_subtitle_language(config_manager: ConfigManager) -> tuple[str, str]:
    """Determine subtitle language from translator/subtitle_generator config."""
    translator_cfg = config_manager.get_section("modules.translator") or {}
    sub_gen_cfg = config_manager.get_section("modules.subtitle_generator") or {}
    use_translated = sub_gen_cfg.get("use_translated", True)
    lang = translator_cfg.get("target_lang", "en") if use_translated else translator_cfg.get("source_lang", "es")
    name = LANGUAGE_NAMES.get(lang, lang.capitalize())
    return lang, name


def _inject_subtitle_language(out_cfg: dict[str, Any], config_manager: ConfigManager) -> None:
    """Inject subtitle_language and subtitle_language_name into output config
    if not already set."""
    if "subtitle_language" in out_cfg and "subtitle_language_name" in out_cfg:
        return
    lang, name = _get_subtitle_language(config_manager)
    out_cfg.setdefault("subtitle_language", lang)
    out_cfg.setdefault("subtitle_language_name", name)


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
            # Propagate subtitle language from translator/subtitle_generator config
            _inject_subtitle_language(out_cfg, config_manager)
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
        # Propagate subtitle language from translator/subtitle_generator config
        _inject_subtitle_language(type_config, config_manager)
        # Merge with video_muxer module config so enabled/encoder settings propagate from init
        video_muxer_cfg = config_manager.get_section("modules.video_muxer")
        if video_muxer_cfg:
            type_config = {**type_config, **video_muxer_cfg}
        default_output = OutputFactory.create(output_type, type_config)
        default_output.name = f"{output_type}_1"
        default_output.set_output_dir(output_dir)
        composite_sink.add_output(default_output.name, default_output)

    # FFmpeg pool (F131: created here, injected into modules)
    ffmpeg_pool = FFmpegPool(max_size=4, idle_timeout=30.0)

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

    # Register modules (pool injected where modules accept it)
    _register_modules(pipeline, config_manager, output_dir, chunk_duration, ffmpeg_pool)

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
    ffmpeg_pool: FFmpegPool | None = None,
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
        if ffmpeg_pool is not None:
            sig = inspect.signature(module_class)
            if "pool" in sig.parameters:
                kwargs["pool"] = ffmpeg_pool

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
