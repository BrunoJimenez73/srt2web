# SRT2Web

Real-time SRT streaming processor with Web dashboard. Translate subtitles on-the-fly and stream to HLS.

## Requirements

- **Python**: 3.12+ (3.14 not supported due to pydantic v1 compatibility)
- **FFmpeg**: Must be installed and in PATH
- **Node.js**: 18+ (for frontend build)
- **CUDA**: Optional, for GPU acceleration (requires CUDA Toolkit 12.x)

## Quick Installation

### Windows

```bash
# Clone repository
git clone https://github.com/BrunoJimenez73/srt2web.git
cd srt2web

# Create virtual environment (Python 3.12)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Build frontend
npm run build:local

# Run server
.\Start.bat
```

### macOS / Linux

```bash
# Clone repository
git clone https://github.com/BrunoJimenez73/srt2web.git
cd srt2web

# Create virtual environment (Python 3.12)
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Build frontend
npm run build:local

# Run server
python main.py
```

## Quick Commands

```bash
# Backend tests
python -m pytest tests/unit/ -v

# Frontend tests
cd frontend && npm test

# Lint & type-check (Python)
ruff check core/ modules/ server/
mypy core/ server/ --config-file=pyproject.toml

# Lint & type-check (Frontend)
cd frontend && npx tsc --noEmit

# Build frontend
cd frontend && npm run build:local

# Quality check (all-in-one)
just quality   # or use: make quality
```

## Usage

- **Dashboard**: `http://localhost:9999/`
- **API**: `http://localhost:9999/api`
- **HLS Stream**: `http://localhost:9999/hls/stream.m3u8`
- **Player**: `http://localhost:9999/player`

## OBS Configuration

1. Open OBS Studio
2. Settings → Output → Recording (tab)
3. Type: Custom Output (FFmpeg)
4. FFmpeg Output Type: Output to URL
5. URL: `srt://127.0.0.1:9000`
6. Container Format: `mpegts`
7. Video Encoder: `libx264` (or `h264_nvenc` for GPU)
8. Keyframe Interval: 10 seconds (important!)

## Documentation

- **Architecture**: [docs/architecture.md](docs/architecture.md)
- **Deployment Guide**: [docs/deployment.md](docs/deployment.md)
- **Compatibility Matrix**: [docs/compatibility.md](docs/compatibility.md)
- **Contributing**: [docs/contributing.md](docs/contributing.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## Project Structure

```
srt2web/
├── core/              # Core pipeline and configuration
├── modules/          # Pipeline modules (transcriber, translator, TTS, etc.)
├── server/           # FastAPI server and API routes
├── frontend/         # Astro + TypeScript + Tailwind frontend
├── tests/            # Unit, integration, and benchmark tests
├── docs/             # MkDocs documentation
└── desktop/          # Electron desktop app
```

## Development

See [TODOs.md](TODOs.md) for current development tasks and priorities.

## License

MIT License - see LICENSE file for details.
