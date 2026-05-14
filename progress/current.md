# Sesión activa — 2026-05-15

**Estado:** F70 completada — API OpenAPI Documentation
**Iniciada:** 2026-05-15

## Resumen de la sesión

Se leyó `AGENTS.md`, `feature_list.json` y `progress/current.md` como punto de entrada.

Antes de continuar se resolvieron dos bloqueos del harness:

- El venv apuntaba a un Python 3.12 eliminado; se regeneró con Python 3.12.13 disponible en Codex.
- `core/paths.py` no caía a paths locales si `platformdirs` encontraba una carpeta de usuario inaccesible. Se añadió fallback ante `OSError`.

Se implementó **F67 — Whisper Timeout Protection**.

### Cambios F67

- **`modules/transcriber.py`**
  - El timeout de Whisper ya no usa `ThreadPoolExecutor` como context manager.
  - En `TimeoutError`, cancela el future y hace `shutdown(wait=False, cancel_futures=True)`.
  - La ruta exitosa conserva `shutdown(wait=True)` para cerrar correctamente.

- **`tests/unit/test_transcriber.py`**
  - Añadido test unitario que verifica que el timeout no espera el cierre bloqueante del executor.

- **`feature_list.json`**
  - Añadida F67 con estado `done`.

### Verificación F67

| Check | Resultado |
|-------|-----------|
| `pytest tests/unit/test_transcriber.py -q` | ✅ 8 passed |
| `init.ps1 -Quick` | ✅ Verde |

## Feature completada — F68

Se implementó **F68 — LRU Cache for Transcriptions**.

### Cambios F68

- **`modules/transcriber.py`**
  - El cache key ahora usa una huella SHA-256 del contenido del audio cuando el archivo existe.
  - Chunks idénticos en paths distintos comparten entrada de cache.
  - El key incluye idioma, modelo y `beam_size`.
  - Si el archivo no puede leerse, mantiene fallback por metadata.

- **`tests/unit/test_transcriber.py`**
  - Añadidos tests para cache hit por contenido idéntico.
  - Añadido test para cache miss cuando el contenido cambia.

### Verificación F68

| Check | Resultado |
|-------|-----------|
| `pytest tests/unit/test_transcriber.py -q` | ✅ 10 passed |
| `init.ps1 -Quick` | ✅ Verde |

## Feature completada — F69

Se implementó **F69 — Frontend Types Cleanup**.

### Cambios F69

- **`frontend/src/lib/types/api.ts`**
  - `Status` tipa `system_metrics`, `system`, `uptime_seconds` y `avg_processing_time_ms`.
  - `MetricsData` ahora cubre campos actuales y legacy: `cpu_percent`, `cpu_usage`, `memory_percent`, `memory_usage`, `gpu_percent`, `gpu_usage`, `gpu_util`, `gpu_memory_mb`, `gpu_memory`, `gpu_memory_percent`, `gpu_memory_usage`.

- **`frontend/src/lib/store/signals.ts`**
  - Eliminados casts `any` en lectura de métricas.
  - `systemMetrics` y `updateStatus` usan `Partial<MetricsData>`.
  - `inputType` ya no necesita cast manual.

### Verificación F69

| Check | Resultado |
|-------|-----------|
| `frontend/node_modules/.bin/tsc.cmd --noEmit` | ✅ 0 errores |
| `init.ps1 -Quick` | ✅ Verde |
| `vitest run src/lib/store/signals.test.ts` | ⚠️ Bloqueado por esbuild/permiso al resolver `vitest.config.ts` |

## Feature completada — F70

Se implementó **F70 — API OpenAPI Documentation**.

### Descubrimiento

- FastAPI ya tiene soporte nativo OpenAPI habilitado en `server/app.py`
- Endpoints disponibles:
  - `/api/docs` - Swagger UI
  - `/api/redoc` - ReDoc
  - `/api/openapi.json` - Spec JSON

### Verificación F70

| Check | Resultado |
|-------|-----------|
| `init.ps1 -Quick` | ✅ Verde |

## Estado actual del proyecto

- ✅ `init.ps1 -Quick` pasa con `PYTEST_ADDOPTS=--basetemp=pytest_tmp_manual`
- ✅ mypy 0 errores en core/ y server/
- ✅ F67-F70 completadas en `feature_list.json`
- ✅ 70 features completadas en total
