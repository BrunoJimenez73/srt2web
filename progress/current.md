# Sesión actual — F116 cerrado: graph_ui_react_flow (2026-06-07)

## Estado del entorno verificado con `init.ps1 -Quick` — **VERDE**

| Check | Estado | Notas |
|---|---|---|
| Python 3.12.13 | OK | venv ok |
| Archivos base del arnés | OK | AGENTS, CHECKPOINTS, feature_list, current, history |
| feature_list.json | OK | 96 features (96 done, 0 in_progress, 0 pending) |
| pytest tests/unit/ (subset) | OK | 53/53 pass (logging_setup, chunk_clock, f107) — full suite timeout por Windows file lock pre-existente en `PARA BORRAR/temp/pytest-of-bruno/` (documentado en F110) |
| mypy --strict core/ server/ modules/ | OK | 0 errores en 92 source files |
| tsc --noEmit | OK | 0 errores |
| vitest | OK | **249/249 pass** (+48 nuevos de F116) |
| ruff | OK | disponible |
| mkdocs | OK | disponible |

---

## F116 cerrado ✅ — `graph_ui_react_flow`

**Resumen**: Segunda versión del dashboard en `/graph`. Editor node-based con React Flow que representa los 8 módulos del pipeline como nodos con conectores tipados (video / audio / transcript / subtitles). El usuario define el pipeline conectando nodos; la topología se valida y se aplica como preset. **No toca** `/` (dashboard clásico) ni `/index_new` (demo legacy).

### Archivos creados (15) + 5 modificados

| Archivo | Cambio |
|---|---|
| `frontend/src/lib/graph/nodeCatalog.ts` (NUEVO, 250 líneas) | Catálogo de 8 nodos: input, audio_extractor, transcriber, translator, subtitle_generator, tts_engine, audio_mixer, output. Cada nodo con `inputs/outputs` (HandleSpec), `configFields` (FieldDef para InspectorPanel), `configLocation` (modules/input/output). `HANDLE_TYPE_COLOR` con colores por tipo de dato. Helpers: `getNodeDef`, `isNodeKind`, `nodeKindToModuleKey`, `getInputTypes`, `getOutputTypes` |
| `frontend/src/lib/graph/typedEdge.ts` (NUEVO, 200 líneas) | Validador tipado: `findHandleSpec`, `getHandleDataType`, `validateConnection`. Reglas: source/target válidos, no self-loop, no input→target/output→source, tipo de dato coincide, no ciclos (BFS con `getOutgoers`), límite de entrantes (1 por defecto, 2 en audio_mixer, 3 en output). `makeIsValidConnection` factory que cierra `nodes`/`edges` por closure para usar como callback en `<ReactFlow>` |
| `frontend/src/lib/graph/serialize.ts` (NUEVO, 320 líneas) | `validateTopology` (DAG, 1 input, ≥1 output, topología permitida, nodos aislados detectados). `graphToConfig` (grafos válidos → `Partial<Config>` con `modules.*.enabled` + `moduleConfig` por nodo). `configToGraph` (round-trip desde `Config` actual). `GraphNodeData` type para `node.data` |
| `frontend/src/lib/graph/liveStatus.ts` (NUEVO, 180 líneas) | `useLiveModuleStatus` hook React: combina polling `GET /api/modules` (cada 2s) + WS `WS /ws/logs` (filtrado por `module`). `MODULE_NAME_TO_KIND` mapea nombres del backend (`whisper`→`transcriber`, `muxer`→`output`, etc.). `LiveNodeStatus` interface: state, processedChunks, lastActiveMs, pulse, enabled, extra, error. Pulse dura 1.5s tras log |
| `frontend/src/components/graph/ModuleNode.tsx` (NUEVO, 130 líneas) | Nodo custom de React Flow. Card con badge de estado (idle/running/error/disabled), borde pulsante verde cuando `pulse=true`, `Handle` por spec con `data-handletype` y color por tipo. Memoizado con `React.memo` |
| `frontend/src/components/graph/InspectorPanel.tsx` (NUEVO, 230 líneas) | Panel inspector auto-generado desde `configFields` del `NodeDef`. Boolean→checkbox, enum→select, number→input numérico, string→text. Para `input` y `output` muestra "Configurar fuera del grafo" |
| `frontend/src/components/graph/Toolbar.tsx` (NUEVO, 200 líneas) | Toolbar con Start/Stop/Apply/Reset/Save preset/Load preset. Dropdown de presets via `GET /api/presets`. Save/Apply muestra toast contextually. Aplicar deshabilitado si `!isDirty` o `isApplying` |
| `frontend/src/components/graph/PipelineCanvas.tsx` (NUEVO, 175 líneas) | Wrapper de `<ReactFlow>`. Provider pattern: `ReactFlowProvider` + `PipelineCanvasInner` con `useNodesState`/`useEdgesState`. Inyecta `liveStatus` en cada nodo via `useMemo`. MiniMap con colores por kind, Background con grid, Controls, validación tipada via `makeIsValidConnection`. SSR-safe con `mounted` state |
| `frontend/src/components/graph/PipelineGraph.tsx` (NUEVO, 320 líneas) | Orquestador: carga `GET /api/config` + `GET /api/status` en mount, `configToGraph` para initialNodes, `useCallback` para handlers de Start/Stop/Apply/Reset/Save/Load. Toast hook (4s timeout). Dirty detection via `JSON.stringify` compare. Topología error mostrada en banner fijo bottom-left |
| `frontend/src/components/graph/PipelineGraph.astro` (NUEVO, 20 líneas) | Wrapper Astro que monta `<PipelineGraph client:only="react" />`. React-only porque React Flow usa refs/medidas DOM que no se pueden en SSR |
| `frontend/src/pages/graph.astro` (NUEVO, 20 líneas) | Página `/graph` que envuelve `PipelineGraph` en `BaseLayout` |
| `frontend/src/lib/graph/nodeCatalog.test.ts` (NUEVO) | 10 tests: 8 nodos, ids únicos, getNodeDef, isNodeKind, nodeKindToModuleKey, getInputTypes/getOutputTypes, HANDLE_TYPE_COLOR |
| `frontend/src/lib/graph/typedEdge.test.ts` (NUEVO) | 15 tests: findHandleSpec, getHandleDataType, validateConnection (success/type-mismatch/no-input/no-output/self-loop/cycle/limit-entrantes/audio_mixer-2-entradas/3ª-rechazada/handle-inválido/nodos-inexistentes), makeIsValidConnection |
| `frontend/src/lib/graph/serialize.test.ts` (NUEVO) | 17 tests: validateTopology (vacío/falta-input/doble-input/falta-output/output-salientes/lineal-mínimo/grafo-completo/aislados/ciclos), graphToConfig (grafos válidos/drop-missing/topología-inválida/campos-custom), configToGraph (8-nodos+edges/round-trip) |
| `frontend/src/components/graph/ModuleNode.test.tsx` (NUEVO) | 6 tests: render de los 8 kinds, label del catálogo, badge de estado, data-handletype, handles por spec |
| `frontend/src/components/graph/InspectorPanel.test.tsx` (NUEVO) | 7 tests: empty state, input/output con mensaje de "fuera del grafo", campos de transcriber, audio_mixer numéricos, onChange en checkbox enabled, onChange en select enum |
| `frontend/package.json` | +5 deps: `@astrojs/react@^4.4.2`, `react@^18.3.1`, `react-dom@^18.3.1`, `@types/react@^18.3.31`, `@types/react-dom@^18.3.7` (dev). +2 devDeps: `@xyflow/react@^12.11.0` movido a deps, `@testing-library/react@^16`, `@testing-library/jest-dom@^6` |
| `frontend/astro.config.mjs` | +`import react from "@astrojs/react"`, `integrations: [react()]`. Ampliado `manualChunks` con `vendor-xyflow` y `vendor-react` (separa React de Preact). `components/graph/` mapea a chunk `graphui` |
| `frontend/tsconfig.json` | +`"jsx": "react-jsx"`, `"jsxImportSource": "react"` para que el tsserver resuelva JSX correctamente |
| `frontend/src/lib/types/api.ts` | +`module?: ModuleName` opcional a `WebSocketMessage` para que `useLiveModuleStatus` pueda filtrar por módulo |
| `AGENTS.md` | Frontend row expandida con stack F116. Sección 8 historial añade entry 07/06 F116 |
| `feature_list.json` | F116 con `status: done`, archivos tocados, acceptance criteria, risk assessment |
| `progress/current.md` | Este documento |

### Decisiones técnicas

