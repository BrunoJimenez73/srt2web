# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-03-16

### Added
- **Windows Batch Scripts**: New scripts for easy server management
  - `Arrancar_Servidor.bat` - Start the server
  - `Detener_Servidor.bat` - Stop the server
  - `Reiniciar_Servidor.bat` - Restart the server
  - `Diagnosticar_Puertos.bat` - Diagnose port issues
- **Hot-Reload API**: Toggle modules on/off via API
  - `PUT /api/modules/{name}/toggle` - Enable/disable modules
  - `POST /api/restart` - Restart pipeline
- **GPU Detection Logging**: Logs which encoder is being used (CPU vs GPU)

### Fixed
- **Windows Encoding Issues**: Removed Unicode characters that caused errors in Windows batch files
- **Player Stability**: Changed from master.m3u8 to stream.m3u8 for more stable playback
- **Missing CSS Class**: Added `.hidden` class that was missing
- **CORS Configuration**: Added port 9999 to allowed origins

### Changed
- **HLS Configuration**: Increased segment duration from 4s to 8-10s
- **Transcriber Model**: Changed from `small` to `tiny` (10x faster)
- **Buffer Settings**: Increased buffer for more stable streaming
  - player.js: liveSyncDurationCount 10, maxBufferLength 60
  - player.html: liveSyncDurationCount 20, maxBufferLength 150
- **Low Latency Mode**: Disabled for stability

### Known Trade-offs
- **Latency**: ~3-4 minutes delay (necessary for stability)
- **Subtitles**: Optional (can cause playback issues if they fail)

## [0.3.0] - 2026-03-XX

### Added
- Initial Phase 3 release
- Modular pipeline architecture
- Real-time metrics dashboard
- HLS streaming support
- Subtitle generation and translation
- TTS voice dubbing

### Features
- SRT input via FFmpeg
- Audio extraction and mixing
- Video transcoding with GPU support (NVENC, QSV, AMF)
- Web-based dashboard and player
- WebSocket real-time logging
- REST API for configuration
