# Sesión actual — F106: Piper TTS ignora la voz (2 bugs distintos) ✅ DONE

## Cambios realizados

### F106 — "Piper TTS ignora la voz" (en realidad 2 bugs distintos)

**Síntoma reportado**: "Cambio la voz Piper en el frontend y siempre suena la misma".

**Causa raíz** (logs del usuario revelaron que NO era 1 bug, sino 2 bugs distintos que producían el mismo síntoma):

#### Bug 1 — `PUT /api/config` 400 por tipo `webplayer`

- `modules/outputs/__init__.py:21-23` registra los aliases `webplayer` + `web` + `hls` apuntando todos a `HLSOutput`.
- `core/io_factory.py:resolve_type()` devolvía el **primer** nombre registrado (FIFO), que era `webplayer` para HLSOutput.
- `server/routes/outputs.py:_sync_outputs_to_config()` (línea 37) llamaba `resolve_type()` y guardaba el valor crudo en `output.outputs[0].type`.
- `core/config_schema.py:OutputTypeEnum` solo acepta `web|srt|rtmp|file|recording`. El `webplayer` en la config hacía fallar TODOS los `PUT /api/config` con 400 Pydantic enum error.
- El usuario no podía guardar la config con la voz nueva. La UI mostraba error toast y el audio quedaba con la voz anterior.

**Fix Bug 1** (defensa en 2 capas):
1. `core/io_factory.py`: nuevo atributo `_canonical_types = frozenset({"web","srt","rtmp","file","recording","webrtc"})`; `resolve_type()` ahora prefiere nombres canónicos sobre aliases.
2. `server/routes/outputs.py`: nueva función `_normalize_output_type()` que mapea `webplayer|hls → web`; aplicada en `_sync_outputs_to_config()` antes de persistir.

#### Bug 2 — Race condition en `PiperSubprocessManager._send_command`

- `modules/piper_loader.py:_send_command()` NO serializaba concurrentes. Cada llamada lanzaba un thread nuevo que hacía `proc.stdout.readline()` sobre el pipe compartido.
- El heartbeat corre cada 30s y llama `_send_command({"action": "ping"})`. Si coincidía con un synth en vuelo, dos threads leían del mismo stdout → respuestas JSON concatenadas en una sola línea.
- Síntoma: `Invalid JSON response: Extra data: line 1 column 22652 (char 22651)` — 22,651 chars de JSON válido + "extra data" (otra respuesta JSON en la misma línea).
- Tras el parse error, `is_alive` podía devolver False → heartbeat disparaba restart, pero el subprocess "vivo" realmente había sido reemplazado y el código no recargaba. Chunks subsiguientes: `Piper subprocess not running` → silencio.

**Fix Bug 2**:
- `modules/piper_loader.py:PiperSubprocessManager.__init__`: nuevo `self._cmd_lock = threading.Lock()`.
- `_send_command()` envuelve TODO su cuerpo en `with self._cmd_lock:`. Synth y heartbeat ahora se serializan; el heartbeat espera al synth en vez de competir por el mismo `readline()`.

**Honrando F106 mitigation**: NO se tocó `modules/tts_engine.py` — la chain `configure() → _init_piper() → PiperSubprocessManager.start()` ya funcionaba correctamente (verificado con tests de propagación). El sintoma del usuario era enteramente backend, no frontend.

