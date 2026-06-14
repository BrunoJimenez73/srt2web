# Plan de mejoras — análisis de código (Bruno, 2026-06-12)

> Generado tras auditoría estática del repo. Sigue las reglas de AGENTS.md:
> una feature a la vez, init.ps1 verde para declarar done, tests obligatorios.
> Añadir cada feature a `feature_list.json` antes de empezar.

---

## Resumen ejecutivo

| Categoría   | Ítems | Impacto estimado                     |
| ----------- | ----: | ------------------------------------ |
| Bugs reales |     3 | Alto — comportamiento incorrecto hoy |
| Seguridad   |     1 | Alto — secretos en historial Git     |
| Refactor    |     3 | Medio — mantenibilidad y deuda       |
| Calidad     |     2 | Medio — tests y observabilidad       |
| Limpieza    |     1 | Bajo — carpeta residual              |

**Orden sugerido:** B1 → B2 → B3 → S1 → R1 → R2 → R3 → Q1 → Q2 → L1

---

## B1 — Bug: \_initialized asignado dos veces (race condition anulada)

**ID propuesto:** F127
**Área:** core · pipeline
**Prioridad:** Alta
**Riesgo:** Medio

### Problema

En `core/unified_pipeline.py`, `__init__` asigna `self._initialized = False` en **dos líneas distintas**
(~línea 165 y ~línea 210). El comentario de la primera dice "Initialize FIRST to avoid race
conditions" pero la segunda asignación sobrescribe la primera, anulando cualquier efecto de orden.

La consecuencia práctica: si hay una carrera entre `start()` y un hilo externo que lee
`_initialized` mientras `__init__` todavía se ejecuta, el valor puede ser inconsistente.

### Fix propuesto

Eliminar la segunda asignación duplicada. Dejar solo la primera (antes de que cualquier hilo
pueda ser lanzado). Revisar si el comentario sigue siendo preciso.

### Archivos

```
core/unified_pipeline.py   (eliminar línea duplicada ~210)
tests/unit/test_unified_pipeline.py   (test: __init__ no asigna _initialized dos veces)
```

### Acceptance

- Solo una asignación de `_initialized` en `__init__`
- Test verifica que `UnifiedPipeline()` tiene `_initialized == False` inmediatamente tras construcción
- `mypy --strict core/` pasa
- `init.ps1 -Quick` verde

---

## B2 — Bug: \_merge_config hace merge superficial, destruye sub-dicts

**ID propuesto:** F128
**Área:** core · pipeline_manager
**Prioridad:** Alta
**Riesgo:** Medio

### Problema

`core/pipeline_manager.py._merge_config()` usa `dict.update()` para mezclar custom config sobre
defaults. Esto es una merge de **un solo nivel**: si `custom_config` contiene
`{"pipeline": {"retry_delay": 2.0}}`, el update reemplaza _todo_ el bloque `"pipeline"` del
default, perdiendo `chunk_duration_sec`, `buffer_size` y `retry_attempts`.

`ConfigManager` ya tiene un `_deep_merge()` correcto que no se reutiliza aquí.

### Fix propuesto

Importar o replicar `_deep_merge` de `core/config_manager.py` y usarlo en `_merge_config`.

```python
# Antes (shallow, roto):
merged[key].update(value)

# Después (profundo, correcto):
merged[key] = _deep_merge(merged[key], value)
```

### Archivos

```
core/pipeline_manager.py   (fix _merge_config, importar _deep_merge o inline)
tests/unit/test_pipeline_manager.py   (test: merge de sub-dict no destruye claves hermanas)
```

### Acceptance

- `_merge_config({"pipeline": {"retry_delay": 2.0}})` conserva `chunk_duration_sec=10`
- Test cubre merge de cada sección (pipeline, input, output, modules)
- `mypy --strict core/` pasa
- `init.ps1 -Quick` verde

---

