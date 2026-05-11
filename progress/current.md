# Sesión activa — 2026-05-12

**Feature:** 4 — add_missing_core_tests
**Inicio:** now
**Estado:** done

## Cambios realizados

### test_hls_output.py (nuevo) — 11 tests

- Init con/sin configuración, configure, stop (shutdown_pool), get_status (idle/extra), get_stream_info, write (none path, nonexistent path)

### test_srt_input.py (nuevo) — 12 tests

- Init default/custom, GPU info, watchdog; configure; get_connection_info (listener/caller); get_next_chunk (sin chunks, vacío, chunk único fresco, retorna data, tracking de índices, salta procesados); is_receiving, is_healthy, get_status

### test_unified_pipeline.py (nuevo) — 11 tests

- register_module (con/sin config, múltiples, not found, get_modules); get_status (idle, keys, módulos registrados, mode default); reconfigure (chunk_duration, module configure); PipelineData defaults/fields

### test_output_modules.py (nuevo) — 16 tests

- FileOutput: init, configure, start (crea dirs), stop, write (copia video, salta missing), get_stream_info
- RTMPOutput: init, configure, is_streaming, get_stream_info, write (sin streaming)
- SRTOutput: init, configure, is_streaming, get_stream_info
- WebRTCOutput: init, start/stop, get_stream_info, write

### test_async_pipeline_v2.py — reactivado (23 tests, 1 fix)

- Se quitó `--ignore` de pytest.ini
- Fix: import cambiado de `AsyncPipeline as AsyncPipelineV2` a `AsyncPipelineV2` directo
- Fix: `pipeline._state` → `pipeline.state` en test_start_running_pipeline

### core/pipeline/base.py — Fix compatibilidad

- `PipelineStrategy` convertido de ABC a clase concreta para backward-compat con `SequentialPipeline`, `ParallelPipeline`, `AsyncPipeline`, `AsyncPipelineV2`
- La nueva ABC `strategies.PipelineStrategy` sigue igual para el pipeline unificado

## Resultados

- `pytest tests/unit/ -m "not slow" -n auto` → 967 passed, 9 failed (pre-existentes)
- Tests nuevos: 85 passed
- init.ps1 -Quick → OK
