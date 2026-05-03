# Log Interpretation Guide - SRT2Web

This document explains how to interpret frequent logs in SRT2Web, what they mean, and how to troubleshoot common issues.

## Log Format

SRT2Web uses structured logging with JSON format. Each log line contains:

```json
{
  "module": "module_name",
  "stage": "stage_name",
  "status": "success|error|warning|info",
  "timestamp": 1234567890.123,
  "chunk_index": 1,
  "correlation_id": "uuid-string",
  "duration_ms": 150.5,
  "message": "descriptive message"
}
```

## Common Log Messages

### Pipeline Logs

#### `[Pipeline] Pipeline started`
- **Meaning**: Pipeline has started processing
- **Action**: Normal, no action needed

#### `[Pipeline] Pipeline stopped`
- **Meaning**: Pipeline has stopped
- **Action**: Normal, no action needed

#### `[Pipeline] Chunk X processed successfully`
- **Meaning**: A chunk has been processed completely
- **Action**: Normal, monitor `duration_ms` for performance

### Module Logs

#### `[transcriber] Transcribing chunk X`
- **Meaning**: Whisper is transcribing audio
- **Action**: Normal, check `duration_ms` (should be <5s for tiny model)

#### `[transcriber] CUDA not available, falling back to CPU`
- **Meaning**: GPU not available for Whisper, using CPU instead
- **Action**: Install CUDA toolkit if GPU desired, or set `device: cpu` in config

#### `[tts_engine] TTS engine loaded`
- **Meaning**: TTS engine (Edge-TTS or Piper) is ready
- **Action**: Normal

#### `[tts_engine] Piper model load failed`
- **Meaning**: Piper TTS couldn't load the voice model
- **Action**: Check voice name in config, ensure model files exist in `models/piper/`

#### `[video_muxer] Segment generated: segment_001.ts`
- **Meaning**: HLS segment created successfully
- **Action**: Normal, check if segments appear in `/hls/` directory

#### `[video_muxer] FFmpeg process failed`
- **Meaning**: FFmpeg encountered an error during muxing
- **Action**: Check FFmpeg logs, verify input files exist, check disk space

### Input Logs

#### `[srt_input] Waiting for SRT connection...`
- **Meaning**: SRT input is waiting for OBS or other SRT source to connect
- **Action**: Start OBS and configure SRT output to `srt://127.0.0.1:9000`

#### `[srt_input] SRT connection established`
- **Meaning**: OBS or SRT source has connected
- **Action**: Normal, pipeline should start processing soon

#### `[srt_input] No input video chunk received`
- **Meaning**: Pipeline is running but no chunks are being received
- **Action**: Check OBS is streaming, verify SRT/RTMP connection, check `chunk_duration_sec` in config (min 10s for OBS)

### Output Logs

#### `[video_muxer] HLS stream started`
- **Meaning**: HLS output is ready and streaming
- **Action**: Normal, access stream at `http://localhost:9999/hls/stream.m3u8`

#### `[video_muxer] Output sink not initialized`
- **Meaning**: Output hasn't been set up properly
- **Action**: Check `output.type` in config, ensure output module is enabled

## Warning Logs

### `[WARNING] Duration drift detected`
- **Meaning**: Accumulated drift between input and output timing
- **Action**: Normal for long sessions, monitor if it grows >5s

### `[WARNING] Audio padding/truncation failed`
- **Meaning**: Couldn't adjust audio duration to match video
- **Action**: Usually harmless, check if audio is in sync

### `[WARNING] connection lost, attempting reconnect`
- **Meaning**: WebSocket or SRT connection was lost
- **Action**: Check network, OBS settings; reconnection happens automatically

## Error Logs

### `[ERROR] CUDA not available`
- **Meaning**: GPU not detected or CUDA not installed
- **Action**: Install CUDA Toolkit 12.x, verify with `nvidia-smi`

### `[ERROR] cuDNN not found`
- **Meaning**: cuDNN libraries missing (needed for Piper TTS GPU)
- **Action**: `pip install nvidia-cudnn-cu12`, or set TTS device to `cpu`

### `[ERROR] FFmpeg process crashed`
- **Meaning**: FFmpeg exited unexpectedly
- **Action**: Check FFmpeg logs in `logs/srt2web.log`, verify input files, check disk space

### `[ERROR] Pipeline stage failed: {stage}`
- **Meaning**: A pipeline stage (transcribe, translate, tts, etc.) failed
- **Action**: Check the specific module logs, verify configuration, check input data

### `[ERROR] Circuit breaker opened for {module}`
- **Meaning**: Module failed too many times, circuit breaker tripped
- **Action**: Fix the underlying issue, then restart pipeline to reset circuit breaker

## Performance Logs

### `[transcriber] Transcribing chunk X: 3500ms`
- **Interpretation**:
  - <2000ms: Excellent (GPU)
  - 2000-5000ms: Good (CPU with tiny/base model)
  - >10000ms: Slow, consider smaller model or GPU

### `[tts_engine] TTS generation: 800ms`
- **Interpretation**:
  - <500ms: Excellent (Piper CPU)
  - 500-1500ms: Good (Edge-TTS)
  - >2000ms: Slow, check TTS engine settings

### `[video_muxer] Muxing chunk X: 200ms`
- **Interpretation**:
  - <500ms: Excellent
  - 500-1000ms: Normal
  - >2000ms: Slow, check FFmpeg settings, consider CPU/GPU encoder

## Using Correlation ID

With the new correlation ID feature, you can track all logs related to a specific request or chunk:

```bash
# Find all logs for a specific correlation ID
grep "correlation_id\": \"abc-123\"" logs/srt2web.log

# Or in the frontend, when you see an error, note the correlation_id from the log message
# and search for all related logs
```

## Log Files

- **Console**: Filtered logs (noise removed)
- **logs/srt2web.log**: Full logs with all details
- **Frontend Logs Panel**: Real-time logs in dashboard

## Troubleshooting Checklist

When the pipeline isn't working:

1. Check if OBS is streaming to SRT/RTMP
2. Verify `chunk_duration_sec` is at least 10s (for OBS keyframe interval)
3. Check if all modules are enabled in config
4. Look for `[ERROR]` messages in logs
5. Verify FFmpeg is installed: `ffmpeg -version`
6. Check GPU availability: `nvidia-smi`
7. Review circuit breaker state in `/api/status`
8. Restart pipeline if circuit breaker is open
9. Check disk space for HLS segments
10. Verify Python dependencies: `pip list`
