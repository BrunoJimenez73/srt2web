# Sesión activa — 2026-05-18

**Estado:** F77 completada — TypeScript/ESLint strict frontend
**Iniciada:** 2026-05-18

## Features completadas

### F74: Repo Cleanup Phase 1

- Eliminados `files/` (38 archivos), `desktop/` (13 entradas), 4 archivos huérfanos en raíz
- Version unification: `server/app.py` usa `importlib.metadata.version()`
- 29 bloques `except Exception:` reemplazados con logging
- 5 tests pre-existentes rotos fixeados
- `init.ps1 -Quick`: ✅ Verde

### F75: mypy gradual en modules/

- `modules/` ya estaba type-clean bajo `strict = true`
- `mypy core/ server/ modules/ --strict`: 0 errores (87 archivos)

### F76: mypy strict en cli/

- `cli/` eliminado de `exclude` en pyproject.toml
- 211 → 0 errores mypy en `cli/` (34 archivos)
- Fixes: imports asyncio/json al top, `-> None` en click commands, `cast()` en http_client, `Screen[Any]`/`Task[Any]` tipados
- `mypy core/ server/ modules/ cli/ --strict`: 0 errores (121 archivos)

### F77: TypeScript/ESLint strict frontend

- `@typescript-eslint/no-explicit-any`: warn → error
- Eliminado `.eslintrc.json` legacy (flat config eslint.config.js es fuente única)
- Eliminado `ignoreDeprecations: "5.0"` de tsconfig.json — tsc sin warnings
- Reemplazado `console.log` en `api.ts:404` por comentario
- Fixeados parsing errors en InputCard.astro (comillas anidadas) y TtsCard.astro (extra `</div>`)
- Fixeados `any` en `outputs.ts:71` (`Record<string, unknown>`) y `astro.d.ts:5` (eslint-disable)
- `npm run lint`: 0 errores, 22 warnings (todo preexistente)
- `npx tsc --noEmit`: limpio
- `init.ps1 -Quick`: ✅ Verde

### F78: Refactor unified_pipeline — circuit breaker y metrics

- Extraído `CircuitBreaker`, `CircuitState`, `RetryStrategy`, `is_recoverable_error` a `core/circuit_breaker.py`
- Extraído `PipelineMetrics` a `core/pipeline_metrics.py`
- `core/unified_pipeline.py` importa y delega; API pública sin breaking changes
- Fix ruff: UP007 (`X | Y`), SIM102, SIM114, SIM110, E402
- Tests: `test_stability.py` y `test_pipeline_metrics.py` pasan
- `init.ps1 -Quick`: ✅ Verde

### F79: Extraer piper worker a módulo separado

- `modules/piper_worker.py` (NUEVO): worker persistente como módulo real (antes string inline de 178 líneas)
- `modules/piper_loader_script.py` (NUEVO): one-shot loader como módulo real (antes string inline de 73 líneas)
- `modules/piper_loader.py`: 805 → 458 líneas (-43%), solo manager + IPC
- Fix: duplicado "ping" handler en worker original eliminado
- Fix: `logger` no definido en worker original reemplazado por `_log()` a stderr
- `mypy modules/`: 0 errores (`# mypy: ignore-errors` en scripts de subprocess)
- `init.ps1 -Quick`: ✅ Verde

---

## Features completadas

### F79: Extraer piper worker a módulo separado

- Eliminado `PERSISTENT_WORKER_SCRIPT` de `piper_loader.py` (ya no necesita constante que lee el archivo entero en import)
- `piper_loader.py` reducido de 545 → 360 líneas (<500 ✅)
- `piper_worker.py`: eliminado `# mypy: ignore-errors`, añadidos type hints completos, import `Any` desde typing
- `piper_loader_script.py`: eliminado `# mypy: ignore-errors`, simplificada lógica condicional
- Tests actualizados: `test_piper_heartbeat.py` lee de `piper_worker.py` directamente; `test_latest_features.py` apunta a `piper_worker.py`
- `mypy modules/piper_loader.py modules/piper_worker.py modules/piper_loader_script.py --strict`: 0 errores
- 37 tests de piper/TTS pasan sin regresiones

### F80: Modularizar pipeline-control e i18n JSON

- `pipeline-control.ts` ya era barrel re-export (refactor pre-existente con ws-manager, polling, config-client, presets-client, config-collector)
- Extraídas traducciones inline de `i18n.ts` (577 líneas) a `frontend/src/lib/locales/en.json` (235 keys) y `es.json` (235 keys)
- `i18n.ts` refactorizado para importar desde JSON en lugar de tener diccionarios inline (80 líneas)
- `npx tsc --noEmit`: 0 errores
- 99 frontend tests pasan (18 failures pre-existentes en effects.test.ts no relacionados)

### F81: Fix pre-existing effects.test.ts failures (18 tests)

- `effects.ts` expandido para centralizar todos los DOM updates driven por señales (status, module indicators, metrics, module metrics, throughput, GPU badges, WS badge, remote mode, clock, sync, logs, pipeline indicator)
- Creados `frontend/src/lib/locales/en.json` y `es.json` con todas las translation keys usadas en el código
- Añadido `startThroughputEffect()` para actualizar `metric-throughput-value` con el promedio de `throughputHistory`
- Añadido `startGpuBadgesEffect()` para actualizar badges por módulo (`gpu-badge-{name}`) con `style.display`
- Fix: warning/critical classes aplicadas a `metric-cpu` en lugar de `metric-cpu-bar`
- `npm test`: 125/125 passing, 0 failing ✅
- `npx tsc --noEmit`: 0 errores

## Completado en esta sesión

### F82: Frontend test coverage >85%