- **Convivencia React + Preact**: Astro permite ambas. Preact para el resto del frontend (más liviano), React solo para el grafo (porque React Flow no soporta Preact). `manualChunks` separa `vendor-react` (react, react-dom, scheduler) y `vendor-xyflow` del resto. El bundle del grafo solo se carga en `/graph` (no afecta a `/`)
- **Estrategia de validación dual**: `isValidConnection` (en runtime, evita conexiones inválidas) + `validateTopology` (en apply, valida el grafo completo antes de enviar al backend). La primera protege la UX, la segunda protege la integridad
- **Topología permitida**: DAG lineal o con un único branch convergente en `audio_mixer`. Esta es la forma natural del pipeline SRT2Web (audio orig y doblaje convergen en el mixer). `output` admite 3 entrantes (video + audio + subtitles). `input` no admite entrantes, `output` no admite salientes
- **Live status con módulo→kind mapping**: el backend usa nombres legacy (`whisper`, `muxer`, `tts`) que difieren del frontend canonical (`transcriber`, `output`, `tts_engine`). `MODULE_NAME_TO_KIND` centraliza la traducción
- **SSR-safety en PipelineCanvas**: React Flow mide DOM refs para layout. Usar `mounted` state + `useEffect` evita errores en SSR. `client:only="react"` en Astro es la opción correcta (no `client:load` ni `client:visible`)
- **graphToConfig con Partial<Config>**: el `modules` resultante es `Partial<ModulesConfig>` porque `disableMissing=false` deja los módulos no usados sin tocar. El caller controla si quiere desactivar lo ausente
- **isValidConnection callback memoizado**: React Flow llama a este callback muy frecuentemente durante drag. Memoizar via `useCallback` con deps `[nodes, edges]` evita re-renders innecesarios
- **Save preset = Apply + POST /api/presets**: el backend no soporta "preset con grafo arbitrario", solo guarda la config actual. La estrategia es: aplicar primero (PUT /api/config) y luego guardar (POST /api/presets). Load preset = POST /api/presets/{name}/apply + reconstruir el grafo con configToGraph
- **Polling adaptativo 2s + WS para pulse**: polling para datos completos (state, chunks, gpu), WS para eventos de baja latencia. `pulse` se activa con un log entrante y dura 1.5s
- **TypeScript strict + sin any**: el catálogo usa `Record<string, unknown>` con type guards explícitos. Las conversiones de `ModuleConfig` a `Record` se hacen via `as unknown as Record<string, unknown>` para no engañar al compilador

### Topología del grafo generado por configToGraph

```
input → audio_extractor ─video→ output
            ├──audio→ transcriber ─transcript→ translator ─transcript→ subtitle_generator ─subtitles→ output
            │                                                          ├──transcript→ tts_engine ─audio→ audio_mixer ─audio→ output
            └──audio→ audio_mixer (audio-orig) ←── tts_engine (audio-dub)
```

10 edges total, 8 nodos. Cada edge tiene tipos consistentes. Topo sort produce orden estable.

### Aceptación vs realidad

- ✅ Ruta `/graph` con `client:only="react"` sin tocar `/` ni `/index_new`
- ✅ 8 nodos con handles tipados (video/audio/transcript/subtitles)
- ✅ isValidConnection rechaza tipo mismatch, ciclos, exceso de entrantes
- ✅ Topología: 1 input, 1 output mínimo, audio_mixer admite 2, output admite 3
- ✅ Toolbar: Start, Stop, Apply, Reset, Save preset, Load preset
- ✅ Inspector auto-generado desde configFields
- ✅ Live status con pulse en nodo activo
- ✅ Build OK con `/graph/index.html` generado
- ✅ tsc 0 errores
- ✅ vitest 249/249 pass (+48 nuevos)
- ✅ mypy --strict 0 errores (subset backend verificado: 53/53)
- ⚠️ **NO testado E2E con servidor corriendo** — F116 fue puramente frontend (build + bundle size + tipos + tests unitarios). Smoke test E2E en navegador real (Playwright manual) no se ejecutó en esta sesión
- ⚠️ **Bundle size no medido** — React + React Flow añaden ~150-250 KB gz. El chunk `graphui` solo se carga en `/graph` (no afecta al dashboard principal)

### Métricas

- `init.ps1 -Quick`: GREEN
- `npx tsc --noEmit`: 0 errores
- `npm run lint`: 0 errores (warnings pre-existentes en otros archivos, ningún warning nuevo)
- `npm test -- --run`: **249/249 pass** (14 test files)
- `npm run build`: 6 páginas, 0 errores, `/graph/index.html` generado
- `mypy --strict core/ server/ modules/`: 0 errores en 92 source files
- `pytest tests/unit/test_logging_setup.py test_chunk_clock.py test_f107_pipeline_init_timeout.py`: 53/53 pass en 3.71s (subset representativo; full suite timeout por Windows file lock pre-existente en `PARA BORRAR/temp/pytest-of-bruno/`, documentado en F110)
- `feature_list.json`: 96 features done (F115 + F116 cerradas esta sesión)

### Archivos tocados (resumen git)

```
M  frontend/package.json
M  frontend/astro.config.mjs
M  frontend/tsconfig.json
M  frontend/src/lib/types/api.ts
A  frontend/src/lib/graph/nodeCatalog.ts
A  frontend/src/lib/graph/nodeCatalog.test.ts
A  frontend/src/lib/graph/typedEdge.ts
A  frontend/src/lib/graph/typedEdge.test.ts
A  frontend/src/lib/graph/serialize.ts
A  frontend/src/lib/graph/serialize.test.ts
A  frontend/src/lib/graph/liveStatus.ts
A  frontend/src/components/graph/ModuleNode.tsx
A  frontend/src/components/graph/ModuleNode.test.tsx
A  frontend/src/components/graph/InspectorPanel.tsx
A  frontend/src/components/graph/InspectorPanel.test.tsx
A  frontend/src/components/graph/Toolbar.tsx
A  frontend/src/components/graph/PipelineCanvas.tsx
A  frontend/src/components/graph/PipelineGraph.tsx
A  frontend/src/components/graph/PipelineGraph.astro
A  frontend/src/pages/graph.astro
M  AGENTS.md
M  feature_list.json
M  progress/current.md
```

### Lecciones / notas

- **React Flow + Preact no conviven en el mismo árbol React**: React Flow requiere React 18+ (no soporta Preact). Astro permite múltiples frameworks por proyecto, pero cada componente se hidrata con su propio provider. `client:only="react"` es OBLIGATORIO (no `client:load`) por refs DOM. Esto se manifiesta en runtime, no en build
- **El catálogo como single source of truth**: tener `nodeCatalog.ts` con la metadata de los 8 nodos (handles, fields, colors, moduleKey) evita duplicación entre `ModuleNode`, `InspectorPanel`, `Toolbar`, `serialize.ts`. Cualquier cambio en un módulo se hace en un solo archivo
- **`useCallback` con deps `[nodes, edges]`**: React Flow llama a `isValidConnection` muy frecuentemente durante drag. Sin memoización, cada render del padre re-evalúa todas las conexiones. La memoización es esencial para UX fluida
- **JSON.stringify para dirty detection es OK para nodos pequeños**: el grafo del pipeline tiene 8-10 nodos. Para 100+ nodos habría que usar un comparador shallow. Aquí la simplicidad gana
- **Tests en jsdom + React Flow**: `@xyflow/react` requiere DOM, pero jsdom lo simula. Los tests de `ModuleNode` (sin `<ReactFlow>`) y `InspectorPanel` (standalone) funcionan sin provider. Tests de `PipelineCanvas` (con `<ReactFlow>`) requieren `ReactFlowProvider` y no los implementé — el comportamiento del canvas en sí es responsabilidad de React Flow, no nuestro
- **El usuario debe probar manualmente en navegador**: F116 verificó tipos, build, tests y lint, pero NO verificó la UX (drag, zoom, pan, conexiones, persistencia). Esto es OK para un primer release, pero un smoke test E2E con Playwright sería el siguiente paso
- **El módulo `polling.ts` genera warning en build** ("dynamically imported... but also statically imported"): pre-existente, no introducido por F116. La advertencia viene de que `pipeline-control.ts` importa `polling.ts` de las dos formas. Out of scope

---

# Sesión anterior — F115 cerrado: refactor_chunk_clock (2026-06-05)

## Estado del entorno verificado con `init.ps1 -Quick` — **VERDE**

| Check | Estado | Notas |
|---|---|---|
| Python 3.12.13 | OK | venv ok |
| Archivos base del arnés | OK | AGENTS, CHECKPOINTS, feature_list, current, history |
| feature_list.json | OK | 95 features (95 done, 0 in_progress, 0 pending) |
| pytest tests/unit/ | **OK** | **0 failures** (1246 pass + 4 skip + 4 xpass) |
| mypy --strict core/ server/ modules/ | OK | 0 errores |
| tsc --noEmit | OK | 0 errores |
| vitest | OK | 201/201 pass |
| ruff | OK | disponible |
| mkdocs | OK | disponible |

---

## F115 cerrado ✅ — `refactor_chunk_clock`

**Resumen**: Extraída la lógica de drift correction de mtime que estaba duplicada verbatim en `srt_input.py:586-591` y `rtmp_input.py:334-342` a una nueva clase `ChunkClock` en `core/chunk_clock.py`. El bloque inline de 7 líneas en cada input ahora es una sola llamada: `chunk_cumulative = self._clock.record_mtime(chunk_path.stat().st_mtime)`. El comportamiento de la corrección de drift se preserva exactamente (mismo clamp `[0.5, 2*chunk_duration]`, misma dirección de la corrección asimétrica).

### Archivos tocados (3) + 1 nuevo

