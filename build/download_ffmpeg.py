#!/usr/bin/env python3
"""
Download FFmpeg binaries for SRT2Web packaging.

Usage:
    python download_ffmpeg.py windows
    python download_ffmpeg.py macos
    python download_ffmpeg.py linux
"""

import os
import sys
import zipfile
import tarfile
import urllib.request
import shutil
from pathlib import Path
from typing import Optional


FFMPEG_RELEASES = {
    "windows": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "extracted_name": "ffmpeg-master-latest-win64-gpl",
        "exe_name": "ffmpeg.exe",
    },
    "macos": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.tar.xz",
        "extracted_name": "ffmpeg-master-latest-macos64-gpl",
        "exe_name": "ffmpeg",
    },
    "linux": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
        "extracted_name": "ffmpeg-master-latest-linux64-gpl",
        "exe_name": "ffmpeg",
    },
}


def get_bin_dir() -> Path:
    """Get the bin directory path."""
    script_dir = Path(__file__).parent.parent
    bin_dir = script_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    return bin_dir


def download_file(url: str, dest: Path) -> bool:
    """Download a file from URL to destination."""
    print(f"Downloading {url}...")
    print(f"Destination: {dest}")

    try:

        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 // total_size)
                print(f"\r  Progress: {percent}%", end="", flush=True)

        urllib.request.urlretrieve(url, dest, reporthook)
        print()  # New line after progress
        return True
    except Exception as e:
        print(f"\nError downloading: {e}")
        return False


def extract_windows(zip_path: Path, dest_dir: Path) -> bool:
    """Extract FFmpeg from Windows zip."""
    print(f"Extracting {zip_path.name}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        return True
    except Exception as e:
        print(f"Error extracting: {e}")
        return False


def extract_unix(tar_path: Path, dest_dir: Path) -> bool:
    """Extract FFmpeg from Unix tar.xz."""
    print(f"Extracting {tar_path.name}...")
    try:
        with tarfile.open(tar_path, "r:xz") as tf:
            tf.extractall(dest_dir)
        return True
    except Exception as e:
        print(f"Error extracting: {e}")
        return False


def find_and_copy_ffmpeg(platform: str, extracted_dir: Path, bin_dir: Path) -> bool:
    """Find FFmpeg binary and copy to bin directory."""
    config = FFMPEG_RELEASES[platform]
    exe_name = config["exe_name"]
    extracted_name = config["extracted_name"]

    # Search patterns for FFmpeg
    search_patterns = [
        extracted_dir / extracted_name / "bin" / exe_name,
        extracted_dir / "bin" / exe_name,
    ]

    found = None
    for pattern in search_patterns:
        if pattern.exists():
            found = pattern
            break

    if not found:
        # Try recursive search
        for root, dirs, files in os.walk(extracted_dir):
            if exe_name in files:
                found = Path(root) / exe_name
                break

    if not found:
        print(f"Could not find {exe_name} in extracted files")
        return False

    print(f"Found FFmpeg at: {found}")

    # Copy to bin directory
    dest = bin_dir / exe_name
    shutil.copy2(found, dest)
    print(f"Copied to: {dest}")

    # Also copy ffprobe if exists
    probe_name = exe_name.replace("ffmpeg", "ffprobe")
    if (found.parent / probe_name).exists():
        shutil.copy2(found.parent / probe_name, bin_dir / probe_name)
        print(f"Copied ffprobe to: {bin_dir / probe_name}")

    return True


def download_ffmpeg(platform: str, force: bool = False) -> bool:
    """
    Download and extract FFmpeg for the specified platform.

    Args:
        platform: Target platform (windows, macos, linux)
        force: Force re-download even if files exist

    Returns:
        True if successful, False otherwise
    """
    if platform not in FFMPEG_RELEASES:
        print(f"Unknown platform: {platform}")
        print(f"Available: {list(FFMPEG_RELEASES.keys())}")
        return False

    config = FFMPEG_RELEASES[platform]
    bin_dir = get_bin_dir()
    exe_name = config["exe_name"]

    # Check if already downloaded
    if not force and (bin_dir / exe_name).exists():
        print(f"FFmpeg already exists at {bin_dir / exe_name}")
        response = input("Re-download? (y/N): ").strip().lower()
        if response != "y":
            print("Using existing FFmpeg.")
            return True

    # Create temp directory
    temp_dir = bin_dir / "temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        # Download
        url = config["url"]
        filename = url.split("/")[-1]
        download_path = temp_dir / filename

        if not download_file(url, download_path):
            return False

        # Extract
        if platform == "windows":
            if not extract_windows(download_path, temp_dir):
                return False
        else:
            if not extract_unix(download_path, temp_dir):
                return False

        # Find and copy FFmpeg
        if not find_and_copy_ffmpeg(platform, temp_dir, bin_dir):
            return False

        print("FFmpeg downloaded successfully!")
        return True

    finally:
        # Cleanup temp files
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: python download_ffmpeg.py <platform>")
        print(f"Available platforms: {list(FFMPEG_RELEASES.keys())}")
        sys.exit(1)

    platform = sys.argv[1].lower()
    force = "--force" in sys.argv or "-f" in sys.argv

    success = download_ffmpeg(platform, force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
