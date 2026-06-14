# Sesión actual — F136-F140: Deep audit + systematic fixes (2026-06-13)

## Features completadas esta sesión

### F136: Dead Code Removal (~800 líneas eliminadas) — DONE

- Eliminados 11 archivos muertos: `srt_ingest.py`, `store.ts`, `file-input.ts`, `state.ts`, `clock.ts`, `shared-types.ts`, `performance.ts`, + 4 test files
- Limpiados 4 archivos: `constants.ts`, `utils/index.ts`, `store/index.ts`, `confirm-modal.ts`
- Fix 4 tests que dependían de strings de código eliminado

### F137: Security Fixes (5 issues) — DONE

- `hmac.compare_digest()` para auth token timing-safe (security.py:127, 459)
- JWT empty-string warning (auth_db.py:33)
- MD5 → SHA256 para cache key (translator.py:195)
- Generic error message sin leak de internals (webrtc_routes.py:101)
- Config save failure propagation (routes/config.py:309)

### F138: Extract Encoder Logic (dedup ~200 líneas, 3 bugs fixed) — DONE

- `resolve_encoder()` + `get_encoder_status()` en `core/encoder_config.py`
- Fixed `name="video_muxer"` bug → `name="web"` en HLSOutput
- Fixed broken passthrough mode + CPU mode en VideoMuxer
- Delegated 64+53 lines a 4 lines each

### F139: Extract FFmpeg Process Lifecycle (dedup ~100 líneas) — DONE

- `core/ffmpeg_process.py` con 6 funciones compartidas
- Actualizados srt_input.py, rtmp_input.py, file_input.py

### F140: Fix Test Suite Quality — DONE

- Removed 3 global monkey-patches de conftest.py (os.mkdir, subprocess.run, requests.post)
- Added MagicMock import (mock_whisper_model fixture was broken)
- Removed unused `config_file` fixture
- Fixed 3 `assert ... or True` → real assertions (webhook_manager, structured_log, api_routes)
- Fixed 4 `assert True` no-ops → meaningful assertions (config_validation)
- Fixed `assert is_valid == True` → `assert is_valid` (config_hot_reload)
- Fixed `test_config_hot_reload` to use tmp_path instead of real config.yaml
- Fixed 2 flaky WS auth tests: `patch.dict(os.environ)` to prevent env var leakage in xdist
- Fixed webhook mock setup (AsyncMock as return_value was wrong, used as post_mock)
- Fixed structured log test: check root logger handlers, not child logger

### F141: Server Anti-Patterns — DONE

- Created `server/ctx.py` with shared `get_ctx()` and `is_public_path()` functions
- Replaced 6 duplicate `_ctx()` definitions across route files with import from `server.ctx`
- Consolidated 2 duplicate `_is_public_path()` methods in security.py to delegate to shared function
- Fixed `int(content_length)` without ValueError handling in RequestSizeLimitMiddleware
- Fixed `__import__('time')` anti-pattern in outputs.py → proper `import time`

## Verificación

| Check           | Estado | Notas                 |
| --------------- | ------ | --------------------- |
| init.ps1 -Quick | PASS   | Todos los tests pasan |
| mypy --strict   | PASS   | 0 errores             |
| TypeScript      | PASS   | 0 errores             |
| Frontend tests  | PASS   |                       |
| ruff check      | PASS   |                       |

### F143: Module type safety — DONE

- Fixed operator precedence bug in `piper_loader_script.py`
- Fixed 12 `except Exception: pass` without logging across modules
- Fixed `webrtc_engine.py` Any returns
- Fixed `asyncio.get_event_loop` deprecated usage
- All tests pass, mypy 0 errors

### F144: Test coverage gaps — DONE

- Created tests for strategies.py (22 tests): StrategyConfig, ChunkProcessor, PipelineStrategy ABC, SequentialStrategy, ThreadParallelStrategy, AsyncIOStrategy, \_process_modules
- Created tests for pipeline_helpers.py (8 tests): get_output_module_status with GPU, idle, fallback, error, no-source scenarios
- Created tests for factory.py (9 tests): create_pipeline 3 modes, custom params, invalid mode, case sensitivity, PipelineMode enum, get_available_modes
- Created tests for srt_input.py chunks (12 tests): no dir, no files, too-new, old-enough, latest-excluded, already-processed, gaps, consecutive calls, clock mtime, watchdog notification
- Created tests for hls_output.py remux (12 tests): \_is_h264, passthrough/auto/h264 decision, disabled/skip, mixed audio, output_hls_path, segment_index increment, FFmpeg error/timeout
- **69 new tests, 0 failures**
- All checks pass: init.ps1 -Quick ✅, mypy 0 errors, tsc 0 errors, ruff clean

## Siguiente feature

F145: Naming & style — eliminate `import json as JSON`, fix logger name inconsistency, move PresetSaveRequest to module level