**Tests añadidos** en `tests/unit/test_f106_piper_voice.py` (9 tests):
- `TestResolveTypePrefersCanonical::test_resolve_type_returns_canonical_for_hlsoutput` — verifica que `resolve_type('HLSOutput') == 'web'`.
- `TestResolveTypePrefersCanonical::test_resolve_type_canonical_in_enum` — itera todos los outputs y verifica que `resolve_type` devuelve un valor en `OutputTypeEnum`.
- `TestNormalizeOutputType::test_normalize_canonical_passthrough` — `web/srt/rtmp/file/recording` retornan igual.
- `TestNormalizeOutputType::test_normalize_alias_webplayer_to_web` — `webplayer` y `hls` → `web`.
- `TestNormalizeOutputType::test_normalize_unknown_to_web` — `None/''/'bogus'` → `web` (fallback seguro).
- `TestSyncOutputsPersistsCanonical::test_sync_persists_web_not_webplayer` — end-to-end: mock composite + `_sync_outputs_to_config()` → `config.set('output.outputs', [...])` con type=`'web'`.
- `TestPiperCmdLock::test_cmd_lock_exists` — `PiperSubprocessManager` tiene `_cmd_lock: threading.Lock`.
- `TestPiperCmdLock::test_concurrent_send_command_serialized` — 2 threads racing en `_send_command`, ambos completan sin error.
- `TestPiperCmdLock::test_sequential_send_command_works` — el lock es un `Lock` acquireable normal (no rompe sequential).

**Verificación**:
- `pytest tests/unit/test_f106_piper_voice.py -v` → **9 passed** en 0.48s
- `pytest tests/unit/test_piper_heartbeat.py test_multioutput_api.py test_composite_output.py test_hls_output.py test_output_modules.py test_error_paths_timeouts.py test_latest_features.py -v` → **129 passed, 3 skipped** (GPU) en 8.07s
- `pytest tests/unit/test_config_manager.py test_config_hot_reload.py test_config_validation.py test_config_deduplication.py test_config_migration.py test_config_snapshot.py test_api_routes.py test_api_cache.py test_api_contract.py -v` → **185 passed, 2 xpassed** en 8.78s
- `npx tsc --noEmit` → 0 errores
- `npx vitest run src/test_f106_piper_voice.test.ts` → **3 passed** (Piper/Edge collect + default Sharvard)
- Script ad-hoc: `resolve_type('HLSOutput')` → `'web'`, `_sync_outputs_to_config` persiste `type='web'` (end-to-end)

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `core/io_factory.py` | `_canonical_types` frozenset; `resolve_type()` prefiere canónicos |
| `server/routes/outputs.py` | `_normalize_output_type()`; aplicada en `_sync_outputs_to_config()` |
| `modules/piper_loader.py` | `PiperSubprocessManager._cmd_lock = threading.Lock()`; `_send_command()` envuelve cuerpo con `with self._cmd_lock:` |
| `tests/unit/test_f106_piper_voice.py` | 9 tests nuevos (Bug 1 + Bug 2 regression) |
| `feature_list.json` | F106 `in_progress` → `done` con descripción detallada de ambos bugs |
| `AGENTS.md` | §7 Estado de features F106 ✅ DONE; §8 Historial con detalle de los 2 bugs |
| `progress/current.md` | Esta entrada (encabezado) |

## Contexto histórico de la sesión

### F105 — `composite_output.py` reconnect Timer sobrevive a `stop()`

**Síntoma reportado**: "Al parar el pipeline no me deja parar e intenta reconectar todo el rato".

**Causa raíz** (1 causa, identificada por análisis de código ya que no había logs):
- `modules/outputs/composite_output.py:114-127` `_schedule_reconnect()` creaba un `threading.Timer(self._reconnect_delay=5s, reconnect)` y lo disparaba con `timer.start()` — pero **nunca guardaba referencia ni lo cancelaba en `stop()`**.
- `composite_output.stop()` (línea 90) solo llamaba a `output.stop()` por cada output; el Timer quedaba pendiente.
- 5s después, el Timer disparaba `_reconnect_output()` (línea 129) que hacía `output.stop()` + `output.start()` — **reanimando un output que el usuario ya había parado**.
- En cada fallo de output, el loop se repetía: hasta `_max_reconnect_attempts=3` con delay de 5s = 15s de ruido "Output X reconnect attempt Y/Z" en el log panel.

**Fix** (4 cambios, todos en `modules/outputs/composite_output.py`):