## B3 — Bug: lost-chunk timeout no es configurable (30 s hardcodeado)

**ID propuesto:** F129
**Área:** core · pipeline
**Prioridad:** Media
**Riesgo:** Bajo

### Problema

En `core/unified_pipeline.py._output_thread_loop()`, la constante `_LOST_CHUNK_TIMEOUT = 30.0`
está hardcodeada. En streams con Whisper en CPU (transcripción ~20-40 s por chunk en hardware
lento) o con Piper TTS cargando modelo, un chunk válido puede ser descartado prematuramente,
produciendo huecos en el HLS.

### Fix propuesto

Leer el timeout desde config con fallback al valor actual:

```python
_LOST_CHUNK_TIMEOUT = self._config.get("pipeline.lost_chunk_timeout_sec", 30.0)
```

Alternativamente, exponerlo en `__init__` como parámetro.

### Archivos

```
core/unified_pipeline.py   (parametrizar _LOST_CHUNK_TIMEOUT)
core/config_schema.py      (añadir lost_chunk_timeout_sec al schema Pydantic)
tests/unit/test_unified_pipeline.py   (test: timeout configurable)
```

### Acceptance

- `SRT2WEB_LOST_CHUNK_TIMEOUT` o `config.yaml pipeline.lost_chunk_timeout_sec` controla el timeout
- Default sigue siendo 30 s (no regresión)
- Test verifica que el pipeline usa el valor configurado
- `init.ps1 -Quick` verde

---

## S1 — Seguridad: verificar historial Git de .env

**ID propuesto:** F130
**Área:** security
**Prioridad:** Alta
**Riesgo:** Bajo (solo diagnóstico + docs)

### Problema

El archivo `.env` (con `SRT2WEB_JWT_SECRET`, `AUTH_TOKEN`, etc.) está presente en el directorio
raíz. Si alguna vez se añadió al índice de Git con valores reales, esos secretos persisten en el
historial aunque el archivo esté ahora en `.gitignore`.

### Fix propuesto

1. Ejecutar `git log --all --oneline -- .env` para ver si hay commits que lo incluyen.
2. Si los hay, rotar todos los secretos afectados.
3. Usar `git-filter-repo` o `BFG Repo Cleaner` para purgar si el repo es público.
4. Añadir `.env` a `.gitignore` si no está (verificar).
5. Documentar el procedimiento en `docs/deployment.md`.

### Archivos

```
.gitignore                  (verificar entrada .env)
docs/deployment.md          (sección "Secretos y .env")
scripts/check_secrets.py    (NUEVO: smoke test que verifica que .env no está trackeado)
```

### Acceptance

- `git ls-files .env` devuelve vacío (no trackeado)
- `scripts/check_secrets.py` detecta si `.env` aparece en `git log --all`
- `docs/deployment.md` tiene instrucciones de rotación
- `init.ps1 -Quick` verde

---

## R1 — Refactor: FFmpegPool como singleton global → inyección de dependencias

**ID propuesto:** F131
**Área:** core · ffmpeg_pool
**Prioridad:** Media
**Riesgo:** Medio

### Problema

`core/ffmpeg_pool.get_pool()` crea y mantiene un singleton global mutable (`_pool`). Esto
complica los tests (hay que resetear el estado global entre tests) y hace imposible tener pools
independientes en multi-pipeline. Varios módulos llaman a `get_pool()` directamente sin
recibir el pool como dependencia.

### Fix propuesto

1. `get_pool()` sigue existiendo para compatibilidad, pero recomienda deprecación.
2. `app_context.py` crea el pool y lo inyecta en los módulos que lo necesitan
   (`audio_extractor`, `audio_mixer`, `video_muxer`).
3. Los módulos aceptan `pool: FFmpegPool | None = None` con fallback a `get_pool()`.

### Archivos