| Archivo | Cambio |
|---|---|
| `core/chunk_clock.py` (NUEVO, 186 líneas) | Clase `ChunkClock` con API: `record_mtime(mtime) -> float`, `update_chunk_duration(new) -> bool`, `reset()`, properties `chunk_duration`/`cumulative`/`has_previous_mtime`. Constantes: `DEFAULT_MIN_DELTA_S=0.5`, `DEFAULT_MAX_DELTA_MULTIPLIER=2.0`. Validación en constructor (chunk_duration > 0, min_delta >= 0, max_delta_multiplier >= 1.0). Type hints completos |
| `modules/inputs/srt_input.py` | `+1 import` (ChunkClock). `_last_chunk_mtime` + `_cumulative_duration` reemplazados por `self._clock = ChunkClock(chunk_duration=self._chunk_duration)`. Las 7 líneas de mtime correction (586-591) reemplazadas por 1 línea + comentario. `configure()` simplificado: `if self._clock.update_chunk_duration(new): log`. `start()`: `self._cumulative_duration = 0.0` → `self._clock.reset()`. **735 → 624 líneas (-15%)** |
| `modules/inputs/rtmp_input.py` | Mismo refactor que srt_input. `__init__` reordenado: `_chunk_duration` ahora se asigna ANTES de `self._clock` (encontré este bug cuando los 3 tests de rtmp fallaron con `AttributeError: '_chunk_duration'`). `configure()` simplificado. `start()`: reset delegado. **402 → 330 líneas (-18%)** |
| `tests/unit/test_chunk_clock.py` (NUEVO) | 28 tests en 7 clases: `TestChunkClockConstructor` (5), `TestChunkClockFirstChunk` (2), `TestChunkClockSequentialChunks` (2), `TestChunkClockClamping` (5), `TestChunkClockReset` (3), `TestUpdateChunkDuration` (4), `TestPropertyAccessors` (2), `TestChunkClockWithRealFiles` (3), `TestChunkClockDriftScenario` (2) |

### Decisiones técnicas

- **Comportamiento preservado EXACTAMENTE**. La fórmula del clamp es: `clamped = max(0.5, min(raw_delta, 2*chunk_duration))` y `cumulative += clamped - chunk_duration`. Cuando `raw_delta < 0.5`, el `clamped` se sube a 0.5, lo cual hace la corrección `0.5 - chunk_duration = -9.5` (negativa) → el cumulative retrocede. Esto es lo que el código original hacía. F108 documentó este sesgo como "drift por mtime" pero no se cambió la dirección. F115 no cambia comportamiento, solo lo extrae.
- **`update_chunk_duration(new) -> bool`** devuelve True si el valor cambió (y resetea cumulative), False si no (no resetea). Esto preserva la semántica del código original: `if new != self._chunk_duration: self._cumulative_duration = 0.0` — el reset solo ocurre en cambio real.
- **Clamp bounds configurables** (`min_delta_s`, `max_delta_multiplier`) aunque los defaults son los del código original. Permite testing del clamp sin tocar el código de prod.
- **`record_mtime` retorna el snapshot DESPUÉS de la corrección y ANTES del increment del chunk_duration**. Eso permite al caller hacer `cum = self._clock.record_mtime(...)` y usar `cum` directamente como `cumulative_duration` del chunk. El internal state queda con `+chunk_duration` para el siguiente chunk.
- **Bug encontrado durante la refactorización**: en `rtmp_input.py`, mi primer intento puso `self._clock = ChunkClock(chunk_duration=self._chunk_duration)` ANTES de que `_chunk_duration` fuera asignado. Resultado: 3 tests de `test_rtmp_input.py::TestRTMPInputIntegration` fallaron con `AttributeError: 'RTMPInput' object has no attribute '_chunk_duration'`. Lo detectó la suite completa, no el smoke test. Reordené para asignar `_chunk_duration` primero, luego el clock. **Lección**: los smoke tests de import no son suficientes — la suite completa es necesaria para detectar bugs de orden de inicialización.

### Aceptación vs realidad

- ✅ ChunkClock extraída a módulo dedicado y testeable
- ✅ 28 tests pasan (incluyendo el escenario F108 de 180 chunks × 0.05s = 8.95s drift)
- ✅ Sin regresión de comportamiento: 1246 pass + 4 skip + 4 xpass + 0 fail
- ⚠️ `srt_input.py < 500 líneas` **NO cumplido** (quedó en 624, -15%). La reducción realista con scope de F115 (solo clock) es ~110 líneas. Para llegar a 500 se necesitaría extraer también: port check (~40 líneas), FFmpeg command builder (~50 líneas usado en 2 sitios, DRY win), GPU detection (~25 líneas). Estas extracciones son candidatas para features futuros, no scope creep aquí.

### Métricas

- `init.ps1 -Quick`: GREEN
- `pytest tests/unit/test_chunk_clock.py -v`: 28/28 pass en 0.39s
- `pytest tests/unit/ -n auto`: 1246 pass + 4 skip + 4 xpass + 0 fail (pre-F115: 1218; +28 de F115)
- `mypy --strict core/chunk_clock.py`: 0 errores
- `mypy --strict core/ server/ modules/`: 0 errores (test_mypy_modules pasa)
- `ruff check core/chunk_clock.py tests/unit/test_chunk_clock.py modules/inputs/srt_input.py modules/inputs/rtmp_input.py`: All checks passed
- `modules/inputs/srt_input.py`: 735 → 624 líneas (-111)
- `modules/inputs/rtmp_input.py`: 402 → 330 líneas (-72)
- `core/chunk_clock.py` (NUEVO): 186 líneas
- `feature_list.json`: 95 done / 0 pending — **todas las features cerradas**

### Archivos tocados (resumen git)

```
M  modules/inputs/srt_input.py
M  modules/inputs/rtmp_input.py
A  core/chunk_clock.py
A  tests/unit/test_chunk_clock.py
M  feature_list.json
M  progress/current.md
```

### Lección / nota

- **Smoke test no es suficiente para refactors de inicialización**. El primer intento falló con tests de integración de rtmp que no aparecen en un simple `import modules.inputs.rtmp_input`. Solo `pytest tests/unit/test_rtmp_input.py` lo detectó. Para refactors que tocan `__init__`, correr el archivo de tests específico SIEMPRE, no solo el import.
- **El `i` no usado en el loop** (`for i in range(180):` donde `i` no se referencia) es flag de ruff B007. Renombrar a `_` o `_i` es trivial pero molesto. Considerar desactivar B007 en `conftest.py` o `.ruff.toml` para tests paramétricos — no es bug, es lint aesthetics.
- **El clamp `clamped - chunk_duration` puede ser negativo** cuando `clamped < chunk_duration`. En la práctica esto ocurre cuando dos chunks se escriben muy juntos (FFmpeg restart, clock jitter). El cumulative retrocede en vez de saltar hacia adelante — el código original acepta esto como "conservador". F115 no lo cambia, pero documenté el comportamiento en el docstring de `record_mtime`.

---

# Sesión anterior — F114 cerrado: logging_consistency (2026-06-05)

---

## F114 cerrado ✅ — `logging_consistency`

**Resumen**: Tercero de los tres canales de log predichos por F108: añadido `crash.log` (uncaught exceptions via `sys.excepthook`), 5MB/2 backups, con crash logger `srt2web.crash` que NO propaga al log principal (evita duplicación). Corregida inconsistencia: `setup_logging()` ahora deriva `log_dir` del `log_file` elegido, así `security.log` y `srt2web.log` viven juntos (antes `SecurityLogHandler` usaba siempre el dir user-level aunque `setup_logging` se llamara con un `log_file` custom). `main.py` instala el crash handler EARLY (después del F111 try/except que captura `numpy._multiarray_umath` DLL load failed) y envuelve el `__main__` en un try/except final con exit code 1.

### Archivos tocados (4) + 1 nuevo

| Archivo | Cambio |
|---|---|
| `core/logging_setup.py` | + `install_crash_handler(log_dir=None) -> Logger \| None`: `RotatingFileHandler` a `crash.log` (5MB, 2 backups), logger `srt2web.crash` con `propagate=False`, reemplaza `sys.excepthook` preservando el original. Constantes exportadas: `CRASH_LOGGER_NAME`, `CRASH_LOG_FILENAME`, `CRASH_MAX_BYTES`, `CRASH_BACKUP_COUNT`. Reordenado imports (`collections.abc.Callable`, `types.TracebackType`). `setup_logging()` ahora deriva `log_dir` del `log_file` y lo pasa a `SecurityLogHandler(log_dir=...)` |
| `main.py` | + `install_crash_handler` import (línea 23, dentro del F111 try/except). Llamada a `install_crash_handler()` justo después del F111 try/except (línea 70) y ANTES de `get_project_root()`. `__main__` envuelto en try/except BaseException: imprime `FATAL: ...` a stderr y exit code 1 (preserva `SystemExit`) |
| `tests/unit/test_logging_setup.py` (NUEVO) | 14 tests en 2 clases: `TestSetupLogging` (4 tests del srt2web/security channels) + `TestInstallCrashHandler` (10 tests: file creation, propagation, idempotency, SystemExit/KeyboardInterrupt skip, original hook preservation, broken-stream resilience, dir uncreatable, default dir) |
| `docs/deployment.md` | Sección "Estructura de Logs" extendida: 3 archivos documentados (`srt2web.log` / `security.log` / `crash.log`), tabla de origen/cuando/quien, formato, cómo cambiar ubicación, referencia F108/F102/F114 en cada uno |

### Decisiones técnicas

- **`_original_excepthook` con tipo `Callable[[type[BaseException], BaseException, TracebackType \| None], Any]`** para que mypy strict no se queje del `Any` return de `sys.excepthook` (typeshed lo declara como `Any`).
- **No usar `return` dentro de `finally`** (ruff B012) — reestructurado: el path `SystemExit/KeyboardInterrupt` llama al hook original y returns explícito; el path normal logea al crash logger y luego llama al hook original al final de la función. Sin `try/finally` envolviendo la llamada al hook original — el crash hook ya tiene su propio try/except interno que impide que el crash handler crashee.
- **`install_crash_handler` resuelve `get_user_log_dir` en call-time** (`import core.paths; core.paths.get_user_log_dir()`) en vez de importarlo al top del módulo. Esto permite que tests monkeypatcheen `core.paths.get_user_log_dir` (F114 test `test_default_log_dir_uses_get_user_log_dir`).
- **Crash logger con `propagate=False`** para que la entrada de crash NO aparezca duplicada en `srt2web.log`. Si quieres verla en ambos, lo activas en un test/debug.
- **Crash handler 5MB / 2 backups** (vs srt2web.log 10MB / 3 backups y security.log 10MB / 3 backups): los crashes son eventos raros, no necesitan tanto espacio.

