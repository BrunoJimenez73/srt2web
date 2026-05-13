# Sesión activa — 2026-05-13

**Estado:** Plan de optimización de latencia creado
**Iniciada:** 2026-05-13

## Audit de features

### Features completamente OK:

- F15 (WS Resilience): exponential backoff con jitter, polling adaptivo ✅
- F20 (Output Health): implementado en todos los outputs, 16 tests ✅
- F22 (Cleanup dead code): todos los archivos eliminados ✅
- F24 (mypy strict): 0 errores en core/ y server/ ✅
- F18, F19, F21, F23, F25, F27, F28: sin incidencias ✅

### Features con detalles a arreglar:

**F26 (Mobile Responsive)**
| Componente | Esperado | Real | Severidad |
|---|---|---|---|
| ProcessGrid.astro | 1 col <640px, 2 cols 640-1024px, 4 cols >1024px | 1 col <768px, 3 cols max | Media |
| Header.astro | Botones colapsables <640px | Sin media queries | Alta |
| MetricsCard.astro | 1 col <480px | 1 col <600px | Baja |
| StatusCard.astro | URLs truncadas | Pendiente verificar | Media |
| LogPanel.astro | max-height 40vh móvil | Pendiente verificar | Baja |

**F29 (Repo hygiene)**

- pytest_tmp_manual/ existe en disco → Baja
- startup_stdout.txt y startup_stderr.txt existen en raíz → Alta (no deberían)

## F30 Sincronización fina de subtítulos

**Feature**: F30 Sincronización fina de subtítulos y optimización de rendimiento
**Status**: done
**Plan**:

- Día 1-2: Backend core (cache, monitor, config, API)
- Día 3: Frontend (signals, effects, badge)
- Día 4: Tests e integración

### Resumen

- ✅ core/cache.py: LRUCache con TTL (max 500, TTL 60s)
- ✅ modules/subtitle_generator.py: timestamp_cache + sync_correction_factor
- ✅ core/subtitle_sync_monitor.py: detección de drift con exponential smoothing
- ✅ core/app_context.py: registro del monitor en pipeline
- ✅ core/config_schema.py: SubtitleSyncConfig (threshold, enable_drift_detection, history_size)
- ✅ server/routes/pipeline.py: /status expone sync object (drift_ms, state, correction_active)
- ✅ Frontend signals.ts: syncDriftMs, syncState, syncCorrectionActive
- ✅ Frontend effects.ts: actualización automática desde pipelineStatus.sync
- ✅ Frontend SubtitleCard.astro: badge con 3 estados (IN SYNC / DRIFT DETECTED / CORRECTING)
- ✅ Tests: test_subtitle_sync_monitor.py (4 tests), test_subtitle_generator.py (4 tests)
- ✅ init.ps1 -Quick: todos verdes, mypy 0 errores
- ✅ TypeScript tsc --noEmit: 0 errores

### Pendiente (futuro)

- Conexión automática entre SubtitleSyncMonitor y SubtitleGenerator (sync_correction_factor)
- Persistencia de estado post-crash
- Latencia de subtítulo medida en logs

**Bloqueadores**: Ninguno
**Notas**: Ver IMPLEMENTACION_PASO_A_PASO.md para arquitectura completa

## Plan de optimización de latencia (F31-F33)

Basado en análisis de logs del 13/05. Latencia total actual ~20-24s extremo a extremo.
Procesamiento por chunk (10s): ~3.5s (HLS encode 49%, audio extract 30%, whisper 9%, translate 7%, TTS 4%)

| ID | Feature | Ahorro estimado | Riesgo | Estado |
|----|---------|----------------|--------|--------|
| F31 | HLS passthrough (encoder_mode: passthrough) | ~1650ms (49%) | Bajo | ✅ done |
| F32 | Eliminar -threads 1 en audio_extractor | ~200-400ms (9%) | Bajo | ⏳ pending |
| F33 | Pipeline parallelism (solapamiento real) | ~300ms (8%) | Medio | ⏳ pending |

**Target post-optimización**: ~1.7s procesamiento → E2E ~10-12s
**Orden**: F31 ✅ → F32 → F33

### F31 — HLS passthrough (completado 13/05)
- config.yaml: encoder_mode cambiado de auto a passthrough en output.web, output.hls, named outputs y video_muxer
- hls_output.py: audio en modo passthrough sin TTS usa -c:a copy (sin recodificar)
- Ahorro estimado: de ~1700ms a ~50ms por chunk
