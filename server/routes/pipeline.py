"""
Pipeline control routes for SRT2Web API.
"""

import asyncio
import contextlib
import glob
import logging
import os
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

from core.cache import cached, invalidate_cache
from server.validators import SeekPosition

logger = logging.getLogger("srt2web.api.pipeline")

router = APIRouter(tags=["pipeline"])


def _check_port_available(port: int) -> bool:
    """Check if a TCP port is available for listening."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", port))
            return result != 0  # port is free if connection refused
    except Exception:
        # Non-critical: port check is best-effort, assume available on failure
        return True  # assume available if check fails


def _ctx(request: Request) -> dict[str, Any]:
    return cast(dict[str, Any], request.app.state.ctx)


@router.get("/status")
@cached("status", ttl_seconds=1)
async def get_status(request: Request) -> dict[str, Any]:
    """Get full pipeline status including all modules and input/output."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    input_source = ctx.get("input_source")
    config = ctx["config"]

    status = cast(dict[str, Any], pipeline.get_status())

    if input_source:
        status["input_receiving"] = input_source.is_receiving()
        status["input_info"] = input_source.get_connection_info()

    # Add network info
    from core.network_utils import get_network_info

    srt_port = config.get("input.srt.listen_port", 9000)
    server_port = config.get("server.port", 9999)
    latency_ms = config.get("input.srt.latency_ms", 1000)
    srt_mode = config.get("input.srt.mode", "listener")
    caller_address = config.get("input.srt.caller_address", "")

    network = get_network_info(srt_port=srt_port, server_port=server_port, latency_ms=latency_ms)
    network["srt_mode"] = srt_mode
    network["caller_address"] = caller_address
    status["network"] = network

    # Add subtitle sync information
    subtitle_sync_config = config.get_section("subtitle_sync")
    if subtitle_sync_config.get("enable_drift_detection", False):
        if hasattr(pipeline, "subtitle_sync_monitor") and pipeline.subtitle_sync_monitor:
            monitor = pipeline.subtitle_sync_monitor
            status["sync"] = {
                "drift_ms": round(monitor.get_drift_ms(), 1),
                "state": monitor.get_state(),
                "correction_active": monitor.correction_active,
                "threshold_ms": subtitle_sync_config.get("sync_correction_threshold", 500),
            }
        else:
            status["sync"] = {
                "drift_ms": 0,
                "state": "in_sync",
                "correction_active": False,
                "threshold_ms": subtitle_sync_config.get("sync_correction_threshold", 500),
            }
    else:
        status["sync"] = {
            "drift_ms": 0,
            "state": "in_sync",
            "correction_active": False,
            "threshold_ms": subtitle_sync_config.get("sync_correction_threshold", 500),
        }

    return status