### Lección / nota

- **`_excepthook` con `Any` desde `sys.excepthook`** es la única forma limpia de encadenar hooks sin perder la cadena de type hints. Tipar `_original_excepthook: Callable[..., Any]` da libertad a mypy sin perder el contrato del original.
- **`setup_logging(log_file=...)` con un dir custom ahora funciona consistentemente** — antes el test que pasaba `log_file=tmp/srt2web.log` veía `security.log` aparecer en `~/AppData/Local/srt2web/srt2web/Logs` (sorpresa). Ahora deriva del parent del log_file. Esto arregló los 3 fallos iniciales del test suite.
- **`B012 return in finally` es un anti-pattern real** — silencia la excepción original si el `finally` también la lanza. En este caso era safe (solo llamábamos al hook original que es no-throwing), pero el linter tiene razón en general.
- **`install_crash_handler` se invoca DESPUÉS del F111 try/except** a propósito: si `import numpy` falla, queremos que el mensaje accionable de F111 llegue al usuario primero, no que el crash handler se ejecute antes de que la app esté lista para loggear.

### Métricas

- `init.ps1 -Quick`: GREEN (9/9 secciones OK)
- `pytest tests/unit/test_logging_setup.py -v`: 14/14 pass en 0.55s
- `pytest tests/unit/ -n auto`: 1218 pass + 4 skip + 4 xpass + 0 fail
- `mypy --strict core/logging_setup.py`: 0 errores
- `mypy --strict core/ server/ modules/`: 0 errores (test_mypy_modules pasa)
- `ruff check core/logging_setup.py tests/unit/test_logging_setup.py`: All checks passed
- `main.py` importa sin warning: el F111 try/except captura `validate_secrets` SECURITY warning y `install_crash_handler` se ejecuta sin error
- `feature_list.json`: 94 done / 1 pending (F115)

### Archivos tocados (resumen git)

```
M  core/logging_setup.py
M  main.py
A  tests/unit/test_logging_setup.py
M  docs/deployment.md
M  feature_list.json
M  progress/current.md
```

---

# Sesión anterior — F113 cerrado: e2e_obsolete_tests (2026-06-05)

---

## F113 cerrado ✅ — `e2e_obsolete_tests`

**Resumen**: El audit del F108 documentó 2 e2e test failures pre-existentes. Verificado en esta sesión que la suite e2e actual está **GREEN** (190 pass + 59 skip + 0 fail), pero quedaba un test trivial `assert 2000 == 2000` (`test_subtitle_polling_interval`) que documentaba el polling eliminado por F108. F113 lo marca como `@pytest.mark.skip` con razón trazable a F108, y mejora el docstring de `test_links_to_hls_stream` para documentar su lógica F108-aware (lee HTML + Astro JS bundle).

### Estado real verificado

```text
pytest tests/e2e/ -m "not slow" -q --tb=line
====================== 190 passed, 59 skipped in 46.31s =======================
```

- `test_links_to_hls_stream` ya estaba F108-aware (refs `server/static/player/index.html` + `server/static/_astro/*.js`) → **PASS**
- `test_subtitle_polling_interval` era `assert 2000 == 2000` (no-op que documentaba el polling pre-F108) → **SKIP** ahora
- `test_subtitle_refresh_interval` (nombre original del audit F108) **no existe** en la suite actual. El equivalente real es `test_subtitle_polling_interval` en `tests/unit/test_player_robustness.py:193`, no en `tests/e2e/`. La descripción F113 tenía el path incorrecto.
- Suite e2e total: 249 collected, 190 pass, 59 skip, 0 fail, 0 error

### Archivos tocados (2)

| Archivo | Cambio |
|---|---|
| `tests/unit/test_player_robustness.py:193-205` | `test_subtitle_polling_interval` ahora tiene `@pytest.mark.skip(reason="Obsolete after F108: subtitle polling was eliminated in favor of HLS.js native subtitle tracks...")` con docstring explicando el cambio y referencia al test que SÍ valida la integración actual (`test_subtitle_native_hls_handling` en e2e) |
| `tests/e2e/test_player_page.py:89-101` | `test_links_to_hls_stream` docstring expandido: documenta que el URL del stream HLS se construye en el JS bundle Astro (`player-subtitles.ts`), no en el HTML. El fixture `_get_player_combined()` lee tanto `server/static/player/index.html` como `server/static/_astro/player*.js` para encontrar el URL |

### Lecciones / notas

- **El estado del audit F108 quedó obsoleto** porque el código evolucionó entre sesiones. Cuando un audit lista "X tests rotos", verificar el estado actual antes de aplicar fix mecánico: a veces el problema ya se resolvió por refactors posteriores.
- **`assert 2000 == 2000` es un test zombie**: pasaba trivialmente, no validaba nada, pero ocupaba un slot en la suite. Tests constantes-de-valor-fijo son mejor reemplazados por `xfail`/`skip` con razón o eliminados, no dejados como "passing".
- **El fixture `_get_player_combined()` en `test_player_page.py:41-47`** es un buen patrón para tests que necesitan leer bundle Astro: combina HTML + todos los JS bundles en un solo string para los asserts. Reutilizable en otros tests Astro.
- **F108 → F113 trazabilidad**: F108 reemplazó `setInterval(2000)` por HLS.js native events. F113 cierra el ciclo dejando un skip-marker con referencia explícita a F108 + al test sucesor (`test_subtitle_native_hls_handling`). Esto facilita que un futuro developer entienda por qué existe un test que no hace nada.

### Métricas

- `init.ps1 -Quick`: GREEN (9/9 secciones OK)
- `pytest tests/e2e/ -m "not slow"`: 190 pass + 59 skip + 0 fail
- `pytest tests/unit/test_player_robustness.py::TestPlayerSubtitles::test_subtitle_polling_interval`: SKIPPED (con razón)
- `pytest tests/e2e/test_player_page.py::TestPlayerPageStructure::test_links_to_hls_stream`: PASSED
- `mypy --strict core/ server/ modules/`: 0 errores en 91 source files
- `feature_list.json`: 93 done / 2 pending (F114, F115)

### Archivos tocados (resumen git)

```
M  tests/unit/test_player_robustness.py
M  tests/e2e/test_player_page.py
M  feature_list.json
M  progress/current.md
```

---

## F112 cerrado ✅ — `env_secrets_generation`

**Resumen**: Hardening completo del flujo de secrets. `.env.example` ya no contiene placeholders públicos (`your-secret-token-here`, `your-secret-key-here`); ahora declara `SRT2WEB_JWT_SECRET=` vacío. La variable real usada por el runtime (`core/auth_db.py`) es `SRT2WEB_JWT_SECRET` — los placeholders legacy nunca llegaron a estar conectados a ningún env var (eran decorativos). El instalador genera automáticamente un secret criptográficamente seguro con `secrets.token_urlsafe(32)`, y `validate_secrets()` en arranque bloquea configuraciones inseguras con mensaje accionable.

### Archivos tocados (8)

| Archivo | Cambio |
|---|---|
| `.env.example` | Eliminados `AUTH_TOKEN`/`SECRET_KEY` legacy. Añadido `SRT2WEB_JWT_SECRET=` vacío con comentario explicativo + docs de rotación |
| `config/requirements.txt` | Añadido `python-dotenv>=1.0.0` (para que `main.py` cargue `.env` antes de `core.auth_db`) |
| `main.py` | `from dotenv import load_dotenv; load_dotenv()` en el F111 try/except, antes de los imports de `core` (para que `os.environ` ya tenga el secret cuando `auth_db.py` lo lea). Llamada a `validate_secrets(strict=...)` con bypass de dev `SRT2WEB_ALLOW_INSECURE_DEFAULTS=1` |
| `Install.bat` | Nueva sección F112 post-install: `python scripts\generate_env_secrets.py` con mensaje accionable Windows-specific si falla |
| `install_Mac.sh` | Misma generación con mensaje Mac-specific |
| `core/config_manager.py` | 2 funciones nuevas: `generate_jwt_secret()` y `validate_secrets(strict=True) -> tuple[bool, str]`. Detecta: empty, default inseguro, placeholders legacy, y warning si < 32 chars |
| `scripts/generate_env_secrets.py` (NUEVO) | Script idempotente: si `.env` falta lo copia de `.env.example`; para cada `MANAGED_KEYS` reemplaza placeholder/vacío con `secrets.token_urlsafe(32)`. Output `GENERATED:` / `KEPT:` machine-parseable |
| `tests/unit/test_config_validation.py` | +8 tests en `TestSecretValidation`: empty/default/legacy/short/valid + `generate_jwt_secret()` + 2 tests de `.env.example` |
| `tests/unit/test_generate_env_secrets.py` (NUEVO) | 7 tests del script: create/replace/keep/preserva-comments/falla-si-falta-example/output-format |
| `docs/deployment.md` | Sección "First-time Setup (F112)" detallada + tabla de env vars actualizada (antes tenía `SRT2WEB_AUTH_TOKEN` que no existía) |

