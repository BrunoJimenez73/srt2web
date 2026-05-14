# SRT2Web

> Real-time SRT streaming processor with Web dashboard, CLI, and TUI.

[![CI](https://github.com/BrunoJimenez73/srt2web/actions/workflows/ci.yml/badge.svg)](https://github.com/BrunoJimenez73/srt2web/actions/workflows/ci.yml)

## Features

- **Input**: SRT, RTMP, File
- **Processing**: Audio extraction, Whisper transcription, Argos translation
- **Output**: HLS, RTMP, SRT, File, Recording, WebRTC
- **Interfaces**: Web dashboard (Astro + Tailwind), CLI + TUI (Textual)
- **GPU**: CUDA (NVIDIA), MPS (Apple Silicon), CPU fallback

## Quick Start

### Windows

```powershell
.\Install.bat
.\Start.bat
```

### macOS (Apple Silicon)

```bash
chmod +x install_Mac.sh
./install_Mac.sh
./start_Mac.sh
```

### Linux / Docker

```bash
docker compose up -d
```

### CLI / TUI

```bash
# After installation:
srt2web-tui status          # Pipeline status
srt2web-tui tui             # Interactive TUI
srt2web-tui logs -f         # Follow logs
srt2web-tui config          # View configuration
srt2web-tui --help          # All commands
```

## Documentation

See `docs/` for full documentation: deployment, architecture, compatibility, and troubleshooting.

## Requirements

- **Python**: 3.12+
- **FFmpeg**: 6.0+ (installed automatically on Mac via Homebrew)
- **Node.js**: 22+ (for frontend build)
- **OS**: Windows 10/11, macOS 12+ (Apple Silicon), Linux

## License

MIT
