"""Helpers for UnifiedPipeline status and reconfiguration."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("srt2web.pipeline.helpers")


def get_output_module_status(
    is_running: bool,
    output_sink: Any,
    module_map: dict[str, Any],
    chunks_processed: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return (output_status, video_muxer_status) tuple."""
    state = "running" if is_running else "idle"
    sink = output_sink if output_sink else module_map.get("video_muxer")
    extra: dict[str, Any] = {}
    processed_chunks = chunks_processed
    last_process_time_ms = 0
    muxer_status: dict[str, Any] | None = None

    if sink:
        try:
            status = sink.get_status()
            status_dict = status.to_dict() if getattr(status, "to_dict", None) else status
            if isinstance(status_dict, dict):
                processed_chunks = status_dict.get("processed_chunks", processed_chunks)
                last_process_time_ms = status_dict.get("last_process_time_ms", last_process_time_ms)
                extra = status_dict.get("extra", {})

                outputs = extra.get("outputs", {})
                muxer_source = None
                for _out_name, out_data in outputs.items():
                    out_extra = out_data.get("extra", {})
                    if out_extra.get("using_gpu") is not None or out_extra.get("encoder_mode") is not None:
                        muxer_source = out_data
                        break
                if muxer_source is None and outputs:
                    first_name = next(iter(outputs.keys()))
                    muxer_source = outputs[first_name]

                if muxer_source:
                    muxer_extra = muxer_source.get("extra", {})
                    muxer_status = {
                        "name": "video_muxer",
                        "state": muxer_source.get("state", state),
                        "enabled": muxer_source.get("enabled", True),
                        "error_message": None,
                        "processed_chunks": muxer_source.get("processed_chunks", processed_chunks),
                        "last_process_time_ms": muxer_source.get("last_process_time_ms", last_process_time_ms),
                        "extra": muxer_extra,
                        "circuit_state": "closed",
                        "memory_mb": None,
                    }
        except Exception as e:
            logger.warning("Failed to get video muxer status: %s", e)

    output_status = {
        "name": "output",
        "state": state,
        "enabled": True,
        "error_message": None,
        "processed_chunks": processed_chunks,
        "last_process_time_ms": last_process_time_ms,
        "extra": extra,
        "circuit_state": "closed",
        "memory_mb": None,
    }
    return output_status, muxer_status


def reconfigure_pipeline(
    pipeline: Any,
    config_manager: Any,
    log_fn: Any,
) -> None:
    """Reconfigure pipeline modules, output sinks, and input source."""
    try:
        new_chunk_duration = config_manager.get("pipeline.chunk_duration_sec", 10)
        pipeline._chunk_duration = new_chunk_duration
        log_fn("info", f"Reconfigured pipeline chunk_duration: {new_chunk_duration}s")
    except Exception as e:
        log_fn("warning", f"Could not update chunk_duration: {e}")

    for module in pipeline._modules:
        try:
            mod_config = config_manager.get_module_config(module.name)
            module.configure(mod_config)
            log_fn("info", f"Reconfigured module: {module.name}")
        except Exception as e:
            log_fn("error", f"Failed to reconfigure {module.name}: {e}")

    if pipeline._output_sink:
        try:
            configure_outputs = getattr(pipeline._output_sink, "configure_outputs", None)
            if configure_outputs:
                configure_outputs(config_manager)
            else:
                configure_method = getattr(pipeline._output_sink, "configure", None)
                if configure_method:
                    output_config = config_manager.get_section("output")
                    configure_method(output_config)
            log_fn("info", "Reconfigured output sinks")
        except Exception as e:
            log_fn("warning", f"Could not reconfigure output sinks: {e}")

    if pipeline._input_source:
        try:
            input_type = config_manager.get("input.type", "srt")
            input_config = config_manager.get_section("input").get(input_type, {})
            input_config["chunk_duration_sec"] = pipeline._chunk_duration
            configure_method = getattr(pipeline._input_source, "configure", None)
            if configure_method:
                configure_method(input_config)
            log_fn("info", f"Reconfigured input source: {input_type}")
        except Exception as e:
            log_fn("warning", f"Could not reconfigure input source: {e}")