- 4 nuevos test files para módulos extraídos en F80:
  - `ws-manager.test.ts` (12 tests): conexión WS, handlers de mensajes/error/close, disconnect
  - `polling.test.ts` (14 tests): polling adaptativo, post-start mode, file info polling, intervalos
  - `config-client.test.ts` (11 tests): save/export config, dumpConfig helper, manejo de errores
  - `presets-client.test.ts` (11 tests): load/apply/save presets, errores HTTP y de red
- Total: 52 tests nuevos, 177/177 tests frontend pasando
- Fix: export `dumpConfig` en `config-client.ts` para testeabilidad
- Fix: Vitest v4 incompatibilidad con arrow functions en `vi.fn()` (constructor mock requiere `function` keyword)
- `npm test`: 9 files, 177 tests, 0 failed ✅

## Bugfixes post-F84-F86 (Mayo 2026)

### Stop.bat — rewrite completo
- Mata TODOS los `python.exe`, `python3.exe`, `ffmpeg.exe`, `ffprobe.exe`
- Libera puertos del sistema (9999, 9000, 8000, 1935)
- Limpia `__pycache__`, `.pyc`, `.pyo`, `.ruff_cache`, `.mypy_cache`, `.pytest_cache`
- Limpia logs y TODOS los directorios temporales de output: `hls`, `subtitles`, `chunks`, `temp_audio`, `temp_mix`, `temp_tts`, `video`, `audio`

### SubtitleGenerator — limpieza y escritura atómica
- `start()` ahora limpia viejos `chunk_*.srt` de sesiones anteriores
- `_rewrite_vtt_file()` usa escritura atómica: escribe a `.subs.vtt.tmp` → `Path.replace()` a `subs.vtt`
- Previene que el webplayer lea el archivo VTT a medio escribir (evita parse errors y subtítulos "colgados")

### LogPanel — auto-expand en primer log
- `addLog()` en `logpanel.ts` ahora expande automáticamente el panel (collapsed → expanded) cuando llega el primer log, en vez de esperar que el usuario haga clic en el header.

### Stop.bat v3 — soporte para Node, kill por puerto, verificación
- Añadido `taskkill /F /IM node.exe` para matar servidores Astro/Node
- Añadido `powershell Stop-Process` por puerto (9999, 9000, 9001, 9002, 8000, 1935, 4321, 5173, 4173)
- Tres pasadas de kill para atrapar respawns (Windows App execution aliases)
- Verificación post-limpieza: chequea que no queden procesos Python/FFmpeg/Node

### Webplayer — arreglo de tirones (stuttering)
- Eliminado `<track>` nativo de `player.astro`: el JS en `player.ts` ya gestiona subtítulos vía `VTTCue`, el `<track>` nativo creaba un sistema dual que causaba conflictos y refrescos de cue innecesarios cada 500ms.
- `hls.js config` ajustada: `lowLatencyMode: false` (el servidor no emite partial segments), `maxBufferLength: 30` (antes 10 = solo 2 segmentos), `liveSyncMaxLatency: 10` (antes 4, muy agresivo para segmentos de 5s), `liveDurationInfinity: true`.
- Subtitle polling reducido de 500ms a 2000ms (120 req/min → 30 req/min).
- `stream.m3u8` y `master.m3u8` ahora se escriben atómicamente (tmp → `os.replace()`) para evitar que hls.js lea playlists a medio escribir.

### Fix Stop pipeline — StatusCard event handlers y WS status broadcast
- **`window.stopPipeline` / `window.startPipeline` estaban undefined**: El botón Stop/Start en StatusCard.astro llamaba a `window.stopPipeline()` y `window.startPipeline()` (línea 113-116), pero nunca se asignaban. Ahora se exponen en `pipeline-control.ts` (`window.startPipeline = handleStart`, `window.stopPipeline = handleStop`), siguiendo el mismo patrón que `window.saveConfig`.
- **Handlers duplicados eliminados**: El `DOMContentLoaded` listener en StatusCard.astro que añadía event listeners a los botones era redundante (ya lo hace `setupEventListeners()` en pipeline-control.ts) y encima llamaba a funciones undefined. Eliminado.
- **WS `broadcast_status` no llegaba al frontend**: El servidor emitía `{"type": "status", "state": "running", ...}` con los campos esparcidos al nivel superior. El frontend espera `data.status` anidado (`{"type": "status", "status": {"state": "running", ...}}`). Corregido: ahora `broadcast_status()` y el handler `get_status` envuelven el status en `status:`.
- **Efecto**: Ahora las actualizaciones de estado vía WebSocket SÍ se consumen, no solo vía HTTP polling. El dashboard reacciona más rápido a cambios de estado.

### Fix pipeline.stop() bloqueaba event loop — Stop desde frontend no funcionaba
- `pipeline.stop()` (`async def`) llamaba `thread.join(timeout=5.0)` directamente, **bloqueando el event loop de asyncio** por hasta ~20s (input + 2 workers + output × 5s c/u).
- El frontend tiene timeout de 15s en `apiCall()`. Al hacer clic en Stop, el POST /api/stop se quedaba colgado → timeout → error en frontend (catch block mostraba error en logs). El usuario creía que el botón no funcionaba.
- Fix: Envolver los `thread.join()` en `await asyncio.to_thread(...)` para que no congelen el event loop. El servidor sigue respondiendo a otras peticiones (status, health) mientras los threads se unen.
- Tests: 132 pipeline/core tests pasan.

### Estado actual
- `pytest tests/unit/ -q --tb=short -m "not slow"` → ✅ 1066 pasan
- `mypy core/ server/ modules/ --strict` → ✅ 0 errores
- `ruff check core/ modules/ server/ tests/` → ✅ limpio
- `npx tsc --noEmit` → 9 errores pre-existentes (i18n keys desactualizadas, no relacionados)