```
core/ffmpeg_pool.py         (añadir docstring deprecation a get_pool)
core/app_context.py         (crear pool + inyectar en módulos)
modules/audio_extractor.py  (aceptar pool inyectado)
modules/audio_mixer.py      (aceptar pool inyectado)
modules/video_muxer.py      (aceptar pool inyectado)
tests/unit/test_ffmpeg_pool.py (test: pool inyectado no usa singleton)
```

### Acceptance

- Tests de módulos crean pool propio sin contaminar el singleton global
- `get_pool()` sigue funcionando (no regresión en producción)
- `mypy --strict core/ modules/` pasa
- `init.ps1 -Quick` verde

---

## R2 — Refactor: unified_pipeline.py — extraer loops a estrategias

**ID propuesto:** F132
**Área:** core · pipeline
**Prioridad:** Media
**Riesgo:** Alto

### Problema

`core/unified_pipeline.py` tiene 1103 líneas. Los métodos `_run_sequential_loop`,
`_input_thread_loop`, `_worker_thread_loop`, `_output_thread_loop` y `_run_async_loop`
pertenecen conceptualmente a las estrategias de `core/pipeline/strategies.py` (que ya existe
como módulo F66), pero nunca se movieron allí.

### Fix propuesto

Mover los 5 métodos de loop a sus clases de estrategia correspondientes. `UnifiedPipeline`
delega solo en `self._strategy.run(...)`. API pública sin breaking changes.

**Orden seguro:**

1. Mover `_run_sequential_loop` → `SequentialStrategy`
2. Mover `_input_thread_loop + _worker_thread_loop + _output_thread_loop` → `ThreadParallelStrategy`
3. Mover `_run_async_loop + _process_chunk_async*` → `AsyncIOStrategy`
4. `UnifiedPipeline.start()` llama `self._strategy.start_loops(input_source, output_sink, modules)`

### Archivos

```
core/unified_pipeline.py            (delegar loops, reducir a <600 líneas)
core/pipeline/strategies.py         (recibir loops)
tests/unit/test_unified_pipeline.py (regresión: comportamiento idéntico)
tests/unit/test_pipeline_strategies.py (tests de loops unitarios)
```

### Acceptance

- `unified_pipeline.py` < 600 líneas
- API pública idéntica (start, stop, register_module, get_status)
- Tests existentes de pipeline pasan sin cambiar assertions
- `mypy --strict core/` pasa
- `init.ps1 -Quick` verde

**⚠️ Nota:** Este es el cambio más arriesgado del plan. Hacerlo en commits pequeños, uno por estrategia.

---

## R3 — Refactor: limpiar carpeta "PARA BORRAR" definitivamente

**ID propuesto:** F133
**Área:** maintenance
**Prioridad:** Baja
**Riesgo:** Bajo

### Problema

`PARA BORRAR/` sigue en el árbol de trabajo (aunque gitignored según AGENTS.md).
Contiene `.openclaude/` (config local preservada según F110) y `temp/pytest-of-bruno/`
(bloqueado por Windows según F110). Presencia confunde a nuevos colaboradores.

### Fix propuesto

1. Verificar si `.openclaude/` puede moverse a `~/.openclaude/` o similar.
2. Limpiar `temp/pytest-of-bruno/` con shell admin o reboot.
3. Si la carpeta queda vacía, eliminarla del árbol.
4. AGENTS.md ya tiene la regla "No toques PARA BORRAR/" — actualizar una vez vacía.

### Archivos

```
PARA BORRAR/    (vaciar y eliminar si posible)
AGENTS.md       (actualizar regla si carpeta desaparece)
.gitignore      (verificar entrada PARA BORRAR/)
```

### Acceptance

- `PARA BORRAR/` ausente del árbol o con solo `README.md` explicativo
- `git status` limpio
- `init.ps1 -Quick` verde

---

## Q1 — Calidad: tests de integración reales para flujo pipeline → HLS

**ID propuesto:** F134
**Área:** testing
**Prioridad:** Media
**Riesgo:** Bajo

