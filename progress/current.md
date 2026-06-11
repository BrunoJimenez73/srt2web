# Sesión actual — F127 cerrado: fix_initialized_double_assignment (2026-06-12)

## Estado

| Check | Estado | Notas |
|-------|--------|-------|
| Python 3.12.13 | OK | venv ok |
| feature_list.json | OK | F127 done (128–135 pending) |
| pytest tests/unit/test_unified_pipeline.py | OK | 15/15 pass (2 nuevos de F127) |
| mypy --strict core/unified_pipeline.py | OK | 0 errores |

---

## F127 cerrado ✅ — `fix_initialized_double_assignment`

**Resumen**: En `core/unified_pipeline.py.__init__`, `self._initialized = False` aparecía
dos veces — una al principio del método (con comentario "Initialize FIRST to avoid race conditions")
y otra más tarde (~línea 173, con comentario "Initialize to False BEFORE thread starts").
La segunda asignación anulaba la protección de la primera reabriendo una ventana de race condition
justo antes de lanzar el hilo de estrategia.

### Cambio

| Archivo | Cambio |
|---------|--------|
| `core/unified_pipeline.py` | Segunda asignación `self._initialized = False` (~línea 173) reemplazada por comentario explicativo que apunta a la primera asignación como la canónica |
| `tests/unit/test_unified_pipeline.py` | +2 tests en `TestF127InitializedSingleAssignment`: `test_initialized_is_false_after_construction` + `test_initialized_not_reassigned_in_init` (inspección de código fuente con `inspect.getsource`) |

### Detalle del fix

```python
# ANTES (roto — 2 asignaciones):
# Línea ~135:
self._initialized = False   # "Initialize FIRST to avoid race conditions"
# ...100 líneas después...
# Línea ~173:
self._initialized = False   # "Initialize to False BEFORE thread starts"

# DESPUÉS (correcto — 1 asignación + comentario):
# Línea ~135:
self._initialized = False   # "Initialize FIRST to avoid race conditions"
# ...100 líneas después...
# Línea ~173:
# NOTE: _initialized was already set to False at the top of __init__
# (before any attribute that could trigger a race). Do NOT re-assign here.
```

### Verificación

- `pytest tests/unit/test_unified_pipeline.py -v`: 15/15 pass en 0.91s
- `mypy --strict core/unified_pipeline.py`: 0 errores
- `feature_list.json`: F127 done

### Archivos tocados

```
M  core/unified_pipeline.py
M  tests/unit/test_unified_pipeline.py
M  feature_list.json
M  progress/current.md
```

---

## Siguientes features pendientes

| ID | Nombre | Prioridad | Siguiente |
|----|--------|-----------|-----------|
| F128 | fix_merge_config_shallow | Alta | ← siguiente |
| F129 | fix_lost_chunk_timeout_configurable | Media | |
| F130 | audit_env_git_history | Alta | |
| F131 | ffmpeg_pool_dependency_injection | Media | |
| F132 | unified_pipeline_extract_loops_to_strategies | Media | depende F127, F128 |
| F133 | cleanup_para_borrar_folder | Baja | |
| F134 | integration_tests_pipeline_hls | Media | |
| F135 | prometheus_metrics_endpoint | Baja | |
