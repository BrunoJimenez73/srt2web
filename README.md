# SRT2Web

[![CI](https://github.com/BrunoJimenez73/srt2web/actions/workflows/ci.yml/badge.svg)](https://github.com/BrunoJimenez73/srt2web/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-590%2B-brightgreen)](https://github.com/BrunoJimenez73/srt2web)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Real-time SRT streaming processor with Web dashboard for live transcription, translation, TTS, and HLS streaming.

## Quick Start

```bash
# Install dependencies
pip install .

# Run server
python main.py
```

## Requirements

- Python 3.12
- FFmpeg
- (Optional) NVIDIA GPU with CUDA for accelerated processing

## Features

- **Input**: SRT, RTMP, or File input
- **Transcription**: Faster-Whisper (GPU accelerated)
- **Translation**: Argos Translate
- **TTS**: Piper or Edge TTS
- **Outputs**: HLS, WebRTC, Recording

## Documentation

See `docs/` for detailed documentation.

## Development

```bash
# Install dev dependencies
pip install ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy core/ modules/ server/

# Linting
ruff check .
```