1. `__init__`: nuevo registro `self._reconnect_timers: dict[str, threading.Timer] = {}` y flag `self._stopped = False`.
2. `start()`: resetea `self._stopped = False` para permitir reconexiones en una nueva ejecución.
3. `stop()`: marca `self._stopped = True` e itera `self._reconnect_timers` llamando `timer.cancel()` a cada uno, luego limpia el dict.
4. `_schedule_reconnect()` y `_reconnect_output()`: check explícito de `self._stopped` al inicio (early return). `_schedule_reconnect` guarda el timer en `self._reconnect_timers[name]` antes de hacer `start()`. La callback del timer hace `self._reconnect_timers.pop(name)` antes de ejecutar.

**Tests añadidos** en `tests/unit/test_composite_output.py`:
- `test_f105_reconnect_timer_cancelled_on_stop`: dispara un Timer, llama `stop()`, verifica que `mock_output._started_count` no cambia tras esperar más que el delay.
- `test_f105_reconnect_after_stop_is_noop`: tras `stop()`, un `_schedule_reconnect()` debe ser no-op (attempts no incrementa).
- `test_f105_start_resets_stopped_flag`: tras un nuevo `start()`, `_stopped = False` y los reconnects vuelven a funcionar.

**Verificación**:
- `pytest tests/unit/test_composite_output.py -v` → **23 passed** (3 nuevos F105)
- `mypy --strict modules/outputs/composite_output.py` → 0 errores
- `npm test -- --run` → 180/180 passed
- `pytest tests/unit/test_recording_output.py test_hls_output.py test_rtmp_input.py test_workspace_fixes.py test_phase4_5_improvements.py test_api_routes.py test_output_modules.py test_composite_output.py` → todos pasan

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `modules/outputs/composite_output.py` | `_reconnect_timers` dict + `_stopped` flag; `stop()` cancela timers; `_schedule_reconnect` y `_reconnect_output` chequean flag |
| `tests/unit/test_composite_output.py` | 3 tests nuevos F105; `MockOutput._started_count` counter para verificarlos |
| `feature_list.json` | F105 status `pending` → `done` |
| `progress/current.md` | Esta entrada |

## Próximo

F106 (Piper TTS ignora voz seleccionada) sigue pendiente. La cadena a investigar es: `frontend → /api/config (tts.*) → tts_engine.configure() → PiperSubprocessManager`. Sospecha principal: lazy load con `_voice_loaded` flag que no se reinicia correctamente al cambiar voz entre start()s.

---


## Cambios realizados

### 1. ✅ LogPanel — colapso/expand + filtro de nivel

**Síntoma**: El panel de logs no respondía al click en el triángulo de colapso ni al filtro dropdown. Los `data-testid` faltaban.

**Causa raíz**: `frontend/src/pages/index.astro` tenía un placeholder inline roto que intentaba `await import('../components/LogPanel.astro')` — los componentes Astro son server-rendered, no se pueden importar dinámicamente client-side.

**Fix**:
- `index.astro`: eliminado el placeholder inline; import estático `import LogPanel from '../components/LogPanel.astro'` + `<LogPanel />`.
- `LogPanel.astro`: reescrito como HTML+CSS puro con `data-testid` correctos (`log-panel`, `btn-toggle-logs`, `log-level-filter`, `btn-export-logs`, `log-search`, `log-entry`); eliminada la duplicación del `<script>` inline (definía `window.__logAdd` que nadie usaba).
- `effects.ts`: en vez del hack `window.__logAdd`, ahora hace `import { addLog } from "../modules/logpanel"` directamente.
- `logpanel.ts`: añadidos `data-testid="log-entry"` a cada entry.
- `en.json` + `es.json`: 11 i18n keys nuevas (`log_title`, `log_filter_all/info/warning/error`, `log_search_placeholder`, `search_logs`, `log_export_json/txt`, `clear_logs`, `log_clear`).

