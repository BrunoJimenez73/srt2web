"""
Shared FFmpeg subprocess utilities for input modules.

Extracts duplicated GPU detection, hwaccel args, status reporting,
and chunk cleanup logic from srt_input, rtmp_input, and file_input.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.subprocess_utils import get_creation_flags

logger = logging.getLogger("srt2web.ffmpeg_process")


def detect_gpu(ffmpeg_path: str | None, log_prefix: str = "Input") -> dict[str, bool]:
    """Detect GPU support via ffprobe and return capability dict.

    Returns dict with keys: nvenc, qsv, amf, vaapi, videotoolbox.
    """
    from core.ffmpeg_utils import check_gpu_support

    gpu_info = check_gpu_support(ffmpeg_path or "")
    logger.info(f"{log_prefix} GPU support: {gpu_info}")
    return gpu_info


def resolve_hwaccel(gpu_info: dict[str, bool], log_prefix: str = "Input") -> tuple[bool, str]:
    """Resolve hwaccel enabled flag and device string from GPU info.

    Returns:
        Tuple of (hwaccel_enabled, hwaccel_device)
    """
    if gpu_info.get("nvenc"):
        logger.info(f"{log_prefix}: Using NVDEC hardware acceleration")
        return True, "0"
    if gpu_info.get("qsv"):
        logger.info(f"{log_prefix}: Using QSV hardware acceleration")
        return True, "0"
    if gpu_info.get("vaapi"):
        logger.info(f"{log_prefix}: Using VAAPI hardware acceleration")
        return True, "0"
    logger.info(f"{log_prefix}: No GPU acceleration available, using CPU")
    return False, "0"


def build_hwaccel_args(
    hwaccel_enabled: bool,
    gpu_info: dict[str, bool],
    hwaccel_device: str = "0",
) -> list[str]:
    """Build FFmpeg hwaccel command-line arguments.

    Returns list of args to extend into the FFmpeg command.
    """
    if not hwaccel_enabled:
        return []

    if gpu_info.get("nvenc"):
        return ["-hwaccel", "cuda", "-hwaccel_device", hwaccel_device]
    if gpu_info.get("qsv"):
        return ["-hwaccel", "qsv", "-hwaccel_device", hwaccel_device]
    if gpu_info.get("vaapi"):
        return ["-hwaccel", "vaapi"]
    return []


def get_input_status_extra(
    gpu_info: dict[str, bool],
    hwaccel_enabled: bool,
) -> dict[str, Any]:
    """Build the extra dict for ModuleStatus in input modules.

    Returns dict with keys: using_gpu, gpu_info, encoder_label, hwaccel.
    """
    if gpu_info.get("nvenc"):
        encoder_label = "NVDEC"
    elif gpu_info.get("qsv"):
        encoder_label = "QSV"
    elif gpu_info.get("vaapi"):
        encoder_label = "VAAPI"
    else:
        encoder_label = "CPU"

    return {
        "using_gpu": hwaccel_enabled,
        "gpu_info": gpu_info,
        "encoder_label": encoder_label,
        "hwaccel": hwaccel_enabled,
    }


def cleanup_old_chunks(chunks_dir: str) -> int:
    """Remove old chunk_*.ts files from chunks directory.

    Returns number of files removed.
    """
    removed = 0
    for f in Path(chunks_dir).glob("chunk_*.ts"):
        with contextlib.suppress(OSError):
            f.unlink()
            removed += 1
    return removed


def kill_ffmpeg_process(proc: subprocess.Popen[Any], timeout: float = 3.0) -> None:
    """Kill an FFmpeg subprocess gracefully.

    Uses taskkill on Windows (kills process tree), terminate elsewhere.
    Waits up to timeout seconds, then force-kills if needed.
    """
    if proc.poll() is not None:
        return

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=timeout,
                creationflags=get_creation_flags(),
            )
        else:
            proc.terminate()
        proc.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        with contextlib.suppress(OSError):
            proc.kill()