### Problema

`tests/integration/` existe pero está prácticamente vacío de tests que cubran el flujo completo.
Los 90+ tests son todos unitarios. Un fallo en la interacción entre
`UnifiedPipeline + HLSOutput + WebSocket broadcast` no quedaría detectado.

### Fix propuesto

Añadir al menos 3 tests de integración que usen mocks ligeros (no hardware real):

1. `test_pipeline_hls_segment_creation`: pipeline procesa chunk → HLS output escribe segmento
2. `test_pipeline_module_failure_recovery`: módulo no-crítico falla → pipeline continúa
3. `test_pipeline_start_stop_clean`: start + stop deja estado IDLE, sin threads colgados

### Archivos

```
tests/integration/test_pipeline_hls_flow.py   (NUEVO, 3 tests)
tests/conftest.py                              (fixtures compartidas si necesario)
```

### Acceptance

- `pytest tests/integration/ -m "not slow"` pasa en < 10 s
- Tests no requieren hardware real (mocks de FFmpeg, HLS output en tmp dir)
- Marcados `@pytest.mark.integration`
- `init.ps1 -Quick` verde (integration tests no corren en Quick mode, pero no rompen colección)

---

## Q2 — Calidad: endpoint /metrics en formato Prometheus

**ID propuesto:** F135
**Área:** observability
**Prioridad:** Baja
**Riesgo:** Bajo

### Problema

`GET /health` devuelve JSON útil pero no es consumible por Prometheus/Grafana directamente.
Para integrar con alerting estándar se necesita un endpoint `/metrics` con formato
`text/plain; version=0.0.4` (formato de exposición Prometheus).

### Fix propuesto

Añadir `GET /metrics` en `server/api_routes.py` o un router nuevo `server/routes/metrics.py`
que exponga las métricas clave:

```
srt2web_chunks_processed_total
srt2web_chunks_failed_total
srt2web_pipeline_state{state="running"} 1
srt2web_module_processing_time_ms{module="transcriber"}
srt2web_memory_mb
```

No requiere librería externa (formato es texto plano sencillo).

### Archivos

```
server/routes/metrics.py   (NUEVO — endpoint /metrics Prometheus)
server/api_routes.py        (registrar router)
tests/unit/test_metrics_endpoint.py (verificar formato text/plain)
```

### Acceptance

- `GET /metrics` responde `Content-Type: text/plain; version=0.0.4`
- Contiene al menos 5 métricas básicas
- `curl localhost:9999/api/metrics | grep srt2web_` devuelve resultados
- Test verifica formato (no solo status 200)
- `init.ps1 -Quick` verde

---

## Cómo añadir estas features a feature_list.json

Antes de empezar cualquier feature, añadirla al JSON con status `pending`:

```json
{
  "id": 127,
  "name": "fix_initialized_double_assignment",
  "title": "Fix: _initialized asignado dos veces en UnifiedPipeline.__init__",
  "status": "pending",
  "area": "core",
  "priority": "Alta"
}
```

Seguir la secuencia del AGENTS.md:

1. Cambiar a `in_progress` + documentar en `progress/current.md`
2. Implementar + tests
3. `init.ps1 -Quick` verde
4. Cambiar a `done` + actualizar `progress/history.md`

---

## Orden de implementación recomendado

```
B1 (F127) → B2 (F128)
     ↓            ↓
     └─── B3 (F129) ──→ S1 (F130)
                              ↓
                         R1 (F131) → Q2 (F135)
                              ↓
                         Q1 (F134)
                              ↓
                    R2 (F132, alto riesgo, solo cuando hay tiempo)
                              ↓
                         R3 (F133, limpieza final)
```

**B1 y B2 primero** porque son bugs silenciosos que afectan comportamiento hoy.
**S1 pronto** porque implica rotación de secretos si hay exposición.
**R2 al final** por su riesgo alto — requiere sesión dedicada sin prisa.