### 2. ✅ Preset save — lista no se actualizaba tras guardar

**Síntoma**: Tras `POST /api/presets/`, la lista `#saved-presets-list` no reflejaba el nuevo preset.

**Causa raíz**: `Header.astro` (versión layout) renderizaba la lista una vez en `onMount` y nunca se re-suscribía al signal `presets`.

**Fix** (`Header.astro`):
- Añadido `effect(() => { re-render lista cuando presets.value cambia })`.
- Botón Eliminar por preset wired a `fetchWithAuth("/api/presets/${name}", { method: "DELETE" })` (endpoint ya existe en `server/routes/config.py:109`); tras éxito recarga la lista.
- Render inicial defensivo por si `loadPresets()` resolvía antes de que el effect se montara.

### 3. ✅ Botón Shortcuts no funcionaba

**Síntoma**: El icono de atajos de teclado en el header no abría el modal.

**Causa raíz**: El handler `keydown` global en `keyboard-shortcuts.ts` solo escucha eventos del DOM, no clicks de botones.

**Fix** (`Header.astro`):
- Click handler en `#btn-shortcuts-help` que despacha un `KeyboardEvent` sintético (`new KeyboardEvent("keydown", { key: "?" })`) al document, reusando el handler existente.

### 4. ✅ Botón Docs → 404 JSON en subrutas

**Síntoma**: `/docs` devolvía la página renderizada, pero cualquier subpath (`/docs/getting-started`, etc.) devolvía JSON 404 en vez de HTML.

**Causa raíz**: Solo existía `frontend/src/pages/docs/index.astro`; no había subpáginas ni catch-all en el server.

**Fix**:
- `frontend/src/pages/docs/index.astro` (NUEVO): landing con hero, sectioned cards (Getting Started / Modules / API / Guides), quickstart codeblock; reusa `DocsLayout.astro` + `DocsSidebar.astro` existentes.
- `server/app.py`: nueva constante `_DOCS_STUB_HTML` + `@app.get("/docs/{path:path}")` que devuelve "Sección en construcción" para subpaths sin HTML estático. **Critical route reorder**: movidas las rutas explícitas (`/`, `/player`, `/webrtc-player`, `/docs/{path:path}`) ANTES de `app.mount("/", static_files)` para que ganen la race; añadida `HTMLResponse` a los imports de FastAPI.

### 5. ✅ SRT URL en dashboard — no se calculaba desde INPUT

**Síntoma**: El campo "SRT" en `ConnectionCard` mostraba `srt://host:port` sin `?mode=` ni `?latency=`. Para pegar en OBS hacía falta el modo opuesto al del servidor.

**Causa raíz**: `connectionUrls` en `signals.ts` construía `srtUrl` sin consultar el config de input.

**Fix** (`signals.ts`):
- Helper `srtClientMode(serverMode)`: listener→caller, caller→listener, rendezvous→rendezvous.
- `srtUrl = srt://${host}:${srtPort}?mode=${obsSrtMode}&latency=${srtLatency}`.
- `rtmpUrl = rtmp://${host}:${rtmpPort}/${rtmpApp}/${rtmpKey}` (también le faltaban app/key).
- Nuevos campos `srtServerMode` + `srtClientMode` en `connectionUrls`.
- `signals.test.ts`: 5 tests actualizados (default con latency=200, caller, rendezvous, latency passthrough, RTMP app/key).
- `api.ts`: `SrtInputConfig.mode` → `"listener" | "caller" | "rendezvous"` (faltaba "rendezvous").

### 6. ✅ System Metrics card — colapso/expand

**Síntoma**: El card de métricas del sistema no tenía triángulo de colapso/expand (el de "Module Timing" interno sí).