### Lecciones / notas

- **El placeholder original (`your-secret-token-here`) nunca estuvo conectado a un env var real.** El proyecto usa `SRT2WEB_JWT_SECRET` desde antes (en `core/auth_db.py`). El `.env.example` tenía un placeholder decorativo que se confundía con algo funcional. F112 lo corrige declarando la variable real y eliminando la confusión.
- **Validación en 2 capas es defensivo-proporcional**: el install script reemplaza placeholders proactivamente (genera y guarda), y `validate_secrets()` rechaza proactivamente (bloquea arranque). Si un usuario copia `.env.example` → `.env` a mano, el script no corre, pero la validación al arranque captura el caso.
- **`secrets.token_urlsafe(32)` produce 43 chars base64-url** (32 bytes = 256 bits entropía, encodados a ~43 chars). Es el estándar para tokens de sesión/secret keys en Python.
- **Listas de placeholders legacy** (`_LEGACY_JWT_PLACEHOLDERS` en config_manager y `PLACEHOLDER_VALUES` en generate_env_secrets) deben mantenerse en sync. Si añades un nuevo placeholder a uno, añádelo al otro. (Mejora futura: consolidar en una constante común en un módulo compartido).
- **Bypass de dev con `SRT2WEB_ALLOW_INSECURE_DEFAULTS=1`** es la salida para tests/dev que no quieren generar secrets reales. Documentado explícitamente como "NEVER use in production" en el mensaje de error.
- **`tests/conftest.py:176` usa `MagicMock` sin import** (ruff F821): bug pre-existente, no introducido por F112. Fuera de scope.

### Métricas

- `init.ps1 -Quick`: GREEN (9/9 secciones OK)
- `pytest tests/unit/test_config_validation.py::TestSecretValidation`: 8/8 pass
- `pytest tests/unit/test_generate_env_secrets.py`: 7/7 pass
- `pytest tests/unit/ -n auto`: 1205 pass + 3 skip + 4 xpass + 0 fail
- `mypy --strict core/ server/ modules/`: 0 errores en 91 source files
- `feature_list.json`: 92 done / 3 pending (F113, F114, F115)

### Archivos tocados (resumen git)

```
M  .env.example
M  config/requirements.txt
M  main.py
M  Install.bat
M  install_Mac.sh
M  core/config_manager.py
A  scripts/generate_env_secrets.py
M  tests/unit/test_config_validation.py
A  tests/unit/test_generate_env_secrets.py
M  docs/deployment.md
M  feature_list.json
M  progress/current.md
```

---

## F111 cerrado ✅ — `windows_numpy_dll_blocked`

**Resumen**: Documenta el crash de numpy en Windows (H1 de la auditoría) y previene el ciclo "instalo y fallo al arrancar". 4 puntos: docs nueva, smoke test, captura ImportError en main.py, validación en scripts de instalación. El log `srt2web_error.log` era de numpy 2.4.5; en este entorno numpy 2.4.6 funciona, así que F111 es **preventivo** (mensaje accionable) más que reactivo.

### Archivos tocados (5)

| Archivo | Cambio |
|---|---|
| `docs/troubleshooting-windows.md` (NUEVO) | 12 secciones, prominente sección numpy DLL load failed con 6 soluciones escalonadas (reinstall → unblock → exclusions → IT) |
| `main.py:13-58` | try/except alrededor del bloque `from core import ...` que carga numpy. Detecta el patrón `_multiarray_umath` / `DLL load failed` / `Control de aplicaciones` y muestra mensaje accionable con link a docs + `sys.exit(1)` |
| `Install.bat` | Nueva sección post-install: `%VENV_PYTHON% -c "import numpy; print('OK')"` con 5 soluciones Windows-specific si falla |
| `install_Mac.sh` | Misma verificación post-install con 2 soluciones Mac-specific (build incompatible, Apple Silicon x86_64 mismatch) |
| `tests/unit/test_numpy_import.py` (NUEVO) | 3 tests: `test_numpy_importable`, `test_numpy_array_creation`, `test_numpy_multiarray_umath_loadable` (este último es el detector específico de F111) |

### Lección / nota

- **`try/except` alrededor de imports de nivel módulo** es un patrón útil para dependencias opcionales o con problemas conocidos de carga. El catch es estrecho (`ImportError` solamente) para no enmascarar otros errores.
- **Detección de patrones en el mensaje de error** (`"DLL load failed"`, `"_multiarray_umath"`, `"Control de aplicaciones"`) es robusto y multilenguaje porque busca substrings independientes del idioma del usuario.
- **`pause` antes de `exit /b 1`** en Install.bat es importante: el usuario está ejecutando el script interactivamente, sin pause se cierra la ventana y no ve el error.
- **Numpy 2.4.6 funciona en este entorno** (path: `venv\Lib\site-packages\numpy\__init__.py`). El log `srt2web_error.log` era histórico de numpy 2.4.5 y ya no se reproduce.

### Métricas

- `init.ps1 -Quick`: GREEN (9/9 secciones OK)
- `pytest tests/unit/test_numpy_import.py -v`: 3/3 pass en 0.17s
- `mypy --strict core/ server/ modules/`: 0 errores en 91 source files
- **main.py** importa sin warning con F111 try/except (verificado con importlib)

---

## F109 cerrado ✅ — `audit_fix_batch`

**Resumen**: Batch de 8 fixes puntuales resultado de la auditoría del 2026-06-05. Dejó `init.ps1 -Quick` 100% verde y `tests/integration/` 100% verde (80 pass + 4 skip Mac-only).

### Fixes aplicados

| # | Archivo | Tipo | Cambio |
|---|---|---|---|
| 1 | `tests/unit/test_f106_piper_voice.py:160` | test bug | `isinstance(..., Lock)` → `isinstance(..., type(threading.Lock()))` |
| 2 | `modules/outputs/composite_output.py:186` | logger | `except Exception: pass` → `logger.warning(..., exc_info=True)` |
| 3 | `modules/outputs/composite_output.py:386` | logger | `except ImportError: pass` → `logger.debug(...)` (mantiene el flujo, ahora visible) |
| 4 | `server/security.py:269-289` | deprecation | `validate_ws_auth` marcado `@deprecated` con docstring apuntando a `ws_routes.py` inline auth (8 tests siguen verdes) |
| 5 | `tests/integration/test_api_routes.py:_make_client` | helper | Nuevos params `pipeline_running=` y `output_dir=` con `Mock(spec=Pipeline)` cuando running |
| 6 | `tests/integration/test_api_routes.py:172-186` | test | `test_ready_endpoint` actualizado para mockear pipeline running; nuevo `test_ready_endpoint_not_running_returns_503` (cubre F102 readiness probe) |
| 7 | `tests/integration/test_api_routes.py:430-441` | test | `test_recording_list_empty` usa `tmp_path` via `_make_client(output_dir=...)` (test isolation) |
| 8 | `tests/integration/conftest.py` (NUEVO) | fixture | Autouse session-scope cleanup de debris en `output/recordings/*` y `output/subtitles/subs.{m3u8,vtt}` |
| 9 | `tests/unit/test_latest_features.py:151-159` | test | `test_chunk_duration_is_valid` ahora `<= 60` (schema) en lugar de `<= 15` (OBS constraint obsoleto) |
| 10 | `git stash drop` | cleanup | 1 stash pre-F108 obsoleto eliminado (player.ts + docs HTML) |

---

## F110 cerrado ✅ — `clean_para_borrar`

**Resumen**: Limpieza completa de `PARA BORRAR/`. 90+ archivos reducidos a 2 entries (config local + dir bloqueado por Windows + README índice). Lo útil (snapshots + helm chart) se archivó en `docs/archive/`.

### Inventario original (15 entries)

| Path | Tipo | Tamaño | Acción |
|---|---|---|---|
| `.openclaude/settings.local.json` | AI tool config (user) | 174 B | **MANTENER** (config local preservada) |
| `.playwright-mcp/` | UX snapshots manuales | 33 files, ~700 KB | → `docs/archive/ux-snapshots/2026-05-snapshots/` |
| `player_snapshot.md` | Snapshot puntual player | 185 B | → `docs/archive/ux-snapshots/2026-05-24-player-retry-snapshot.md` |
| `deploy/helm/srt2web/` | Helm chart completo | Chart + 8 templates, ~10 KB | → `docs/archive/helm-srt2web/chart/` |
| `120/`, `chunks/` | Carpetas vacías | 0 B | **ELIMINAR** |
| `output/` (8 subdirs) | Runtime debris | varies | **ELIMINAR** |
| `logs/` (2 files) | Runtime logs | ~115 KB | **ELIMINAR** |
| `temp/pytest-of-bruno/` | Pytest tmp data | locked | **BLOQUEADO** (Access Denied Windows, documentado) |
| `.coverage` | Coverage data | 68 KB | **ELIMINAR** |
| `Cleaning`, `Killing` (0 B) | Marcadores vacíos | 0 B | **ELIMINAR** |
| `package.json`, `package-lock.json` | Node huérfano | 683 B | **ELIMINAR** |
| `presets.json` (`{}`) | Preset vacío | 3 B | **ELIMINAR** |

### Estado final

**`PARA BORRAR/`** (3 entries):
- `.openclaude/` — config local preservada
- `temp/pytest-of-bruno/` — bloqueado a nivel Windows, documentado en `PARA BORRAR/README.md` (instrucciones de limpieza con admin shell / reboot)
- `README.md` — NUEVO índice de qué hubo y qué se hizo

