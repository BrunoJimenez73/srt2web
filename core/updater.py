"""
Auto-updater for SRT2Web.

Checks GitHub for new releases and offers to download and install them.
"""

import os
import sys
import json
import logging
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import urllib.request
import urllib.error

logger = logging.getLogger("srt2web.updater")

RELEASES_URL = "https://api.github.com/repos/BrunoJimenez73/srt2web/releases/latest"
ASSETS_URL = "https://api.github.com/repos/BrunoJimenez73/srt2web/releases"

VERSION_FILE = "version.txt"
CURRENT_VERSION = "0.4.0"


class UpdaterError(Exception):
    """Custom exception for updater errors."""

    pass


def get_current_version() -> str:
    """Get the current version of SRT2Web."""
    version_file = Path(__file__).parent.parent / VERSION_FILE
    if version_file.exists():
        return version_file.read_text().strip()
    return CURRENT_VERSION


def check_for_updates() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Check GitHub for new releases.

    Returns:
        Tuple of (latest_version, release_data) or (None, None) if no update available
    """
    try:
        logger.info("Checking for updates...")

        req = urllib.request.Request(
            RELEASES_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "SRT2Web-Updater",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

            latest_version = data.get("tag_name", "").lstrip("v")
            current_version = get_current_version()

            logger.info(f"Current version: {current_version}")
            logger.info(f"Latest version: {latest_version}")

            if is_newer_version(latest_version, current_version):
                return latest_version, data

            return None, None

    except urllib.error.URLError as e:
        logger.warning(f"Could not connect to GitHub: {e}")
        return None, None
    except json.JSONDecodeError as e:
        logger.error(f"Could not parse GitHub response: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        return None, None


def is_newer_version(new_version: str, current_version: str) -> bool:
    """
    Compare version strings.

    Returns True if new_version > current_version
    """

    def parse_version(v: str) -> Tuple[int, ...]:
        try:
            return tuple(int(x) for x in v.split(".") if x.isdigit())
        except (ValueError, AttributeError):
            return (0,)

    return parse_version(new_version) > parse_version(current_version)


def get_release_assets(release_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get list of assets from release data."""
    return release_data.get("assets", [])


def find_windows_installer(assets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find Windows installer in release assets."""
    for asset in assets:
        name = asset.get("name", "").lower()
        if "windows" in name or ".exe" in name or ".msi" in name:
            if "setup" in name or "installer" in name or ".exe" in name:
                return asset
    return None


def download_asset(asset: Dict[str, Any], dest_dir: Path) -> Optional[Path]:
    """
    Download a release asset.

    Args:
        asset: Asset dict with name and browser_download_url
        dest_dir: Destination directory

    Returns:
        Path to downloaded file or None on error
    """
    name = asset.get("name", "update")
    url = asset.get("browser_download_url")

    if not url:
        logger.error("Asset has no download URL")
        return None

    dest_path = dest_dir / name

    try:
        logger.info(f"Downloading {name}...")

        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/octet-stream",
                "User-Agent": "SRT2Web-Updater",
            },
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Progress: {percent:.1f}%", end="", flush=True)

        print()  # New line after progress
        logger.info(f"Downloaded to: {dest_path}")
        return dest_path

    except Exception as e:
        logger.error(f"Error downloading asset: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return None


def download_update(version: str) -> Optional[Path]:
    """
    Download the latest release for current platform.

    Args:
        version: Target version to download

    Returns:
        Path to downloaded update file or None on error
    """
    import platform

    system = platform.system().lower()

    # Determine asset pattern for this platform
    patterns = {
        "windows": ["windows", "setup", "installer", ".exe"],
        "darwin": ["macos", "mac", "dmg"],
        "linux": ["linux", "appimage", ".tar"],
    }

    try:
        # Get releases list
        req = urllib.request.Request(
            f"{ASSETS_URL}/tags/v{version}",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "SRT2Web-Updater",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            assets = data.get("assets", [])

        # Find matching asset
        platform_patterns = patterns.get(system, patterns["windows"])
        for asset in assets:
            name = asset.get("name", "").lower()
            if all(p in name for p in platform_patterns):
                with tempfile.TemporaryDirectory() as temp_dir:
                    return download_asset(asset, Path(temp_dir))

        logger.warning(f"No update found for platform: {system}")
        return None

    except Exception as e:
        logger.error(f"Error downloading update: {e}")
        return None


def apply_update(update_path: Path) -> bool:
    """
    Apply a downloaded update.

    Args:
        update_path: Path to the update file

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Applying update...")

        # Get current executable directory
        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path(__file__).parent.parent

        if update_path.suffix == ".zip":
            with zipfile.ZipFile(update_path, "r") as zf:
                extract_dir = app_dir / "_update_temp"
                extract_dir.mkdir(exist_ok=True)
                zf.extractall(extract_dir)

                # Copy files
                for item in extract_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, app_dir / item.name)
                    elif item.is_dir():
                        dest = app_dir / item.name
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)

                # Cleanup
                shutil.rmtree(extract_dir)

        elif update_path.suffix == ".exe":
            # Run installer and restart
            logger.info("Running installer...")
            subprocess.run([str(update_path)], check=True)

        logger.info("Update applied successfully!")
        return True

    except Exception as e:
        logger.error(f"Error applying update: {e}")
        return False


def run_update_check() -> Optional[str]:
    """
    Run update check and return message.

    Returns:
        Message to display or None
    """
    version, release = check_for_updates()

    if version is None:
        return None

    return f"Version {version} is available! You are running {get_current_version()}."


def main():
    """CLI interface for updater."""
    import argparse

    parser = argparse.ArgumentParser(description="SRT2Web Updater")
    parser.add_argument("--check", action="store_true", help="Check for updates")
    parser.add_argument(
        "--download", action="store_true", help="Download latest update"
    )
    parser.add_argument("--apply", metavar="FILE", help="Apply update from file")

    args = parser.parse_args()

    if args.check:
        msg = run_update_check()
        if msg:
            print(msg)
        else:
            print("You are running the latest version.")

    elif args.download:
        version, _ = check_for_updates()
        if version:
            path = download_update(version)
            if path:
                print(f"Downloaded to: {path}")
            else:
                print("Download failed.")
        else:
            print("No update available.")

    elif args.apply:
        apply_update(Path(args.apply))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