**Fix** (`MetricsCard.astro`):
- Header convertido a `<button id="metrics-header-toggle">` con chevron `▾` dentro del título.
- Body (`metrics-grid` + `module-timing-section`) envuelto en `<div class="metrics-body" id="metrics-body">`.
- CSS: `.metrics-header[aria-expanded="false"] + .metrics-body { display: none }`; chevron rota -90deg cuando colapsado.
- JS handler persiste estado en `localStorage["srt2web:metrics:system-expanded"]` (default = expandido).
- `e.stopPropagation()` en el timing header interno para evitar doble toggle; el handler externo ignora clicks burbujeados desde `.timing-header`.

## Verificación

- `npx astro build` → **OK**, `/docs/index.html` generado, 5 páginas estáticas
- `npm test -- --run` → **180 passed** (incluyendo 5 nuevos tests de SRT/RTMP URL)
- `npx tsc --noEmit` → **0 errores**
- `pytest tests/unit/test_api_routes.py test_health_check.py test_frontend_dashboard_features.py test_player_robustness.py test_presets_api.py test_frontend_refactor.py` → **166 passed**

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `frontend/src/pages/index.astro` | Eliminado placeholder inline; import estático + `<LogPanel />` |
| `frontend/src/components/LogPanel.astro` | Reescrito: HTML+CSS puro con data-testid; sin script inline |
| `frontend/src/components/layout/Header.astro` | Effect de preset, DELETE handler, shortcuts synthetic event |
| `frontend/src/components/MetricsCard.astro` | Header colapsable + chevron + localStorage persist |
| `frontend/src/pages/docs/index.astro` | NUEVO: landing con hero + cards + quickstart |
| `frontend/src/lib/store/signals.ts` | `srtClientMode` helper; SRT/RTMP URLs con mode/latency/app/key |
| `frontend/src/lib/store/signals.test.ts` | 5 tests actualizados para URLs extendidas |
| `frontend/src/lib/store/effects.ts` | `import { addLog }` directo; sin `window.__logAdd` |
| `frontend/src/lib/modules/logpanel.ts` | `data-testid="log-entry"` en entries |
| `frontend/src/lib/types/api.ts` | `SrtInputConfig.mode` acepta `"rendezvous"` |
| `frontend/src/lib/locales/en.json` + `es.json` | 11 i18n keys nuevas |
| `server/app.py` | `HTMLResponse` import; `_DOCS_STUB_HTML`; `@app.get("/docs/{path:path}")`; **route reorder** (explícitas antes del static mount) |
| `server/static/docs/index.html` | Generado por `npx astro build` |
| `progress/current.md` | Esta sesión |

## Siguiente

F104 — pendiente (ver `feature_list.json`).

---


## Cambios realizados

### 1. ✅ ADR 003 — Duplicado deprecado
- Reemplazado contenido por redirect a ADR 001 (única fuente de verdad)
- Fecha de deprecation añadida

### 2. ✅ ADR 001 — PipelineOrchestrator → PipelineManager
- `PipelineOrchestrator` → `PipelineManager` (clase real actual)
- `AsyncPipelineStrategy` → `AsyncIOStrategy` (clase real en strategies.py)
- Añadida referencia a `core/pipeline/strategies.py` y `core/pipeline_manager.py`

### 3. ✅ docs/architecture.md — Estructura y clases actualizadas
- Pipeline modes: clases legacy → estrategias activas (`SequentialStrategy`, `ThreadParallelStrategy`, `AsyncIOStrategy`)
- Añadida nota sobre wrappers deprecados que emiten `DeprecationWarning`
- Directorio CLI: `cli/srt2web.py` → `cli/main.py` + `cli/client/`, `cli/commands/`, `cli/tui/`
- Directorio pipeline: añadido `strategies.py` como activo, marcados wrappers legacy como deprecados
- `pipeline.py` → alias `Pipeline = UnifiedPipeline`

