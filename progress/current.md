# Sesión actual — F145+F142: Naming/style consistency + Frontend cleanup (2026-06-19)

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

### F146: Fix audio stutter in webplayer + reparar tests pre-existentes — DONE

- **Fix #1 (EXTINF real)**: HLS output ahora ejecuta `get_video_duration(segment_path)` via ffprobe después del mux y escribe la duración real en el manifest en vez del nominal `chunk_duration`.
- **Fix #2 (PipelineData.duration real)**: `srt_input.py` usa `get_video_duration(chunk_path)` al crear `PipelineData`, pasando la duración medida.
- **Fix #3 (crossfade)**: `audio_mixer.py:46` — crossfade aumentado de 10ms a 40ms.
- **Fix #4 (timeout)**: `lost_chunk_timeout_sec` reducido de 30s a 15s.
- **Fix #5 (sample rate)**: `audio_extractor.py:104` — FFmpeg `-ar 8000` corregido a `-ar 24000`.
- **Fix #6 (test mock)**: `test_hls_output.py` — añadido `patch("modules.outputs.hls_output.get_video_duration")` para que el mock de subprocess.run no se rompa por la nueva llamada ffprobe.
- **Fix #7 (config.yaml empty)**: Config restaurado desde commit `83eb251` y actualizado con customizaciones del usuario + `lost_chunk_timeout_sec: 15.0`. Git staged para evitar que `git stash pop` lo vacíe. **17 tests pre-existentes reparados** (config_validation, frontend_dashboard, latency_optimization, performance_optimizations).

## Verificación (post-F142+F145)

| Check        | Estado | Notas             |
| ------------ | ------ | ----------------- |
| pytest unit  | PASS   | 1399 pass, 0 fail |
| tsc --noEmit | PASS   | 0 errores         |
| ruff check   | PASS   | limpio            |

## Features completadas esta sesión

### F145: Naming & style consistency — DONE

- `modules/webrtc_engine.py:12`: `import json as JSON` → `import json`
- `modules/subtitle_generator.py:554`: `import time as _time` (inline) → `import time` global
- `server/routes/config.py`: `PresetSaveRequest` movido de inner class a module level (con `from pydantic import BaseModel` top-level)
- **22 test files**: eliminado `sys.path.insert` redundante (ya lo hace `conftest.py`)
- Ruff clean, tests pasan

### F142: Frontend code quality — DONE

- `Header.astro`: `import('../../lib/utils')` → `import('../../lib/modules/toast')` — ruta correcta para `showToast`
- `PipelineGraph.tsx`: `JSON.stringify(nodes) !== JSON.stringify(initialNodes)` reemplazado por comparación directa de `id`, `type`, `position`
- `Toolbar.tsx`: `window.prompt()` reemplazado por inline input React con Enter/Escape + confirm/cancel
- TypeScript typecheck 0 errores

### Fix 18 tests fallando (config.yaml corrupto) — DONE

- Root cause: `test_config_hot_reload.py` → `manager.save()` con parches incompletos (faltaban `atomic_replace` + `tempfile.mkstemp`)
- Fix: `tmp_path` fixture + `patch("core.config_manager.atomic_replace")`
- 1399 tests pasan, 0 fallos
