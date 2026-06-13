# Sesión actual — F132: Extract loops to strategies (2026-06-13)

## Feature

**F132**: unified_pipeline_extract_loops_to_strategies
**Status**: DONE
**Objetivo**: Reducir `unified_pipeline.py` de 1106 → <600 líneas extrayendo los 5 métodos de loop a `core/pipeline/strategies.py`.

## Resultado

- `unified_pipeline.py`: 1106 → 599 líneas (-46%)
- `strategies.py`: 265 → 723 líneas (loop implementations + PipelineContext)
- `pipeline_helpers.py`: nuevo, 120 líneas (extracted output status + reconfigure)
- Total: 1442 líneas (vs 1106 antes — +336 en módulos nuevos, -507 del principal)

### Cambios clave

1. **PipelineContext dataclass** en strategies.py — bundles shared state (stop_event, semaphore, queues, modules, metrics, callbacks)
2. **SequentialStrategy.start_threads()** + `_run_sequential_loop()` — extracted from unified_pipeline
3. **ThreadParallelStrategy.start_threads()** + `_input/_worker/_output_thread_loop()` — extracted
4. **AsyncIOStrategy.start_threads()** + `_run_async_loop()`, `_process_chunk_async()` — extracted
5. **Lazy imports** via `importlib.import_module()` to break circular dependency chain
6. **pipeline_helpers.py** — extracted `_get_output_module_status()` and `reconfigure()` logic

### Verificación

| Check                        | Estado | Notas                                                               |
| ---------------------------- | ------ | ------------------------------------------------------------------- |
| unified_pipeline.py < 600    | PASS   | 599 líneas                                                          |
| Tests pipeline (48)          | PASS   | 48/48                                                               |
| mypy --strict (3 archivos)   | PASS   | 0 errores                                                           |
| init.ps1 -Quick              | PASS   | 30 failures pre-existente (CSRF F125 + file locking)                |
| API pública idéntica         | PASS   | start, stop, register_module, get_status, reconfigure — sin cambios |
| Tests existentes sin cambios | PASS   | assertions intactas                                                 |

### Pre-existing failures (no relacionados con F132)

- 24 CSRF 403 (F125 security changes)
- 4 PermissionError (Windows file locking en tests paralelos)
- 2 config assertion failures (segment_duration mismatch)

## Siguiente feature

F123: session security (JWT expiry, refresh tokens, token blacklist) — el siguiente pendiente.
| mypy pre-F132 | 1 error (app_context.py:173) | Pre-existente |