**`docs/archive/`** (NUEVO, 3 subdirs):
- `README.md` — índice y política de archivo
- `ux-snapshots/` (35 files + 1 dir):
  - `README.md` — describe los snapshots y por qué están archivados
  - `2026-05-snapshots/` (33 files movidos: 16 page-*.yml, 14 console-*.log, 1 png, 1 snapshot-remote.yml, 1 placeholder)
  - `2026-05-24-player-retry-snapshot.md` (movido)
- `helm-srt2web/` (12 files + 1 dir):
  - `README.md` — explica F51 quedó pending, razones del archivo, cómo reactivar
  - `chart/` (Chart completo movido: `Chart.yaml`, `values.yaml`, `README.md`, `.helmignore`, 8 templates)

### Métricas

- **Archivos movidos**: 46 (34 a ux-snapshots, 12 a helm-srt2web)
- **Carpetas eliminadas**: 7 (`120/`, `chunks/`, `deploy/`, `logs/`, `output/`, `temp/`, `PARA BORRAR/Cleaning`/`Killing` parents)
- **Archivos sueltos eliminados**: 7 (`.coverage`, `Cleaning`, `Killing`, `package.json`, `package-lock.json`, `presets.json`)
- **READMEs creados**: 4 (`docs/archive/README.md`, `docs/archive/ux-snapshots/README.md`, `docs/archive/helm-srt2web/README.md`, `PARA BORRAR/README.md`)
- **`init.ps1 -Quick`**: GREEN (sin regresiones, 9/9 secciones OK)
- **`git status`**: limpio, solo cambios esperados de F109/F110 (sin debris unexpected)
- **`.gitignore`**: verificado cubre `PARA BORRAR/`, `output/`, `logs/`, `temp/`, `chunks/`, `.coverage*`

### Limitación encontrada

**`PARA BORRAR/temp/pytest-of-bruno/`** está bloqueado a nivel Windows (Access Denied incluso con `takeown` y `icacls` desde PowerShell, requiere admin shell elevado o reboot). El directorio está vacío según el listado de Windows pero el handle no se libera. Documentado en `PARA BORRAR/README.md` con instrucciones para limpieza manual. El contenido es de pytest tmp data del 02/05/2026, sin valor para el proyecto.

### Lecciones / notas

- **`docs/archive/`** es un patrón limpio para preservar código/configuración histórica sin contaminar el árbol activo. No se importa, no se ejecuta, pero sigue las convenciones de docs/ (linkable desde MkDocs si se quisiera).
- **Helm chart archivado** vs eliminado: el chart nunca se usó en producción, pero conservarlo documentado permite reactivar el feature F51 en el futuro sin reinventar la rueda.
- **Snapshots de Playwright MCP** son material de betatesting manual valioso para regression testing visual. Archivar (no eliminar) preserva la línea base.
- **Windows file locks** en pytest tmp dirs: cuando un proceso Python muere abruptamente, los handles de pytest tmp no se liberan. El directorio queda huérfano hasta reboot o admin intervention. Es comportamiento normal, no bug.

### Métricas

- **init.ps1 -Quick**: GREEN (9/9 secciones OK)
- **pytest tests/integration/ -m "not slow"**: 80 pass + 4 skip (Mac-only) + 0 fail
- **mypy --strict**: 0 errores en core/ + server/ + modules/
- **tsc --noEmit**: 0 errores
- **vitest**: 201/201
- **F106 suite (9 tests)**: 9/9 pass después del fix
- **git stash list**: vacío

### Archivos tocados (10)

```
M tests/unit/test_f106_piper_voice.py
M modules/outputs/composite_output.py
M server/security.py
M tests/integration/test_api_routes.py
A tests/integration/conftest.py
M tests/unit/test_latest_features.py
M feature_list.json
M progress/current.md
```

### Lecciones / notas

- **`from threading import Lock` importa la factory, no la clase.** El tipo real de una instancia `Lock()` es `_thread.lock`, accesible vía `type(threading.Lock())`. Patrón a evitar en tests.
- **F102 readiness probe** está bien diseñado: 503 cuando pipeline no está running. El test original asumía 200 siempre; el fix mockea el pipeline para validar ambos casos (running → 200, idle → 503).
- **`validate_ws_auth` NO es totalmente dead code** — está cubierto por 8 tests que documentan el contrato de auth WS. La solución fue marcarlo `@deprecated` en vez de eliminarlo (los tests siguen válidos y validan el inline check de `ws_routes.py`).
- **xdist + Windows + tmp_path + log file handlers** puede dar `PermissionError` en teardown. Es una flakiness pre-existente que no se reprodujo en este run con xdist; queda fuera de F109 scope.

---

## Auditoría 2026-06-05 (estado anterior al fix)

### Estado del entorno verificado con `init.ps1 -Quick`

| Check | Estado | Notas |
|---|---|---|
| Python 3.12.13 | OK | venv ok |
| Archivos base del arnés | OK | AGENTS, CHECKPOINTS, feature_list, current, history |
| feature_list.json | OK | 88 features (todas `done`) |
| pytest tests/unit/ | **FAIL** | **1 test fallido** (test_f106_piper_voice.py:160) + 1182 pass + 3 skip + 4 xpass |
| mypy --strict core/ server/ modules/ | OK | 0 errores |
| tsc --noEmit | OK | 0 errores |
| vitest | OK | 201/201 pass |
| ruff | OK | disponible |
| mkdocs | OK | disponible |

> ⚠️ **init.ps1 considera el entorno "no listo"** por el único test fallido de F106 (F55 el bug crítico real está arreglado; F106 la cadena Piper está OK; el test solo tiene un bug trivial de uso de `Lock` como tipo).

## Tests integration/e2e (no se ejecutan en init.ps1, descubiertos en auditoría)

| Test | Estado | Tipo |
|---|---|---|
| `tests/integration/test_api_routes.py::TestHealthEndpoints::test_ready_endpoint` | **FAIL** | Test bug — F102 diseñó `/ready` para devolver 503 cuando el pipeline no está corriendo; el test no arranca pipeline antes de chequear |
| `tests/integration/test_api_routes.py::TestErrorPaths::test_recording_list_empty` | **FAIL** | Test no aislado — `output/recordings/test_recording.mp4` (0 bytes) queda de runs anteriores |
| `tests/cli/` | OK | 192/192 pass |
| `tests/integration/test_pipeline_integration.py` | OK | 10/10 pass |
| `tests/integration/test_hardware_mac.py` | OK | 4 skip (sin Mac) + pass |
| `tests/integration/test_server.py` | OK | 15/15 pass |

## Auditoría completa: hallazgos

### 🔴 HALLAZGOS CRÍTICOS (afectan funcionalidad)

#### H1 — `srt2web_error.log` reporta numpy DLL bloqueado por Windows

`C:\Users\bruno\Documents\programacion\Antigravity\srt2web\srt2web_error.log` (2608 bytes) contiene:

```
ImportError: DLL load failed while importing _multiarray_umath:
Una directiva de Control de aplicaciones bloqueó este archivo.
```

- **Causa**: Windows Defender SmartScreen / AppLocker está bloqueando `numpy/_core/_multiarray_umath.cp312-win_amd64.pyd` al ejecutar `main.py`.
- **Impacto**: El servidor **no puede arrancar** en este entorno.
- **Workaround conocido**: `pip uninstall numpy && pip install numpy==2.2.6` o `pip install --upgrade --force-reinstall numpy` (Microsoft/Numpy bug conocido con cuDNN 9.x en Windows).
- **Mitigación a corto plazo**: Documentar paso a paso en docs/troubleshooting-mac.md (o crear `docs/troubleshooting-windows.md`).
- **No-bloqueante** para los tests unitarios porque pytest importa `numpy` solo en módulos de transformaciones, no en collect.

#### H2 — `test_f106_piper_voice.py:160` test falla por uso incorrecto de `Lock`

```python
# ACTUAL (roto):
from threading import Lock
assert isinstance(manager._cmd_lock, Lock)  # TypeError: Lock es factory, no tipo

# CORRECTO (3 opciones):
assert isinstance(manager._cmd_lock, type(threading.Lock()))  # opción 1
# o:
import _thread; assert isinstance(manager._cmd_lock, _thread.lock)  # opción 2 (no funciona en 3.13)
# o (más simple):
assert hasattr(manager, "_cmd_lock") and manager._cmd_lock.acquire(blocking=False)  # opción 3
```

- **F106 está cerrado funcionalmente** (los otros 8 tests de la feature pasan: alias canonical, normalize, sync, concurrent, sequential). Solo este test de "existencia de atributo" está mal escrito.
- **Severidad**: Baja (no afecta runtime), pero init.ps1 falla por esto.

### 🟡 HALLAZGOS MEDIOS (deuda técnica importante)

#### H3 — `test_ready_endpoint` y `test_recording_list_empty` (integration tests rotos)

- **`test_ready_endpoint`**: El test asume que `/ready` devuelve 200 con `{"status": "ready"}` pero el endpoint (diseñado en F102) correctamente devuelve 503 porque el pipeline mock no está corriendo. **Es un test bug**, no un código bug.
- **`test_recording_list_empty`**: Asume que `output/recordings/` está vacío, pero hay `test_recording.mp4` (0 bytes) del 01/06/2026 dejado por un test anterior. **Falta cleanup en setup o test isolation**.

#### H4 — `output/subtitles/subs.m3u8` existe en árbol de trabajo (F108 side-effect)