### 4. ✅ docs/deployment.md — WebSocket auth, CLI, test count
- WebSocket: query param `?token=` → mensaje JSON `{"type":"auth","token":"..."}`
- CLI: todos los comandos actualizados (`srt2web` → `srt2web-tui`, `modules` → `module`, `outputs` → `output`)
- Test count: 740 → 1129

### 5. ✅ docs/cli.md — Reescribir completo
- Entry point: `cli/srt2web.py` → `srt2web-tui` (Click, `cli.main:cli_entry`)
- Comandos removidos que no existen: `stream`, `available`, `shell`, `metrics`
- Comandos añadidos: `pipeline start/stop/restart`, `preset`, `recording`, `input`, `network`, `health`, `tui`
- Flags actualizados: `--watch` → `--follow/--no-follow`, `--filter LEVEL` → `--level LEVEL`, `--format json` → `--json`
- Grupos de comandos: `modules` → `module`, `outputs` → `output`
- Ejemplos de integración con scripts actualizados

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `docs/adr/003-modular-pipeline-architecture.md` | Deprecado, redirect a ADR 001 |
| `docs/adr/001-pipeline-modular-architecture.md` | PipelineOrchestrator→PipelineManager, AsyncPipelineStrategy→AsyncIOStrategy |
| `docs/architecture.md` | Pipeline modes, dir structure CLI+pipeline, class names |
| `docs/deployment.md` | WebSocket auth message-based, CLI examples, test count 1129 |
| `docs/cli.md` | Reescribir completo para CLI Click actual |
| `feature_list.json` | F103 done |
| `progress/current.md` | Esta sesión |

## Resultados

- `.\init.ps1 -Quick` → **verde** (1 fallo pre-existente no relacionado en test_config_hot_reload.py)
- `mypy --strict core/ server/ modules/` → **0 errores** (sin cambios en código Python)
- `cd frontend && npx tsc --noEmit` → **0 errores**

## Siguiente

F104 — **DONE** (esta sesión).

**Bugs nuevos reportados por el usuario al final de la sesión (pendientes de investigación y fix)**:

### F105 — Stop pipeline no cierra del todo, WS/IO se reconecta en bucle

**Síntoma**: Al pulsar Stop, el pipeline no se queda en `idle`; algo sigue intentando reconectar (logs con noise constante, posiblemente el pipeline vuelve a `running` por su cuenta).

**Causas probables a investigar** (NO TOCAR todavía):
1. **Watchdog de SRT input** (`modules/inputs/srt_input.py`): `max_restarts=10`. Si la condición `_stopping.is_set()` no se respeta durante el restart, el watchdog puede reactivar ffmpeg después del stop.
2. **Polling adaptativo** (`frontend/src/lib/modules/polling.ts`): si el WS llega con `state=running` después del stop, entra en `POST_START` mode (1s polling). Esto reactivaría el indicador de actividad.
3. **WS reconnect** (`frontend/src/lib/modules/ws-manager.ts`): tras stop, el servidor puede seguir enviando mensajes; el cliente intenta reconectar 5 veces con backoff.
4. **Race entre `await pipeline.stop()` y el watchdog thread**: el watchdog check es cada 5s. Si stop se llama justo después de un crash, el watchdog puede ver el proceso muerto y relanzarlo antes de que el flag `_stopping` se propague.

**Hipótesis a verificar primero**: leer `logs/app.log` con timestamps de los últimos minutos de un ciclo start→stop, contar cuántos reintentos reales hay, y a qué componente pertenecen.

### F106 — Piper TTS ignora la voz seleccionada

**Síntoma**: Cambiar la voz Piper en la UI no tiene efecto. Siempre suena la misma.

