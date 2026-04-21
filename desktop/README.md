# SRT2Web Desktop

Desktop application for SRT2Web - Real-time SRT Stream Processor with Subtitles and TTS.

## Features

- **Real-time processing**: Transcribe, translate, and generate subtitles from SRT/RTMP streams
- **Text-to-Speech**: Generate dubbed audio with TTS voices
- **HLS Output**: Watch translated streams in any browser
- **Cross-platform**: Windows, macOS, and Linux support

## Installation

### Windows
1. Download `SRT2Web-{version}-Setup.exe` from releases
2. Run the installer
3. Launch from Start Menu or Desktop shortcut

### macOS
1. Download `SRT2Web-{version}.dmg` from releases
2. Mount the disk image
3. Drag SRT2Web to Applications

### Linux
1. Download `SRT2Web-{version}.AppImage` from releases
2. Make executable: `chmod +x SRT2Web-{version}.AppImage`
3. Run: `./SRT2Web-{version}.AppImage`

## Development

### Prerequisites

- Node.js 20+
- Python 3.10+
- FFmpeg (for video processing)

### Setup

```bash
# Install Node dependencies
cd desktop
npm install

# Run in development mode
npm run dev
```

### Build

```bash
# Build for current platform
npm run build

# Build for all platforms
npm run build:all

# Build for Windows
npm run build:win
```

## Project Structure

```
desktop/
├── package.json          # Electron + electron-builder config
├── src/
│   ├── main.js       # Electron main process
│   ├── preload.js    # Context bridge (IPC)
│   └── python/
│       └── launcher.py  # Python backend launcher
├── build/
│   ├── icon.ico      # Windows icon
│   ├── icon.icns     # macOS icon
│   ├── icon.png      # Linux icon
│   └── installer.nsh # Custom NSIS script
└── resources/
    └── ffmpeg/      # Bundled FFmpeg (optional)
```

## Architecture

```
┌─────────────────────────────────────────┐
│           SRT2Web Desktop              │
├─────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐  │
│  │  Electron   │    │    Python   │  │
│  │  (Window)   │───▶│   Server   │  │
│  │             │    │            │  │
│  │ Dashboard   │    │ Pipeline   │  │
│  │ (Astro)    │    │ Processing │  │
│  └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────┘
```

## Auto-Update

Updates are downloaded automatically from GitHub Releases when available.

## License

MIT License - see LICENSE file for details.