@router.post("/start")
async def start_pipeline(request: Request) -> dict[str, Any]:
    """Start the processing pipeline."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    input_source = ctx.get("input_source")
    log_broadcast = ctx.get("log_broadcast")
    config = ctx["config"]

    # Check if pipeline is already running (handle both string and enum)
    pipeline_state = getattr(pipeline, "state", "idle")
    if pipeline_state in ("running", "RUNNING") or (
        hasattr(pipeline_state, "value") and pipeline_state.value == "running"
    ):
        raise HTTPException(400, "Pipeline is already running")

    # If pipeline is in error state, reset to idle before starting again
    if pipeline_state in ("error", "ERROR"):
        try:
            pipeline.reset_error_state()
            logger.info("Pipeline state reset from error to idle")
        except Exception as e:
            logger.warning(f"Could not reset pipeline state: {e}")

    # Validar puertos antes de arrancar
    input_type = config.get("input.type", "srt") if config else "srt"
    if input_type == "srt":
        srt_port = config.get("input.srt.listen_port", 9000)
        if not _check_port_available(srt_port):
            raise HTTPException(
                400,
                f"El puerto SRT {srt_port} ya está en uso. Elige otro puerto o cierra la aplicación que lo está usando.",
            )
    elif input_type == "rtmp":
        rtmp_port = config.get("input.rtmp.listen_port", 1935)
        if not _check_port_available(rtmp_port):
            raise HTTPException(
                400,
                f"El puerto RTMP {rtmp_port} ya está en uso. Elige otro puerto o cierra la aplicación que lo está usando.",
            )
    logger.info(f"Starting pipeline with input type: {input_type}")

    if input_type == "rtmp" and input_source:
        rtmp_config = config.get("input.rtmp", {}) if config else {}
        logger.info(f"RTMP config: {rtmp_config}")
        # Configure RTMP input with listen port from config
        if hasattr(input_source, "configure"):
            rtmp_port = rtmp_config.get("listen_port", 1935)
            app_name = rtmp_config.get("app", "live")
            stream_key = rtmp_config.get("stream_key", "stream")
            # URL without listen param - it's set via -rtmp_listen option in FFmpeg
            listen_url = f"rtmp://127.0.0.1:{rtmp_port}/{app_name}/{stream_key}"
            new_config = {**rtmp_config, "url": listen_url}
            input_source.configure(new_config)
            logger.info(f"RTMP input configured in listen mode: {listen_url}")

    # File input setup
    if input_type == "file" and input_source:
        file_config = config.get("input.file", {}) if config else {}
        logger.info(f"File config: {file_config}")
        if hasattr(input_source, "configure"):
            input_source.configure(file_config)
            logger.info(f"File input configured with path: {file_config.get('path', '')}")

    def on_log(level: str, message: str) -> None:
        if log_broadcast:
            log_broadcast(level, message)

    def on_state(state: str) -> None:
        if log_broadcast:
            log_broadcast("info", f"Pipeline state changed: {state}")

    try:
        pipeline.start(
            on_log=on_log,
            on_state_change=on_state,
        )
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        raise HTTPException(500, f"Failed to start pipeline: {e}") from e

    input_info = {}
    if input_source:
        input_info = input_source.get_connection_info()

    invalidate_cache("status")
    return {"status": "started", "input": input_info}


@router.post("/stop")
async def stop_pipeline(request: Request) -> dict[str, Any]:
    """Stop the processing pipeline and clean up temporary files."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    output_dir = ctx.get("output_dir", "./output")

    try:
        await pipeline.stop()
    except Exception as e:
        logger.error(f"Error stopping pipeline: {e}")
        pass

    # Clean up temporary files
    # Safety: resolve output_dir and ensure it's within project root
    _output_path = Path(output_dir).resolve()
    _project_root = Path(__file__).parent.parent.parent.resolve()
    if not str(_output_path).startswith(str(_project_root)):
        logger.warning(
            f"Output dir '{output_dir}' resolves outside project root, " "skipping cleanup to avoid accidental deletion"
        )
        invalidate_cache("status")
        return {"status": "stopped", "warning": "output_dir outside project root"}

    cleanup_dirs = [
        os.path.join(output_dir, "chunks"),
        os.path.join(output_dir, "temp_audio"),
        os.path.join(output_dir, "temp_mix"),
        os.path.join(output_dir, "temp_tts"),
    ]

    for cleanup_dir in cleanup_dirs:
        if os.path.exists(cleanup_dir):
            try:
                import shutil

                shutil.rmtree(cleanup_dir)
                os.makedirs(cleanup_dir, exist_ok=True)
                logger.info(f"Cleaned up: {cleanup_dir}")
            except Exception as e:
                logger.warning(f"Could not clean {cleanup_dir}: {e}")

    # Also clean old HLS files
    hls_dir = os.path.join(output_dir, "hls")
    if os.path.exists(hls_dir):
        # Remove segment files
        for seg_file in glob.glob(os.path.join(hls_dir, "seg_*.ts")):
            with contextlib.suppress(OSError):
                os.remove(seg_file)
        # Remove chunk SRT files
        for srt_file in glob.glob(os.path.join(hls_dir, "chunk_*.srt")):
            with contextlib.suppress(OSError):
                os.remove(srt_file)
        # Remove playlist files but recreate them empty
        for m3u8_file in ["stream.m3u8", "master.m3u8"]:
            m3u8_path = os.path.join(hls_dir, m3u8_file)
            try:
                if os.path.exists(m3u8_path):
                    os.remove(m3u8_path)
            except OSError:
                pass
        # Keep subs.vtt but clear old entries
        subs_path = os.path.join(hls_dir, "subs.vtt")
        if os.path.exists(subs_path):
            try:
                with open(subs_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
            except OSError:
                pass

    invalidate_cache("status")
    return {"status": "stopped"}


@router.post("/restart")
async def restart_pipeline(request: Request) -> dict[str, Any]:
    """Restart the pipeline to apply module configuration changes."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    config = ctx["config"]

    try:
        await pipeline.stop()
    except Exception as e:
        logger.error(f"Error stopping pipeline: {e}")

    # Small delay to ensure clean shutdown
    await asyncio.sleep(0.5)

    # Reconfigure all modules
    pipeline.reconfigure(config)

    # Start pipeline again
    try:
        pipeline.start(
            on_log=lambda level, msg: None,
            on_state_change=lambda state: None,
        )
    except Exception as e:
        logger.error(f"Failed to restart pipeline: {e}")
        raise HTTPException(500, f"Failed to restart pipeline: {e}") from e

    return {"status": "restarted"}


# ── Input/Output Info ───────────────────────────


@router.get("/input-info")
async def input_info(request: Request) -> dict[str, Any]:
    """Get input source connection information."""
    ctx = _ctx(request)
    input_source = ctx.get("input_source")

    if not input_source:
        raise HTTPException(404, "No input source configured")

    return cast(dict[str, Any], input_source.get_connection_info())


# ── File Input Playback Controls ────────────────


@router.post("/input/control/play")
async def input_play(request: Request) -> dict[str, Any]:
    """Resume file playback (for file input type)."""
    ctx = _ctx(request)
    input_source = ctx.get("input_source")

    if not input_source:
        raise HTTPException(400, "No input source configured")

    logger.info(f"[API] input/control/play called - input_source type: {type(input_source).__name__}")

    if hasattr(input_source, "play"):
        input_source.play()
        logger.info("[API] input_source.play() executed successfully")
        return {"status": "playing", "message": "Playback resumed"}
    else:
        raise HTTPException(400, "Input source does not support play control")


@router.post("/input/control/pause")
async def input_pause(request: Request) -> dict[str, Any]:
    """Pause file playback (for file input type)."""
    ctx = _ctx(request)
    input_source = ctx.get("input_source")

    if not input_source:
        raise HTTPException(400, "No input source configured")

    logger.info(f"[API] input/control/pause called - input_source type: {type(input_source).__name__}")

    if hasattr(input_source, "pause"):
        input_source.pause()
        logger.info("[API] input_source.pause() executed successfully")
        return {"status": "paused", "message": "Playback paused"}
    else:
        raise HTTPException(400, "Input source does not support pause control")


@router.post("/input/control/seek")
async def input_seek(request: Request, body: SeekPosition) -> dict[str, Any]:
    """Seek to a specific position in the file (for file input type)."""
    ctx = _ctx(request)
    input_source = ctx.get("input_source")

    if not input_source:
        raise HTTPException(400, "No input source configured")

    if hasattr(input_source, "seek"):
        input_source.seek(body.position)
        return {
            "status": "seeked",
            "position": body.position,
            "message": f"Seeked to {body.position}s",
        }
    else:
        raise HTTPException(400, "Input source does not support seek control")
