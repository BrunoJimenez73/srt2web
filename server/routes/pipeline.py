"""
Pipeline control routes for SRT2Web API.
"""

import asyncio
import glob
import logging
import os

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger("srt2web.api.pipeline")

router = APIRouter(tags=["pipeline"])


def _ctx(request: Request) -> dict:
    return request.app.state.ctx


@router.get("/status")
async def get_status(request: Request):
    """Get full pipeline status including all modules and input/output."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    input_source = ctx.get("input_source")
    config = ctx["config"]

    status = pipeline.get_status()

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

    return status


@router.post("/start")
async def start_pipeline(request: Request):
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

    # RTMP input setup - no external server needed, FFmpeg listens for connections
    input_type = config.get("input.type", "srt") if config else "srt"
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

    def on_log(level, message):
        if log_broadcast:
            log_broadcast(level, message)

    def on_state(state):
        if log_broadcast:
            log_broadcast("info", f"Pipeline state changed: {state}")

    try:
        pipeline.start(
            on_log=on_log,
            on_state_change=on_state,
        )
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        raise HTTPException(500, f"Failed to start pipeline: {e}")

    input_info = {}
    if input_source:
        input_info = input_source.get_connection_info()

    return {"status": "started", "input": input_info}


@router.post("/stop")
async def stop_pipeline(request: Request):
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
        for f in glob.glob(os.path.join(hls_dir, "seg_*.ts")):
            try:
                os.remove(f)
            except OSError:
                pass
        # Remove chunk SRT files
        for f in glob.glob(os.path.join(hls_dir, "chunk_*.srt")):
            try:
                os.remove(f)
            except OSError:
                pass
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

    return {"status": "stopped"}


@router.post("/restart")
async def restart_pipeline(request: Request):
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
        raise HTTPException(500, f"Failed to restart pipeline: {e}")

    return {"status": "restarted"}