**Causa más probable** (encontrada en código, NO confirmada todavía):
- `modules/tts_engine.py:_run_piper_tts()`: la voz se carga lazy en la primera síntesis si `not self._voice_loaded`.
- `configure()` (línea 60-67) sí resetea `_voice_loaded = False` cuando la voz cambia.
- **Pero** `_init_piper()` crea un NUEVO `PiperSubprocessManager` sobreescribiendo el anterior (línea 137: `self._piper_manager = PiperSubprocessManager()`). El anterior nunca se llama `.stop()` → puede quedar zombie.
- Si el `PiperSubprocessManager.start()` recicla el proceso anterior en vez de matar y relanzar con el modelo nuevo, la voz sigue siendo la del primer load.

**Causa alternativa** (verificar primero): el cambio de voz en el frontend NO llega al backend. La cadena es:
`Header/Settings.ts → POST /api/config → config_manager → tts_engine.configure()`. Si algún punto de esta cadena no propaga `tts.voice`, el módulo nunca se entera.

**Hipótesis a verificar primero**: leer `logs/app.log` filtrando por "TTS" o "Piper" y confirmar si aparece el log "Lazy loading voice: <nombre>" con el nombre NUEVO. Si NO aparece, el problema está en la frontera frontend→API. Si aparece pero suena la voz vieja, el problema está en `PiperSubprocessManager`.

### F104 (pre-existente arreglado de paso)

`tests/unit/test_workspace_fixes.py:test_stop_mac_sh_has_clean_flag` esperaba la variable `CLEAN_MODE` en `stop_Mac.sh`, pero la implementación actual usa `DO_CLEAN`/`AGGRESSIVE_CLEAN`. Actualizado el test a `DO_CLEAN`. **Este test failure ya existía en F100 (commit be1dc0b) y nunca se había corregido.**

---


# Sesión 2026-06-01 — Bugfix: Stale images in webplayer + Stop scripts cleanup

## Cambios realizados

### 1. ✅ Service Worker — root cause of "stale images from another session"

**Síntoma**: El webplayer mostraba imágenes de la sesión anterior al iniciar una nueva, aunque los archivos del servidor estaban limpios.

**Causa raíz**: `frontend/public/service-worker.js` usaba estrategia **cache-first** y cacheaba **todo GET con status 200** — incluyendo `/hls/seg_*.ts`, `/hls/stream.m3u8` y `/subtitles/subs.vtt`. Los segmentos HLS tienen nombres fijos (`seg_000000.ts`…) que se reutilizan entre sesiones: el SW servía el contenido viejo cacheado aunque el servidor ya tenía el nuevo.

**Fix** (`frontend/public/service-worker.js`):
- Bump `CACHE_NAME` `srt2web-v1` → `srt2web-v2` (fuerza purge en clientes existentes)
- Whitelist `NO_CACHE_PATH_PREFIXES`: `/hls/`, `/subtitles/`, `/recordings/`, `/api/`, `/ws`, `/health`, `/ready`, `/live`, `/player`, `/webrtc-player`
- Esos paths van **siempre a la red** (`fetch(request, { cache: "no-store" })`), sin leer ni escribir cache
- Hash fingerprints de Astro (`/_astro/*`) → cache-first seguro (cambian con el hash)
- HTML shell / manifest / icons → **network-first** con fallback a cache (así se ven updates rápido)
- Handler `message` para `CLEAR_CACHES` (la app puede forzar purgado en reconexión)
- Copia de `server/static/service-worker.js` sincronizada (se copia manualmente para que tome efecto sin rebuild de Astro)

### 2. ✅ Backend — `Cache-Control: no-store` en `/hls` y `/subtitles`

Defense-in-depth para usuarios sin service worker / con cache de disco / con proxy intermedio.

