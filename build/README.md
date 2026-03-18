# SRT2Web Build Scripts

This directory contains scripts and configurations for building SRT2Web releases.

## Directory Structure

```
build/
├── common/                  # Common build utilities
├── windows/                 # Windows-specific build files
│   ├── SRT2Web.spec        # PyInstaller spec file
│   ├── SRT2Web.nsi        # NSIS installer script
│   └── build.bat          # Windows build script
├── macos/                   # macOS-specific build files
├── linux/                   # Linux-specific build files
├── download_ffmpeg.py      # FFmpeg download script
└── create_release.py        # Master release script
```

## Quick Start

### 1. Download FFmpeg

```bash
python build/download_ffmpeg.py windows
```

### 2. Build Windows Executable

```bash
build\windows\build.bat
```

### 3. Create Release Package

```bash
python build/create_release.py --version 0.4.0
```

## Requirements

- Python 3.9+
- PyInstaller: `pip install pyinstaller`
- NSIS (for Windows installer): https://nsis.sourceforge.io/

## Build Outputs

After building, outputs go to `dist/`:

```
dist/
├── SRT2Web/                    # Raw PyInstaller output
├── SRT2Web_v0.4.0.exe         # NSIS installer
└── SRT2Web_v0.4.0_Portable.zip # Portable ZIP
```

## Auto-Updater

The built executable includes an auto-updater that checks GitHub releases for new versions.

To enable:
1. Create a GitHub Personal Access Token
2. Set as `GITHUB_TOKEN` environment variable
3. Use `--github` flag when creating release

## Troubleshooting

### FFmpeg Download Fails
- Check internet connection
- Try manually downloading from: https://github.com/BtbN/FFmpeg-Builds

### PyInstaller Build Fails
- Ensure all dependencies are installed: `pip install -r requirements-full.txt`
- Try with clean build: `pyinstaller --clean build/windows/SRT2Web.spec`

### NSIS Installer Fails
- Install NSIS 3.x: https://nsis.sourceforge.io/Download
- Check that build output exists in `dist/SRT2Web/`
