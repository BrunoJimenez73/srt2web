"""
FFmpeg utilities for SRT2Web.

Handles FFmpeg binary detection, download, and common operations
like SRT ingestion and HLS packaging.
"""

import os
import sys
import shutil
import logging
import platform
import subprocess
import urllib.request
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("srt2web.ffmpeg")

# FFmpeg download URLs for pre-built binaries
FFMPEG_URLS = {
    "Windows": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "Darwin": "https://evermeet.cx/ffmpeg/getrelease/zip",
}


def get_project_bin_dir() -> Path:
    """Get the bin/ directory in the project root."""
    return Path(__file__).parent.parent / "bin"


def find_ffmpeg() -> Optional[str]:
    """
    Find the FFmpeg binary. Checks in order:
    1. Project bin/ directory
    2. System PATH
    
    Returns the full path to ffmpeg, or None if not found.
    """
    # Check project bin/ directory first
    bin_dir = get_project_bin_dir()
    if platform.system() == "Windows":
        local_ffmpeg = bin_dir / "ffmpeg.exe"
    else:
        local_ffmpeg = bin_dir / "ffmpeg"

    if local_ffmpeg.exists():
        logger.info(f"Found FFmpeg in project bin: {local_ffmpeg}")
        return str(local_ffmpeg)

    # Also check inside extracted folder structure
    for candidate in bin_dir.rglob("ffmpeg*"):
        if candidate.is_file() and candidate.stem == "ffmpeg":
            logger.info(f"Found FFmpeg in project bin: {candidate}")
            return str(candidate)

    # Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        logger.info(f"Found FFmpeg in PATH: {system_ffmpeg}")
        return system_ffmpeg

    logger.warning("FFmpeg not found")
    return None


def find_ffprobe() -> Optional[str]:
    """Find the FFprobe binary (same search logic as FFmpeg)."""
    bin_dir = get_project_bin_dir()
    exe = "ffprobe.exe" if platform.system() == "Windows" else "ffprobe"

    local = bin_dir / exe
    if local.exists():
        return str(local)

    for candidate in bin_dir.rglob("ffprobe*"):
        if candidate.is_file() and candidate.stem == "ffprobe":
            return str(candidate)

    system = shutil.which("ffprobe")
    if system:
        return system

    return None


def get_ffmpeg_version(ffmpeg_path: str) -> Optional[str]:
    """Get the version string of an FFmpeg binary."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        first_line = result.stdout.split("\n")[0]
        return first_line
    except Exception as e:
        logger.error(f"Failed to get FFmpeg version: {e}")
        return None


def check_gpu_support(ffmpeg_path: str) -> dict:
    """Check for hardware acceleration support in FFmpeg (encoders)."""
    results = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}
    try:
        result = subprocess.run(
            [ffmpeg_path, "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.lower()
        results["nvenc"] = "h264_nvenc" in output or "hevc_nvenc" in output
        results["qsv"] = "h264_qsv" in output or "hevc_qsv" in output
        results["amf"] = "h264_amf" in output or "hevc_amf" in output
        results["vaapi"] = "h264_vaapi" in output or "hevc_vaapi" in output
    except Exception:
        pass
    return results


def get_video_duration(file_path: str, ffprobe_path: Optional[str] = None) -> float:
    """Get the exact duration of a video/audio file using ffprobe."""
    if ffprobe_path is None:
        from core.ffmpeg_utils import find_ffprobe
        ffprobe_path = find_ffprobe()
    
    if not ffprobe_path:
        return 0.0
        
    try:
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def check_srt_support(ffmpeg_path: str) -> bool:
    """Check if FFmpeg was compiled with SRT protocol support."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-protocols"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "srt" in result.stdout.lower()
    except Exception:
        return False


def download_ffmpeg(progress_callback=None) -> Optional[str]:
    """
    Download pre-built FFmpeg binaries for the current platform.
    
    Args:
        progress_callback: Optional callable(downloaded_bytes, total_bytes)
    
    Returns:
        Path to the ffmpeg binary, or None on failure.
    """
    system = platform.system()
    if system not in FFMPEG_URLS:
        logger.error(
            f"No pre-built FFmpeg available for {system}. "
            "Please install FFmpeg manually."
        )
        return None

    url = FFMPEG_URLS[system]
    bin_dir = get_project_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Downloading FFmpeg from {url}...")

        # Download with progress
        archive_path = bin_dir / ("ffmpeg_download.zip" if system == "Windows" else "ffmpeg_download.zip")

        def _reporthook(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                downloaded = block_num * block_size
                progress_callback(downloaded, total_size)

        urllib.request.urlretrieve(url, str(archive_path), _reporthook)

        logger.info("Extracting FFmpeg...")

        # Extract
        if str(archive_path).endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(bin_dir)
        elif str(archive_path).endswith((".tar.gz", ".tar.xz")):
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(bin_dir)

        # Clean up archive
        archive_path.unlink(missing_ok=True)

        # Find the extracted binary
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            # Make executable on Unix
            if system != "Windows":
                os.chmod(ffmpeg_path, 0o755)
                ffprobe = find_ffprobe()
                if ffprobe:
                    os.chmod(ffprobe, 0o755)
            logger.info(f"FFmpeg downloaded and ready at: {ffmpeg_path}")
            return ffmpeg_path
        else:
            logger.error("FFmpeg binary not found after extraction")
            return None

    except Exception as e:
        logger.error(f"Failed to download FFmpeg: {e}")
        return None


def ensure_ffmpeg(progress_callback=None) -> str:
    """
    Ensure FFmpeg is available. Downloads if necessary.
    
    Returns:
        Path to the ffmpeg binary.
    
    Raises:
        RuntimeError: If FFmpeg cannot be found or downloaded.
    """
    path = find_ffmpeg()
    if path:
        return path

    logger.info("FFmpeg not found. Attempting to download...")
    path = download_ffmpeg(progress_callback)
    if path:
        return path

    raise RuntimeError(
        "FFmpeg is required but could not be found or downloaded. "
        "Please install FFmpeg manually: https://ffmpeg.org/download.html"
    )


def run_ffmpeg(
    args: List[str],
    ffmpeg_path: Optional[str] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run an FFmpeg command with the given arguments.
    
    Args:
        args: Arguments to pass to FFmpeg (without the ffmpeg binary itself)
        ffmpeg_path: Path to FFmpeg binary (auto-detected if None)
        timeout: Command timeout in seconds
        capture_output: Whether to capture stdout/stderr
    
    Returns:
        CompletedProcess instance
    """
    if ffmpeg_path is None:
        ffmpeg_path = ensure_ffmpeg()

    cmd = [ffmpeg_path] + args
    logger.debug(f"Running: {' '.join(cmd)}")

    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def start_ffmpeg_process(
    args: List[str],
    ffmpeg_path: Optional[str] = None,
) -> subprocess.Popen:
    """
    Start a long-running FFmpeg process (e.g., SRT listener).
    
    Args:
        args: Arguments to pass to FFmpeg
        ffmpeg_path: Path to FFmpeg binary (auto-detected if None)
    
    Returns:
        Popen instance for the running process
    """
    if ffmpeg_path is None:
        ffmpeg_path = ensure_ffmpeg()

    cmd = [ffmpeg_path] + args
    logger.info(f"Starting FFmpeg process: {' '.join(cmd)}")

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