**Fix** (`server/app.py`):
- Nueva clase `NoCacheStaticFiles(StaticFiles)` que sobrescribe `get_response` para inyectar headers `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, `Expires: 0`
- Aplicada a los mounts `/hls` y `/subtitles` (`/recordings` ya va por route handler, no StaticFiles)
- Verificado end-to-end con TestClient: `GET /hls/seg_000000.ts` → `200` con `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`

### 3. ✅ Player — enviar `CLEAR_CACHES` al SW en cada `connect()`

**Fix** (`frontend/src/lib/modules/player.ts`):
- En la función `connect()`, antes de inicializar HLS.js, envía `{ type: "CLEAR_CACHES" }` al SW controlador
- Es la red de seguridad final: si un cliente con SW antiguo aún tenía segmentos cacheados pre-fix, los descarta en la primera carga de la nueva sesión

### 4. ✅ `Stop.bat` — limpieza automática de temporales de sesión anterior

**Comportamiento anterior**: `Stop.bat` por defecto solo paraba el servidor. La limpieza requería `Stop.bat --clean` + confirmación interactiva "s". Resultado: archivos stale se acumulaban.

**Comportamiento nuevo**:
- **Por defecto**: para el servidor y limpia los temporales de sesión anterior (`chunks/`, `temp_audio/`, `temp_mix/`, `temp_tts/`, `hls/seg_*.ts`, `hls/*.m3u8`, `subtitles/chunk_*.srt`, `subtitles/subs.vtt`)
- **Siempre preserva**: `output/recordings/` (datos del usuario) y `logs/` (útil para debug)
- `--no-clean` → solo para, sin tocar nada
- `--clean`/`-c`/`--purge` → limpieza + wipe de `logs/`, `__pycache__/`, `*.pyc`, `.ruff_cache`, `.mypy_cache`, `.pytest_cache` (con confirmación "s")
- `--keep-recordings` → flag aceptado para compatibilidad (ya es el default)

Bug encontrado y corregido durante el desarrollo: `if not defined DO_CLEAN` siempre era false porque `DO_CLEAN=0` está definido. Cambiado a `if "%DO_CLEAN%"=="0"`.

### 5. ✅ `stop_Mac.sh` — paridad con Stop.bat

Misma lógica portada a macOS con sintaxis bash:
- `find output/hls -maxdepth 1 -type f -name "*.m3u8" -delete` para manifiestos
- `find . -type d -name __pycache__ -not -path "*/venv/*" -not -path "*/node_modules/*" -exec rm -rf {} +` para pycache
- Mismas flags, mismo comportamiento

## Verificación

- `cmd /c Stop.bat --no-clean` → 6 archivos stale **preservados** ✓
- `cmd /c Stop.bat` (default) → 5 archivos stale **eliminados**, `recordings/test_recording.mp4` **preservado** ✓
- `echo s | cmd /c Stop.bat --clean` → 5 stale + `logs/app.log` + `core/__pycache__/` **eliminados**, recordings **preservado** ✓
- `python -m pytest tests/unit/test_api_routes.py test_hls_output.py test_subtitle_generator.py test_player_robustness.py test_player_websocket_fixes.py test_frontend_dashboard_features.py test_frontend_refactor.py` → **148 passed** ✓
- TestClient: `GET /hls/seg_000000.ts` → `200` con `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` ✓
- `node --check frontend/public/service-worker.js` → sintaxis OK ✓
- `python -m ruff check server/app.py` → no new errors (los 2 F401/E402 son pre-existentes) ✓

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `frontend/public/service-worker.js` | Reescrito: NO_CACHE_PATH_PREFIXES, network-first para live, handler CLEAR_CACHES, bump CACHE_NAME |
| `server/static/service-worker.js` | Copia sincronizada del source (efecto inmediato sin rebuild) |
| `server/app.py` | Clase `NoCacheStaticFiles`, aplicada a mounts `/hls` y `/subtitles` |
| `frontend/src/lib/modules/player.ts` | `connect()` envía `CLEAR_CACHES` al SW controlador |
| `Stop.bat` | Limpieza automática por defecto; `--clean` agresivo; `--no-clean` opt-out; preserva `recordings/` y `logs/` |
| `stop_Mac.sh` | Misma lógica portada a bash |
| `progress/current.md` | Esta entrada |

## Siguiente

F104 — pendiente.
