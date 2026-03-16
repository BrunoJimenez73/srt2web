# SRT2Web - Product Requirements Document

## Project Overview

SRT2Web is a modular pipeline that receives SRT streams and converts them to HLS for browser playback with AI-powered dubbing and subtitle translation.

## Tech Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **Processing**: FFmpeg, faster-whisper, Argos Translate
- **Output**: HLS (HTTP Live Streaming)
- **Testing**: pytest, FastAPI TestClient

## Core Features

### 1. SRT Stream Ingestion
- Receives SRT streams via FFmpeg
- Segments into 4-second chunks
- Outputs to `/output/chunks/` directory

### 2. Modular Processing Pipeline
Processing modules in order:
- **AudioExtractor**: Extracts audio from video
- **Transcriber**: Whisper-based transcription (faster-whisper)
- **Translator**: Argos Translate for offline translation
- **SubtitleGenerator**: Creates .vtt and .srt subtitles
- **TTSEngine**: Generates AI voice (Azure TTS)
- **AudioMixer**: Mixes original + dubbed audio with ducking
- **VideoMuxer**: Packages to HLS with hardware acceleration

### 3. HLS Output
- Segmented video output in `/output/hls/`
- Seamless playback using time offsets
- Hardware acceleration: NVENC, AMF, QSV

### 4. REST API
FastAPI server with endpoints:
- `GET /health` - Health check
- `GET /api/status` - Pipeline status
- `POST /api/start` - Start pipeline
- `POST /api/stop` - Stop pipeline
- `GET /api/config` - Get configuration
- `PUT /api/config` - Update configuration
- `GET /api/modules` - List modules
- `PUT /api/modules/{name}/toggle` - Toggle module
- `GET /api/srt-info` - SRT connection info

### 5. WebSocket Log Streaming
- `WS /ws/logs` - Real-time logs

## API Validation Rules

### Config Keys
- `port`: 1-65535
- `latency_ms`: >= 0
- `transcriber.model`: tiny, small, medium, large-v2, large-v3, large
- `transcriber.language`: auto, en, es, fr, de, it, pt, ja, zh, ko, ru
- `transcriber.device`: auto, cuda, cpu
- `srt.mode`: listener, caller
- `volume`: 0.0-2.0
- `speed`: 0.5-2.0

### Module Names
Valid: audio_extractor, transcriber, translator, subtitle_generator, tts_engine, audio_mixer, video_muxer

## Data Structures

### PipelineData
```python
{
    "chunk_index": int,
    "timestamp": float,
    "duration": float,
    "video_chunk_path": str,
    "audio_chunk_path": str,
    "transcript": str,
    "translated_text": str,
    "dubbed_audio_path": str,
    "subtitle_path": str
}
```

### Module Status
```python
{
    "name": str,
    "enabled": bool,
    "state": "idle|starting|running|stopping|error",
    "error": str
}
```

## Testing Strategy

### Unit Tests
- test_api_routes.py: 53 tests
- test_config_manager.py: 18 tests
- test_pipeline.py: 15 tests

### Test Approach
- Use FastAPI TestClient for API tests
- Mock external dependencies (SRT ingest, FFmpeg)
- Fixtures in tests/conftest.py

## Known Limitations
- SRT port 9000 must be available
- FFmpeg required for processing
- GPU recommended but optional
