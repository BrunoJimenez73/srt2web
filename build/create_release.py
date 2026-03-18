#!/usr/bin/env python3
"""
SRT2Web Release Script

Creates release packages for all platforms and uploads to GitHub.

Usage:
    python create_release.py                    # Interactive mode
    python create_release.py --version 0.4.0   # Specific version
    python create_release.py --download-only   # Only download dependencies
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

# Try to import github3 for GitHub releases
try:
    import github3

    HAS_GITHUB = True
except ImportError:
    HAS_GITHUB = False
    print("Warning: github3.py not installed. GitHub releases disabled.")
    print("Install with: pip install github3.py")


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def log(msg: str, color: str = Colors.BLUE):
    """Print a colored message."""
    print(f"{color}{msg}{Colors.ENDC}")


def log_step(step: str, msg: str):
    """Print a step header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}  {step}: {msg}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 50}{Colors.ENDC}\n")


def run_command(
    cmd: List[str], cwd: Optional[Path] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    log(f"Running: {' '.join(cmd)}", Colors.YELLOW)
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        if check:
            raise
        return e


def download_ffmpeg(platform: str) -> bool:
    """Download FFmpeg for the specified platform."""
    script_dir = Path(__file__).parent
    download_script = script_dir / "download_ffmpeg.py"

    log_step("Download FFmpeg", f"Platform: {platform}")

    result = run_command(
        [sys.executable, str(download_script), platform, "--force"], check=False
    )

    return result.returncode == 0


def build_windows() -> bool:
    """Build Windows executable."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    build_script = script_dir / "windows" / "build.bat"

    log_step("Build Windows", "Using PyInstaller")

    result = run_command([str(build_script)], cwd=project_root, check=False)

    if result.returncode == 0:
        log("Windows build successful!", Colors.GREEN)
        return True
    else:
        log("Windows build failed!", Colors.RED)
        return False


def create_windows_installer(version: str) -> Optional[Path]:
    """Create Windows NSIS installer."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    nsi_script = script_dir / "windows" / "SRT2Web.nsi"
    dist_dir = project_root / "dist"
    installer_dir = dist_dir / "installers"

    log_step("Create Installer", "Windows NSIS")

    # Create installers directory
    installer_dir.mkdir(parents=True, exist_ok=True)

    # Check if NSIS is available
    nsis_path = shutil.which("makensis") or shutil.which("makensis.exe")

    if not nsis_path:
        log("NSIS not found. Skipping installer creation.", Colors.YELLOW)
        log("Install NSIS from: https://nsis.sourceforge.io/", Colors.YELLOW)
        return None

    # Update version in NSIS script
    nsi_content = nsi_script.read_text()
    nsi_content = nsi_content.replace(
        '!define PRODUCT_VERSION "0.4.0"', f'!define PRODUCT_VERSION "{version}"'
    )
    nsi_script.write_text(nsi_content)

    # Build installer
    result = run_command([nsis_path, str(nsi_script)], cwd=project_root, check=False)

    if result.returncode == 0:
        installer_path = dist_dir / f"SRT2Web_Setup_v{version}.exe"
        if installer_path.exists():
            log(f"Installer created: {installer_path}", Colors.GREEN)
            return installer_path

    log("Installer creation failed!", Colors.RED)
    return None


def create_portable_archive(version: str) -> Optional[Path]:
    """Create portable ZIP archive."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    dist_dir = project_root / "dist"

    log_step("Create Archive", "Portable ZIP")

    portable_dir = dist_dir / f"SRT2Web_v{version}_Windows_Portable"

    # Copy build output to portable directory
    build_dir = dist_dir / "SRT2Web"

    if not build_dir.exists():
        log("Build directory not found!", Colors.RED)
        return None

    if portable_dir.exists():
        shutil.rmtree(portable_dir)

    shutil.copytree(build_dir, portable_dir)

    # Create ZIP
    zip_path = dist_dir / f"SRT2Web_v{version}_Windows_Portable.zip"

    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(portable_dir), "zip", portable_dir)

    # Cleanup portable directory
    shutil.rmtree(portable_dir)

    log(f"Archive created: {zip_path}", Colors.GREEN)
    return zip_path


def create_github_release(
    version: str, files: List[Path], token: Optional[str] = None
) -> bool:
    """Create GitHub release."""
    if not HAS_GITHUB:
        log("GitHub module not available. Install: pip install github3.py", Colors.RED)
        return False

    if not token:
        token = os.environ.get("GITHUB_TOKEN")

    if not token:
        log(
            "GitHub token not found. Set GITHUB_TOKEN environment variable.",
            Colors.YELLOW,
        )
        return False

    log_step("GitHub Release", f"Version {version}")

    try:
        gh = github3.login(token=token)
        repo = gh.repository("BrunoJimenez73", "srt2web")

        # Create release
        release = repo.create_release(
            tag_name=f"v{version}",
            name=f"SRT2Web v{version}",
            message=f"Release v{version}\n\nSee CHANGELOG.md for details.",
            draft=True,
            prerelease=False,
        )

        # Upload assets
        for file_path in files:
            if file_path.exists():
                with open(file_path, "rb") as f:
                    release.upload_asset(
                        name=file_path.name,
                        asset=f,
                        content_type="application/octet-stream",
                    )
                log(f"Uploaded: {file_path.name}", Colors.GREEN)

        log(f"Release created: {release.html_url}", Colors.GREEN)
        return True

    except Exception as e:
        log(f"GitHub release failed: {e}", Colors.RED)
        return False


def main():
    parser = argparse.ArgumentParser(description="SRT2Web Release Script")
    parser.add_argument("--version", help="Release version (e.g., 0.4.0)")
    parser.add_argument(
        "--download-only", action="store_true", help="Only download dependencies"
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip build step")
    parser.add_argument(
        "--skip-installer", action="store_true", help="Skip installer creation"
    )
    parser.add_argument("--github", action="store_true", help="Create GitHub release")
    parser.add_argument("--token", help="GitHub token")

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Get version
    version = args.version
    if not version:
        version_file = project_root / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
        else:
            version = input("Enter version (e.g., 0.4.0): ").strip()

    log_step("SRT2Web Release", f"Version {version}")

    # Download FFmpeg
    download_ffmpeg("windows")

    if args.download_only:
        log("Download complete.", Colors.GREEN)
        return

    if not args.skip_build:
        # Build
        if not build_windows():
            log("Build failed!", Colors.RED)
            sys.exit(1)
    else:
        log("Skipping build step.", Colors.YELLOW)

    # Create release artifacts
    artifacts = []

    # Portable ZIP
    zip_path = create_portable_archive(version)
    if zip_path:
        artifacts.append(zip_path)

    # Installer
    if not args.skip_installer:
        installer_path = create_windows_installer(version)
        if installer_path:
            artifacts.append(installer_path)

    # GitHub release
    if args.github:
        create_github_release(version, artifacts, args.token)

    # Summary
    log_step("Release Complete", f"Version {version}")

    print("\nArtifacts created:")
    for artifact in artifacts:
        print(f"  - {artifact}")

    print("\nNext steps:")
    print("1. Test the executable")
    print("2. Review the artifacts")
    print("3. Create GitHub release with: python create_release.py --github")
    print("4. Publish the release on GitHub")


if __name__ == "__main__":
    main()