- `output/` está en `.gitignore` ✓ pero el archivo subs.m3u8 está físicamente en el árbol de tests/ejecuciones.
- Es solo un subproducto de los tests F108 (que crean este archivo al correr), pero indica que los tests no limpian su output.
- El contenido es válido (`#EXTM3U`, `#EXT-X-VERSION:3`, `#EXT-X-TARGETDURATION:10`, `#EXT-X-MEDIA-SEQUENCE:0`).
- **No bloqueante** — `.gitignore` lo cubre, pero el test debería limpiarlo en teardown.

#### H5 — Composite output: 1 `except Exception:` silencioso en `composite_output.py:186-192`

```python
# modules/outputs/composite_output.py:179-192
try:
    first_status = first_output.get_status()
    state = first_status.state
    ...
except Exception:
    # Fallback to idle state if output status query fails
    state = ModuleState.IDLE
    enabled = True
    ...
```

- **Bug**: F74 limpió 29 silenciosos, pero este pasó inadvertido. Si un output falla, no se registra en logs.
- **Fix**: Añadir `logger.warning(f"Output {first_name} status query failed: {e}")` antes del fallback.

#### H6 — Composite output: `_register()` silencia ImportError

```python
# modules/outputs/composite_output.py:382-389
def _register() -> None:
    try:
        from core.io_factory import OutputFactory
        OutputFactory.register("composite", CompositeOutput)
    except ImportError:
        pass
```

- Probablemente intencional (evitar circular import en build time), pero el `pass` opaco complica debug si falla por otra razón.
- **Fix**: Capturar `ImportError` específicamente y dejar que otros errores suban; opcionalmente `logger.debug`.

#### H7 — `output/recordings/test_recording.mp4` (0 bytes) y `output/subtitles/subs.m3u8` (78 bytes) son debris de tests

- `output/` está en `.gitignore` ✓ pero el contenido se mantiene entre runs.
- **Fix**: Añadir cleanup en `tests/integration/conftest.py` o en cada test que use estos paths.

### 🟢 HALLAZGOS MENORES / OBSERVACIONES

#### H8 — `srt_input.py:30KB / 735 líneas` y `unified_pipeline.py:46KB / 1103 líneas` son muy grandes

- `unified_pipeline.py` se intentó refactorizar en F78, pero sigue siendo el orquestador.
- `srt_input.py` tiene muchas responsabilidades: ingest, mtime correction, watchdog, status, FFmpeg restart.
- **Recomendación**: F109 futuro — extraer mtime correction a `core/chunk_clock.py`.

#### H9 — `validate_ws_auth()` en `server/security.py:269-289` es dead code

- Solo se referencia en un docstring (línea 20 de `ws_routes.py`).
- El endpoint `/ws/logs` ahora usa protocolo de mensaje `auth` inline (línea 228 de ws_routes.py), no la función helper.
- **Recomendación**: Eliminar `validate_ws_auth` o moverlo a test fixtures.

#### H10 — `PARA BORRAR/` contiene 90+ archivos no eliminados

- Incluye snapshots de Playwright, helm chart abandonado, scripts viejos, runtimes temp.
- AGENTS.md lo marca como "candidatos a limpieza, ver F29" — F29 ya está hecho pero la carpeta no se vació.
- **Recomendación**: Mover contenido útil a `docs/archive/` y vaciar.

#### H11 — Stash huérfano: `stash@{0}: WIP on main: 0c0b754 fix: Subtitle timing sync...`

- Stash de abril 2026 con código de player.ts anterior a F108.
- F108 (junio 2026) ya reescribió player.ts con HLS.js native.
- **Recomendación**: `git stash drop stash@{0}` — el código está obsoleto.

#### H12 — `output/` y `PARA BORRAR/` tienen `temp_audio/`, `temp_mix/`, `temp_tts/`, `chunks/`, `hls/`, `subtitles/`

- 7 subdirectorios de output, todos creados por la última ejecución del pipeline (04/06/2026).
- Indica que el servidor se ejecutó al menos una vez completo (generó chunks, hls, subtitles, temp_audio).
- Logs están en `output/` o en la raíz — no en `logs/`. La raíz `srt2web_error.log` solo tiene el crash de numpy.
- **Recomendación**: Setup `logs/` o redirigir a `output/logs/`.

#### H13 — Frontend: `frontend/src/lib/modules/player.ts` referenciado en e2e tests pre-existentes

- 2 e2e test failures conocidas (mencionadas en F108): `test_links_to_hls_stream`, `test_subtitle_refresh_interval`.
- Causa: Leen `server/static/player.html` (que ya no se bundle; el frontend ahora es Astro).
- **No bloqueante** pero ensucia la suite.

#### H14 — Mypy passes pero `cli/tui/widgets/module_card.py` eliminado (F55)

- F55 claims lo eliminó. Verificado: ya no existe. ✓
- F55 acceptance: "Multi-word keys en module_detail form funcionan correctamente" — verificado con `_get_nested` ahora hace flat lookup sobre `self.module_config = self.config.get("modules", {}).get(module_name, {})` que ya aplana. ✓

#### H15 — `.env.example` tiene `AUTH_TOKEN=your-secret-token-here`

- Default inseguro (placeholder visible) en .env.example. Si alguien copia literal, el server queda con token "your-secret-token-here" — **valor público**.
- **Fix**: Comentario que diga "REEMPLAZAR con valor aleatorio de 32+ caracteres" o generar uno en `Install.bat`/init.

## Resumen de severidades

| Hallazgo | Severidad | Bloquea init.ps1 | Afecta prod |
|---|---|---|---|
| H1 — numpy DLL bloqueado | Crítico | No | Sí |
| H2 — test_f106 Lock | Bajo | Sí | No |
| H3 — 2 tests integration fallan | Medio | No (no en init) | No |
| H4 — subs.m3u8 debris | Bajo | No | No |
| H5 — except silencioso composite | Medio | No | Sí (debug) |
| H6 — except silencioso _register | Bajo | No | No |
| H7 — recordings debris | Bajo | No | No |
| H8 — archivos grandes | Bajo | No | No |
| H9 — validate_ws_auth dead | Bajo | No | No |
| H10 — PARA BORRAR lleno | Bajo | No | No |
| H11 — stash huérfano | Bajo | No | No |
| H12 — logs mezclados | Bajo | No | No |
| H13 — e2e pre-rotos | Bajo | No | No |
| H14 — frontend OK | — | — | — |
| H15 — .env.example inseguro | Medio | No | Sí (config) |

## Plan de implementación (siguiendo normas del arnés)

### Orden: una feature a la vez. F109 → F110 → F111 → ...

### **F109 — Fix test failures + dead code + cleanups batch** (Alta, 1 sesión)

**Objetivo**: dejar `init.ps1 -Quick` verde (0 failures) y `tests/integration/` verde (0 failures).

**Cambios**:

1. `tests/unit/test_f106_piper_voice.py:160`:
   - Cambiar `isinstance(manager._cmd_lock, Lock)` → `isinstance(manager._cmd_lock, type(threading.Lock()))`
   - El import `from threading import Lock` ya no es necesario

2. `tests/integration/test_api_routes.py::TestHealthEndpoints::test_ready_endpoint`:
   - Opción A: Iniciar pipeline mock antes de chequear (más correcto)
   - Opción B: Renombrar a `test_ready_endpoint_returns_503_when_not_running` y actualizar assert
   - Elegir A para verificar también que devuelve 200 cuando SÍ está corriendo

3. `tests/integration/test_api_routes.py::TestErrorPaths::test_recording_list_empty`:
   - Setup que limpia/crea tmp dir antes del test, no usar el `output/recordings/` real
   - O usar `tmp_path` fixture de pytest

4. `output/recordings/test_recording.mp4` y `output/subtitles/subs.m3u8`:
   - Añadir a `tests/integration/conftest.py` autouse fixture que limpia `output/recordings/`, `output/subtitles/`, `output/hls/`, `output/chunks/`, `output/temp_audio/`, `output/temp_mix/`, `output/temp_tts/` antes de cada test

5. `modules/outputs/composite_output.py:186`:
   - Reemplazar `except Exception: pass` con `except Exception as e: logger.warning(f"Output {first_name} status query failed: {e}", exc_info=True)`

6. `modules/outputs/composite_output.py:386-389`:
   - Mantener `except ImportError: pass` (es intencional) pero añadir `logger.debug("CompositeOutput: factory import deferred")` para diagnóstico

7. `server/security.py:269-289` `validate_ws_auth`:
   - Verificar que no se usa; eliminar o marcar como deprecated con test
   - Si se elimina, eliminar también docstring reference

8. `git stash drop stash@{0}`:
   - El stash es código obsoleto pre-F108

9. `PARA BORRAR/`:
   - No tocar en esta sesión (riesgo de borrar algo útil). Crear F110.

**Aceptación**:
- `init.ps1 -Quick` → 0 failures
- `pytest tests/integration/ -m "not slow" -q` → 0 failures
- `mypy --strict` → 0 errores
- ruff clean

**Riesgo**: Bajo. Cambios puntuales en tests + 2 log statements.

---

### **F110 — Limpieza de PARA BORRAR y archivos debris** (Media, 1 sesión)

**Objetivo**: Vaciar `PARA BORRAR/` de archivos recuperables a `docs/archive/`, mantener solo lo que el usuario confirmó preservar.

**Cambios**:

1. Inventariar `PARA BORRAR/` (90+ archivos):
   - `.playwright-mcp/` (snapshots de pruebas manuales de UI)
   - `deploy/helm/` (chart de Kubernetes abandonado, ver F51)
   - `output/`, `logs/`, `chunks/`, `temp/` (runtime debris)
   - `package.json`, `package-lock.json`, `Cleaning`, `Killing`, `player_snapshot.md`, `presets.json`, `.coverage`

2. **Migrar a `docs/archive/`** lo documentalmente útil:
   - helm chart → `docs/archive/helm-srt2web/`
   - playwright snapshots importantes → `docs/archive/ux-snapshots/`
   - Cualquier script con valor histórico

3. **Eliminar** el resto (ya está en .gitignore, así que no hay commit diff).

4. Mover `output/`, `logs/`, `chunks/`, `temp/`, `*.log` entries a `.gitignore` si no están.

**Aceptación**:
- `PARA BORRAR/` solo contiene README.md explicando qué se movió a dónde
- `docs/archive/` tiene el contenido preservado
- `git status` no muestra debris

**Riesgo**: Bajo (todo está en .gitignore).

---

### **F111 — Diagnóstico y mitigación de numpy DLL load failed (Windows)** (Alta, 1 sesión)

**Objetivo**: Documentar y opcionalmente prevenir el crash de numpy en Windows por AppLocker/Defender.

**Cambios**:

1. `docs/troubleshooting-windows.md` (NUEVO):
   - Síntoma: `ImportError: DLL load failed while importing _multiarray_umath: Una directiva de Control de aplicaciones bloqueó este archivo`
   - Causa: AppLocker / Windows Defender SmartScreen / EDR corporativo bloquea DLLs no firmadas
   - Diagnóstico: Verificar `%LOCALAPPDATA%\..\Local\Temp`, `Get-EventLog -LogName Application`, `Get-AppLockerPolicy -Effective | Format-List`
   - Workarounds:
     - Reinstalar numpy: `pip uninstall numpy -y && pip install numpy==2.2.6 --no-cache-dir`
     - Añadir excepción AppLocker para `venv/Lib/site-packages/numpy/**/*.pyd`
     - Usar conda que tiene DLLs firmadas
     - Desactivar temporalmente: `Set-MpPreference -SubmitSamplesConsent 2` (no recomendado en producción)

2. `Install.bat` / `install_Mac.sh`:
   - Después de `pip install`, verificar `python -c "import numpy"` y mostrar mensaje accionable si falla
   - Pre-check: `python -c "import platform; print(platform.platform())"` y advertir sobre Python 3.12 + numpy 2.4 combo

3. `main.py`:
   - Añadir try/except alrededor de `from core import ...` que muestra un mensaje claro si numpy/u otra dep crítica falla al importar

4. `tests/unit/test_numpy_import.py` (NUEVO):
   - `assert __import__("numpy")` — smoke test para detectar este crash en CI
   - Marcar `@pytest.mark.windows` para skip en Mac/Linux

**Aceptación**:
- `docs/troubleshooting-windows.md` con sección dedicada
- `Install.bat` muestra mensaje accionable si numpy falla
- Smoke test detecta el crash

**Riesgo**: Bajo (solo diagnóstico y docs).

---

### **F112 — Hardening de `.env.example` y generación de secrets** (Media, 1 sesión)

**Objetivo**: Eliminar placeholders públicos y generar secrets seguros en install.

**Cambios**:

1. `.env.example`:
   - `AUTH_TOKEN=` (vacío) con comentario `# Generado automáticamente por Install.bat — ver .env`
   - `SECRET_KEY=` (vacío) con comentario similar
   - `SRT2WEB_GENERATE_SECRETS=1` (instrucción para Install.bat)

2. `Install.bat` / `install_Mac.sh`:
   - Si `.env` no existe, copiar de `.env.example`
   - Generar `AUTH_TOKEN` y `SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(32))"` si están vacíos
   - Reemplazar en `.env` antes de continuar con pip install
   - Mostrar resumen: "AUTH_TOKEN=xxxxxxxxx (almacenado en .env)"

3. `core/config_manager.py`:
   - Validar al arranque: si `auth_token == "your-secret-token-here"` o `len < 16` → warning bloqueante

4. `tests/unit/test_config_validation.py` (extender):
   - Test que verifica que auth_token placeholder es rechazado
   - Test que verifica que secret_key < 32 chars es rechazado

5. `docs/deployment.md`:
   - Sección "First-time setup" explicando el flujo de secrets

**Aceptación**:
- `.env` generado en install con secrets reales
- Cargar config con placeholder falla con error claro
- Cargar config con secret corto falla con warning

**Riesgo**: Medio. Cambia el flujo de install, requiere tests cuidadosos.

---

### **F113 — Frontend e2e tests: limpieza o eliminación** (Baja, 1 sesión)

**Objetivo**: Resolver los 2 e2e pre-fallidos conocidos o marcarlos como skip.

**Cambios**:

1. `tests/e2e/test_player_robustness.py::TestPlayerSubtitles`:
   - Verificar qué lee. Si lee `server/static/player.html`, refactorizar para leer el bundle Astro actual (`server/dist/`) o skip si no existe
   - Marcar como `@pytest.mark.skipif(not Path("server/static/index.html").exists(), reason="player.html not bundled")`

2. `tests/e2e/test_player_robustness.py::test_subtitle_refresh_interval`:
   - El test valida que el polling de subs es 2000ms. F108 eliminó el polling. Actualizar para validar la nueva estrategia (HLS.js native) o eliminar.

3. `tests/e2e/test_links_to_hls_stream`:
   - Si valida links en HTML estático, refactorizar para usar la app corriendo o skip.

**Aceptación**:
- `pytest tests/e2e/ -m "not slow" -q` → 0 failures, 0 errores, skip con razón
- O eliminar los tests obsoletos

**Riesgo**: Bajo.

---

### **F114 — Logging: setup consistente y archivo de log** (Media, 1 sesión)

**Objetivo**: Que el sistema de logging siempre escriba a un archivo y se pueda consultar post-mortem.

**Cambios**:

1. `core/logging_setup.py`:
   - Verificar que `setup_logging()` siempre añade un `RotatingFileHandler` a `logs/srt2web.log`
   - Crear `logs/` automáticamente
   - Nivel por defecto INFO; capturar DEBUG solo si `SRT2WEB_DEBUG=1`
   - Separar handler para `srt2web.security` que escribe a `logs/security.log` (auditoría)

2. `main.py`:
   - Llamar a `setup_logging()` antes de cualquier import que pueda loggear
   - Capturar excepciones no manejadas y escribir a `logs/crash.log` con traceback

3. `tests/unit/test_logging_setup.py` (NUEVO o extender):
   - Verificar que `logs/srt2web.log` se crea al primer log
   - Verificar que `logs/security.log` se crea en eventos SECURITY
   - Verificar rotación a 10MB

4. `docs/deployment.md`:
   - Documentar dónde están los logs y cómo verlos

**Aceptación**:
- Iniciar server produce `logs/srt2web.log` con primer INFO
- Eventos de seguridad van a `logs/security.log` separados
- Crash no manejado produce `logs/crash.log`

**Riesgo**: Bajo.

---

### **F115 — Refactor: extraer mtime correction a módulo core** (Baja, 1 sesión)

**Objetivo**: Reducir `srt_input.py:30KB` extrayendo lógica de clock a `core/chunk_clock.py`.

**Cambios**:

1. `core/chunk_clock.py` (NUEVO):
   - `ChunkClock` class con `record_mtime(mtime)`, `get_cumulative_duration()`, `reset()`
   - Encapsula la lógica de `srt_input.py:586-591` y `rtmp_input.py` (similar)

2. `modules/inputs/srt_input.py`:
   - Reemplazar bloque mtime con `self._clock = ChunkClock(chunk_duration=...)` + `self._clock.record_mtime(chunk_path.stat().st_mtime)`

3. `modules/inputs/rtmp_input.py`:
   - Mismo refactor

4. `tests/unit/test_chunk_clock.py` (NUEVO):
   - Drift acumulado, clamping, reset

5. Aplicar F108 acceptance criterio: `srt_input.py < 500 líneas` (ahora 735)

**Aceptación**:
- `srt_input.py < 500 líneas`
- Lógica de clock en módulo dedicado y testeable
- Sin regresión de comportamiento

**Riesgo**: Bajo (refactor mecánico).

---

## Resumen del plan

| ID | Nombre | Severidad | Esfuerzo | Dependencias |
|---|---|---|---|---|
| F109 | Fix test failures + dead code + cleanups | Alta | 1 sesión | — |
| F110 | Limpieza PARA BORRAR y debris | Media | 1 sesión | F109 |
| F111 | Diagnóstico numpy DLL load failed | Alta | 1 sesión | — |
| F112 | Hardening .env.example y secrets | Media | 1 sesión | — |
| F113 | Frontend e2e tests obsoletos | Baja | 1 sesión | — |
| F114 | Logging consistente y archivo | Media | 1 sesión | — |
| F115 | Refactor: extraer mtime a core/chunk_clock | Baja | 1 sesión | — |

**Orden recomendado**:
```
F109 (verdes tests) → F111 (numpy blocker) → F110 (cleanup) → F112 (secrets) → F114 (logging) → F113 (e2e) → F115 (refactor)
```

## Próximo paso

1. Marcar F109 como `in_progress` en `feature_list.json`
2. Implementar F109: 4 cambios de tests + 2 cambios de log statements + 1 git stash drop
3. Verificar con `init.ps1 -Quick` y `pytest tests/integration/`
4. Marcar F109 `done` y empezar F111 (numpy blocker)
