# AGENTS.md — Mapa de navegación para srt2web

> Punto de entrada para cualquier agente que trabaje en este repo.
> Lee solo lo que necesites. Divulgación progresiva.

---

## 1. Mapa del repositorio

| Archivo / carpeta   | Qué contiene                                                                                                                                                                                                                                                                 | Cuándo leerlo           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `harness.db`        | Base de datos SQLite con features, sesiones, audit trail y progreso                                                                                                                                                                                                          | Siempre, al empezar     |
| `harness/`          | Paquete Python para gestionar features (CLI + DB + migración + web UI)                                                                                                                                                                                                       | Para gestionar features |
| `feature_list.json` | Features con status (legacy, migrado a harness.db)                                                                                                                                                                                                                           | Solo para migración     |
| `CHECKPOINTS.md`    | Criterios de "estado final correcto"                                                                                                                                                                                                                                         | Antes de declarar done  |
| `init.ps1`          | Script de verificación (Windows)                                                                                                                                                                                                                                             | Al empezar y al cerrar  |
| `init_Mac.sh`       | Script de verificación (macOS)                                                                                                                                                                                                                                               | En Mac, al empezar      |
| `install_Mac.sh`    | Instalador para Mac Silicon                                                                                                                                                                                                                                                  | En Mac, para setup      |
| `core/`             | Pipeline, módulos base, config, factories                                                                                                                                                                                                                                    | Para implementar        |
| `modules/`          | Procesamiento (audio, TTS, transcripción) + I/O plugins                                                                                                                                                                                                                      | Para implementar        |
| `server/`           | FastAPI, WebSocket, seguridad                                                                                                                                                                                                                                                | Para implementar        |
| `frontend/`         | Dashboard Astro + TypeScript + Tailwind. **F116**: editor visual en `/graph` con React Flow — `lib/graph/` (catálogo, validador, serializador, live status) + `components/graph/` (PipelineCanvas, ModuleNode, InspectorPanel, Toolbar, PipelineGraph) + `pages/graph.astro` | Para implementar        |
| `cli/`              | CLI + TUI (Textual) — cliente HTTP/WS + comandos                                                                                                                                                                                                                             | Para implementar        |
| `tests/`            | Tests pytest + vitest                                                                                                                                                                                                                                                        | Para verificar          |
| `config.yaml`       | Configuración runtime del pipeline                                                                                                                                                                                                                                           | Para entender defaults  |
| `docs/`             | MkDocs, ADRs, guías de arquitectura                                                                                                                                                                                                                                          | Para contexto técnico   |

## 2. Antes de empezar

1. Consulta `python -m harness next` para ver la siguiente feature a trabajar
2. Consulta `python -m harness show <id>` para ver el estado de una feature
3. Ejecuta el script de verificación:
   - **Windows**: `.\init.ps1`
   - **macOS**: `./init_Mac.sh`
   - Si falla, **para y resuelve** antes de tocar código
4. Inicia sesión: `python -m harness session start --notes "描述 de la sesión"`
5. Cambia la feature a `in_progress`: `python -m harness update <id> status in_progress --agent <nombre>`

## 3. Reglas duras

- **Una feature a la vez.** No mezcles cambios de varias tareas.
- **init.ps1 o init_Mac.sh verde para declarar done.** `pytest tests/unit/` pasa siempre.
- **Documenta mientras trabajas** en la sesión de harness, no al final.
- **Deja el repo limpio:** sin prints, TODOs sin contexto, ni archivos temporales.
- **CHECKPOINTS.md completo** antes de cerrar sesión.
- Si te bloqueas, documenta en la sesión de harness con estado `blocked` y para.
- **Código nuevo debe ser cross-platform.** Siempre verificar en Mac si el cambio afecta subprocess, paths o GPU.

## 4. Comandos útiles

```bash
# Verificar entorno
.\init.ps1              # Windows: completo
.\init.ps1 -Quick       # Windows: unit tests rápidos
./init_Mac.sh           # macOS: completo
./init_Mac.sh --quick   # macOS: unit tests rápidos

# Gestión de features (harness)
python -m harness next                    # Siguiente feature a trabajar
python -m harness list --status=pending   # Features pendientes
python -m harness show <id>               # Detalles de una feature
python -m harness stats                   # Estadísticas del proyecto
python -m harness health                  # Validar integridad de la DB
python -m harness update <id> status done --agent <nombre>  # Marcar done
python -m harness audit <id>              # Ver cambios de una feature
python -m harness session start --notes "..."  # Iniciar sesión
python -m harness session end <id> --features "1,2" --notes "..."  # Cerrar sesión

# Tests
python -m pytest tests/unit/ -v              # Unit tests
python -m pytest tests/unit/test_X.py -v     # Test específico
cd frontend && npm test                       # Frontend tests
cd frontend && npm run test:coverage          # Cobertura frontend

# Tipado
python -m mypy core/ server/ --strict        # mypy estricto (F24)
cd frontend && npx tsc --noEmit              # TypeScript check

# Frontend
cd frontend && npm run build:local           # Build + copiar a server/static/

# Servidor (Windows)
.\Start.bat                                   # Iniciar servidor (minimizado)
.\Stop.bat                                    # Parar solo procesos srt2web

# Servidor (macOS)
./start_Mac.sh                                # Iniciar servidor
./stop_Mac.sh                                 # Parar servidor

# Linting
ruff check core/ modules/ server/ tests/     # Lint Python
cd frontend && npm run lint                  # Lint TypeScript
```

## 5. Arquitectura rápida

```
SRT/RTMP/File → AudioExtractor → Transcriber (Whisper) → Translator (Argos)
                                                               ↓
HLS ← CompositeOutput ← AudioMixer ← TTS (Piper) ← SubtitleGenerator
```

**Pipeline** (`core/unified_pipeline.py`): 3 modos (sequential/thread_parallel/asyncio).
Por defecto `thread_parallel` con 2 workers concurrentes. Las estrategias viven en
`core/pipeline/strategies.py` y se instancian vía `core/pipeline/factory.py`.

**Módulos registrados** en `core/app_context.py`:

- `audio_extractor`, `transcriber`, `translator`, `subtitle_generator`, `tts_engine`, `audio_mixer`
- `video_muxer` NO está registrado como módulo del pipeline (es OutputSink, se reporta via `_get_output_module_status()`)

**I/O plugins** (auto-registro via `InputFactory`/`OutputFactory`):

- Inputs: SRT, RTMP, File
- Outputs: HLS, RTMP, SRT, File, Recording, WebRTC (composite delegado)

**Config**: Pydantic (`core/config_schema.py` → `SRT2WebConfig`). `ConfigManager` carga `config.yaml`, valida, permite get/set por dotted keys. Los cambios se propagan via WebSocket (F21).

**Estado reactivo frontend**: `@preact/signals-core` — señales en `lib/store/signals.ts`, efectos DOM en `lib/store/effects.ts`. No usar variables globales mutables fuera de signals.

**Seguridad**: AuthMiddleware (token query param), RateLimiter, SecurityHeaders. WebSocket con autenticación propia. CORS es el middleware más externo.

## 6. Notas técnicas

### GPU / CUDA / Apple Silicon

- `setup_cuda_environment()` en `core/cuda_paths.py` configura PATH para DLLs CUDA (Windows only)
- ONNX Runtime GPU NO soporta cuDNN 9.x. Usar `device: auto` o `cpu` en config
- `HardwareMonitor` (nvidia-ml-py) reporta % uso y memoria GPU (solo NVIDIA)
- **En Mac Silicon**: MPS (Metal Performance Shaders) vía PyTorch, CoreML vía ONNX Runtime, VideoToolbox vía FFmpeg
- `detect_mps()` en `core/hardware.py` — disponible si PyTorch con MPS instalado
- GPU badge en frontend: verde si módulo usa GPU + está running + processed_chunks > 0

### Piper TTS

- `modules/piper_loader.py` usa subprocess persistente (evita bloqueo event loop)
- Modelos en `models/piper/` (17 voces). Default: `es_ES-sharvard-medium`
- Voces ES: Sharvard, Davefx (ES), Claude (MX), Daniela (AR)
- Timeout 90s para carga de modelo. `device: auto` → intenta CUDA/MPS, fallback CPU
- **Heartbeat**: ver F17 — el subprocess necesita mecanismo de detección de bloqueo

### FFmpeg

- Pool de procesos en `core/ffmpeg_pool.py` (max 4, idle 30s)
- `FFmpegWatchdog` en `core/watchdog.py` detecta crashes/hangs
- Keyframe interval OBS mínimo ~10s → chunk duration mínima ~10s
- **En Mac**: FFmpeg vía Homebrew con VideoToolbox para aceleración hardware

### Frontend

- Astro + TypeScript strict + Tailwind CSS v4. Build: `npm run build:local` → copiar a `server/static/`
- WebSocket en `lib/store/signals.ts` + `lib/modules/pipeline-control.ts`
- Reconexión con **exponential backoff + jitter** (F15) — no lineal
- HLS player en `http://localhost:9999/player`
- `ProcessGrid` = 8 cards: Input, Whisper, Translate, TTS, Subtitle, AudioMixer, HLS, Output
- Tema único (dark) — soporte light/dark en F17
- Logs: panel virtual con export JSON/TXT en F16
- **Subtítulos nativos HLS.js (F108)**: `player.ts` activa la primera subtitle track del master playlist vía `player-subtitles.ts` helper. HLS.js carga `subs.m3u8` nativamente, renderiza cues en el mismo `currentTime` que el video — **cero polling, cero lag, cero flicker**. Antes (pre-F108) había un `setInterval` cada 2s que hacía fetch+parse+wipe de todos los cues.

### CLI / TUI (F34)

- `cli/` package completo: `cli/client/` (API + WS), `cli/commands/` (one-shot), `cli/tui/` (Textual)
- Entry point: `srt2web-tui` definido en `pyproject.toml`
- **Comandos one-shot**: `status`, `start`, `stop`, `restart`, `config [get|set]`, `logs [-f] [--level]`, `health`
- **TUI interactiva** (Textual): Header con WS status y reloj, StatusBar con estado/chunks/modo, MetricsPanel con barras CPU/RAM/GPU y sparklines, ModuleGrid 4×2 con 8 cards de módulos, ConfigPanel con vista YAML, LogPanel con logs en vivo
- Atajos: `Space` start/stop, `S` save, `L` toggle logs, `C` config, `O` outputs, `?` help, `Q` quit
- Conexión vía WebSocket con exponential backoff + jitter (mismo patrón frontend)
- Polling adaptativo: 1s (running), 3s (stopped), 5s (error)
- Soporta `--server` y `--token` para servidores remotos con auth
- Ambos frontend web + TUI funcionan simultáneamente

### Testing

- `pytest` con `asyncio_mode = auto`. Fixtures function-scoped en `tests/conftest.py`
- Markers: `unit`, `integration`, `e2e`, `slow`, `security`, `gpu`, `cpu`
- Tests marcados `@pytest.mark.slow`: solo `test_whisper_integration.py` y `test_tts_integration.py` (cargan modelos reales, ~30s+). Se excluyen automáticamente con flags `--quick`/`-m "not slow"`
- Frontend: Vitest. `npm test` en `frontend/`. Cobertura: `npm run test:coverage`
- Objetivo cobertura frontend: 80%+ (ver F25)

### Convenciones de código nuevo

- Python: type hints completos en funciones públicas, `typing.Protocol` para interfaces
- TypeScript: sin `any`, preferir `unknown` + type guard
- CSS: usar variables CSS del tema (`--bg-card`, `--text-prime`, etc.), no colores hardcoded
- No `console.log` en producción — usar el logger configurable del módulo
- **Cross-platform**: Todo subprocess debe usar helper `get_creation_flags()` en vez de `CREATE_NO_WINDOW` directo. Todo path debe usar `pathlib.Path` + `platformdirs`.

## 7. Estado de features

Ver `feature_list.json` para lista completa y estados. Total actual: 130 features.

**Features 1–14**: todas DONE (ciclo Abril–Mayo 2026).

**Features 15–33**: completadas en sesiones Mayo 2026.

**Features 34–54**: features adicionales completadas.

**Features 55–58**: TUI/CLI bugfixes, commands, features y test coverage — todas DONE (sesión 14/05/2026).

**Features 59–65**: Compatibilidad macOS — todas DONE.

**Features 66–102**: refactors, hardening y limpieza de fases 1–3 — todas DONE.

**Feature 103**: Documentación y ADR drift — DONE (02/06/2026).

**Feature 104**: Bugfixes de UI en dashboard (LogPanel, presets, shortcuts, docs, SRT URL, System Metrics) — DONE (02/06/2026).

**Features 105–107**: bugs reportados en sesiones 2026-06-02 y 2026-06-03:

- **F105** ✅ DONE: composite_output.\_schedule_reconnect Timer sobrevivía a stop(); cancelado ahora
- **F106** ✅ DONE: "Piper TTS ignora la voz" — **2 bugs distintos** producían el mismo síntoma. Bug 1: PUT /api/config 400 por type='webplayer' (OutputTypeEnum solo acepta 'web'). Bug 2: race condition en PiperSubprocessManager.\_send_command entre synth+heartbeat. Fix: `_normalize_output_type` en outputs route + `_canonical_types` en OutputFactory + `_cmd_lock` serializando \_send_command. 9 tests en `test_f106_piper_voice.py`.
- **F107** ✅ DONE: "Cannot start pipeline in state: starting" — **3 bugs distintos** en `UnifiedPipeline.start()` producían el mismo síntoma. Bug 1: mensaje mentiroso ("60 seconds" mientras el join era 120s). Bug 2: state huérfano en STARTING tras timeout/excepción; `reset_error_state()` solo maneja ERROR, así que ningún retry funcionaba hasta reiniciar el server. Bug 3: excepciones dentro del init thread se tragaban silenciosamente — usuario siempre veía "timed out" aunque el init hubiera crash instantáneamente. Fix: `_DEFAULT_INIT_TIMEOUT_S=300` (configurable via `SRT2WEB_PIPELINE_INIT_TIMEOUT`); `__init__` trackea `_init_thread` y `_init_error`; `start()` rechaza concurrente con "already in progress", setea ERROR en timeout/excepción, reraisea `PipelineError(__cause__=init_error)` para que el error real llegue al usuario. 11 tests en `test_f107_pipeline_init_timeout.py`.

**Feature 108**: Subtítulos desincronizados del video en sesiones largas / webplayer pausado (2026-06-04):

- "Subtítulos se desincronizan del video" reportado tras varios minutos de stream. 3 capas de causas raíz identificadas:
  - **Capa 1 (principal)**: `player.ts` hacía `setInterval(loadSubtitles, 2000)` que fetch+parse+wipe-and-replace TODAS las cues cada 2s. Produjo lag 0-2s oscilante (cue del chunk N+1 llega al HLS player instantáneo, el cliente tarda hasta 2s), flicker visible (cue activa desaparece/vuelve), y costo creciente (rolling window de 2000 cues re-creadas cada poll).
  - **Capa 2 (código muerto)**: `SubtitleSyncMonitor.check_sync()` se creaba en `app_context.py` pero nunca se llamaba en el path runtime. El flag `enable_drift_detection` se ignoraba.
  - **Capa 3 (drift por mtime)**: `srt_input.py:586-591` ajusta `cumulative_duration` con deltas de mtime acotados a `[0.5, 2*chunk_duration]`. Pequeño sesgo sistemático se acumula: 180 chunks × 0.05s = 9s en 30 min.
- **Fix**: Reemplazar polling con HLS.js native subtitle track.
  - **Backend**: per-chunk VTT fragments con timestamps **media-relative** (`subs_seg_NNNNNN.vtt`), `subs.m3u8` HLS media playlist (`EXT-X-VERSION:3`, atomic rewrite, rolling window), master playlist URI switched to `/subtitles/subs.m3u8`, `HLSOutput.start()` pre-crea `subs.m3u8` vacío. `SubtitleSyncMonitor` ahora se invoca por chunk con `check_sync(audio_wall_clock_ms, first_cue_media_ms)` y aplica blend suavizado `0.7*old + 0.3*new` con clamp en `|deviation|>=0.5`. Legacy `subs.vtt` rolling sigue produciéndose para `webrtc_engine.py` y `recording_output.py`.
  - **Frontend**: eliminado polling (`parseVTT`, `loadSubtitles`, `startSubtitlePolling`); `player-subtitles.ts` helper con `activateFirstSubtitleTrack(hls, {preferredLang: "es"})` en MANIFEST_PARSED, `onSubtitleTrackListChange` re-activates on every manifest re-parse, `disableSubtitles` on disconnect. HLS.js carga `subs.m3u8` nativamente, renderiza cues en el mismo `currentTime` que el video.
- **Tests**: 42 backend en `test_f108_subtitle_hls_sync.py` (fragment media-relative, playlist target_duration/media_sequence, rolling window, drift monitor blend+clamp, master playlist URI selection, legacy subs.vtt compat) + 18 frontend en `player-subtitles.test.ts` (preferred lang exact/prefix/fallback, closed-captions filter, disable, unsubscribe). Verificación: 42+18 pass, 1183 unit tests pass (xdist), mypy --strict 0 errores, tsc 0 errores, ruff clean.
- **2 e2e test failures pre-existentes** (`test_links_to_hls_stream`, `test_subtitle_refresh_interval`): confirmado con `git stash` que fallan ANTES de F108 — references "master.m3u8"/"setInterval" en `server/static/player.html` que ya no está bundled.

**Feature 117**: Fix critical bugs — DONE (11/06/2026). hardware.py GPU auto-detect no-op, Dockerfile COPY path wrong, config_manager non-atomic save.

**Feature 118**: Security hardening — DONE (11/06/2026). PBKDF2-HMAC-SHA256 (600K iter), removed hardcoded JWT fallback, timing-safe compare, AuthMiddleware 503.

**Feature 121**: Password policy — DONE (11/06/2026). validate_password_strength(), create_user/setup_first_admin return tuple, change_password(), PUT /api/auth/password.

**Feature 122**: Account lockout — DONE (11/06/2026). 5 failed attempts → 30 min lockout, auto-expiry, unlock endpoint.

**Feature 150**: PTS-based subtitle sync — DONE (23/06/2026). Elimina drift mtime (~9s/30min) usando PTS/PCR del contenedor MPEG-TS.

**Feature 167**: Unificar renderizado de subtítulos (eliminar dual path) — DONE (27/06/2026). Eliminado polling `setInterval(loadSubtitles, 2000)` y SubtitleRenderer; única ruta nativa HLS.js con `activateFirstSubtitleTrack()` + `forceSubtitleTrackMode()`.

**Feature 168**: Aplicar corrección de drift en el pipeline — DONE (27/06/2026). `SubtitleGenerator._do_process()` llama `_drift_monitor.check_sync()` cada chunk, aplica correction factor a `pipeline_delay` y `shifted_start`. `enable_drift_detection: true` por defecto.

**Feature 169**: ABR adaptativo en HLS — DONE (27/06/2026). `BitrateProfile` + `bitrate_ladder` en `WebOutputConfig` con 3 perfiles (500K/480p, 1.5M/720p, 3M/1080p). Master playlist genera `EXT-X-STREAM-INF` por perfil.

**Feature 170**: Pipeline reactivo (auto-adaptación a carga) — DONE (27/06/2026). 4 subsistemas:

- **(a) EMA reactivo**: smoothing factor configurable (`0.4` default), reset brusco (`reset_factor=0.7`) cuando `ratio > reset_threshold (0.3)`.
- **(b) Concurrencia dinámica**: `_adaptive_monitor_loop` cada 5s lee CPU/GPU via `HardwareMonitor`, ajusta `_concurrency_target`. Umbrales: CPU>80% o GPU>85% reduce; CPU<40% y GPU<50% aumenta.
- **(c) Backpressure**: `_input_thread_loop` frena si `output_queue` o `chunk_queue > buffer*0.7` con `sleep` progresivo hasta 0.5s.
- **(d) Chunk duration adaptativo**: cada `adaptation_interval_chunks` (10) en `_output_thread_loop`, si `avg_proc_time/chunk_duration > 0.8` aumenta chunk (×1.5, max 60s); si < 0.3 reduce (/1.5, min 2s). Propaga via `set_chunk_duration()` en `BaseInput`.
- **Config**: `AdaptiveConfig` (14 campos) en `config_schema.py` + `config.yaml`.

**Feature 171**: Feedback loop player → servidor — DONE (27/06/2026). `PlayerFeedbackMonitor` en `core/player_feedback.py` con thresholds configurables. Endpoint `WS /ws/player-feedback` recibe buffer health, stall, bandwidth desde el player. Adaptación: stall o buffer<2s → reduce chunk_duration×0.5 y concurrencia→2; buffer>15s por >60s → restaura defaults. Frontend: `player-feedback.ts` conecta WS dedicado, hooks en `BUFFER_APPENDED`, `STALLED`, `LEVEL_UPDATED` de HLS.js. 238/238 tests frontend, todos los módulos Python OK.

**Siguiente pendiente**: F172 por definir — posiblemente tuning de latencia total <20s o feedback loop bidireccional completo.

## 8. Historial compacto (post-Abril 2026)

### 10/08 — Frontend type safety audit (F180)

- **F180 cerrado**: eliminados `any` y casteos sin validación en producción:
  - `apiCall()`: `method: string` → union `HttpMethod` ("GET"|"POST"|"PUT"|"DELETE"|"PATCH"|"HEAD"|"OPTIONS"). `ensureCsrfToken()` validaba con type guard propio y `unknown` (antes `data.csrf_token` con any implícito).
  - `WSClient.send()`: `data: unknown` → `{ type: string; [key: string]: unknown }` (el backend despacha por `type`, cada frame debe declararlo). Test de api ajustado.
  - Eventos HLS.js con type guards: nuevo `frontend/src/lib/hls-guards.ts` con `isHlsErrorData()`/`isHlsLevelUpdatedData()` (interfaces `HlsErrorData`/`HlsLevelUpdatedData` movidas de player.ts). `player.ts` usa los guards en LEVEL_UPDATED y ERROR en vez de `data as X`.
  - `preferredLang` externalizado: `DEFAULT_SUBTITLE_LANG = DEFAULTS.SUBTITLE_LANG` en `lib/constants.ts`; `player.ts` ya no hardcodea `"es"`.
  - `MetricsCard.astro`: `(pipelineStatus.value as any)?.chunks_failed` → `pipelineStatus.value?.chunks_failed` (Status ya tipa `chunks_failed?`).
  - `OutputManagerCard.astro`: props `any[]`/`(config: any)` → `OutputStatus[]`/`AnyOutputConfig` (import de `lib/types`).
  - `DocsSearch.astro`: `pagefind: any` → interfaz `PagefindInstance` con shape-check al importar.
- **Verificación**: `tsc --noEmit` 0 errores; `npm test` 248 passed, 8 skipped (8 nuevos en `hls-guards.test.ts`); `npm run lint` 0 errores (3 warnings pre-existentes); `build:local` 6 páginas OK — build-all falla solo por `mkdocs` no instalado en este entorno (pre-existente, docs).
- Detalles en `harness.db` (sesión #33).

### 10/08 — Type safety audit (F179)

- **F179 cerrado**: eliminados los últimos `Any` con tipos concretos y código huérfano:
  - `modules/tts_engine.py`: `_piper_manager: Any` → `PiperSubprocessManager | None` (import vía TYPE_CHECKING; el lazy import real en `_init_piper` se mantiene → cero carga de onnxruntime en import).
  - `server/routes/outputs.py`: `_get_composite(pipeline: Any) -> Any` → `(pipeline: UnifiedPipeline) -> CompositeOutput` (imports vía TYPE_CHECKING; `from __future__ import annotations` para evaluación diferida). `status: dict[str, Any] | ModuleStatus` en fallback de sink simple. En `server/api_routes.py` eliminado `cast(dict[str, Any], ...)` redundante.
  - TUI screens (4): `api_client: Any` → `APIClient` en `input_control.py`, `presets_screen.py`, `recordings_screen.py`, `module_detail.py` (import de `cli.client.http_client`).
  - `core/module_base.py:93-136`: eliminado docstring huérfano + `MemoryManager.to_dict()` roto (referenciaba `self.name/state/extra` inexistentes, 0 usos en repo).
  - `core/types.py`: eliminada dataclass duplicada `SystemMetrics` (nadie la importaba; la canónica Pydantic vive en `core/schemas.py:67`).
- **Verificación**: mypy --strict sobre los 9 archivos tocados + `core/ server/ modules/` — único error restante `core/paths.py:163` (pre-existente); mypy `cli/` solo 3 errores pre-existentes en `cli/tui/app.py` (reactive assignments, no tocado); ruff 0 en los 9; 63 tests impactados pasan (test_stability, test_tts_engine, test_f106_piper_voice, test_f183_f187_startup_races); 25 fallos tests/cli confirmados pre-existentes vía git stash (fallan igual en HEAD); imports de todos los módulos editados OK.
- Detalles en `harness.db` (sesión #32).

### 10/08 — Fixes de arranque, races paralelas y dashboard (F183–F187)

- **F183 cerrado** (start no bloqueante): `POST /api/start` bloqueaba el event loop ~41s (import argos 31.7s + whisper + Piper lazy). Fix: `await asyncio.to_thread(pipeline.start, ...)` en `server/routes/pipeline.py` (el endpoint responde al instante); `core/warmup.py` nuevo — daemon thread que pre-carga argos/whisper al arrancar el server (idempotente, skip en testing); `modules/tts_engine.py` arma el subproceso Piper en thread `tts-warmup-{voice}` (best-effort). Primer start pasa de ~41s a segundos de respuesta inmediata del API.
- **F184 cerrado** (races paralelas, eco + subtítulos que desaparecen):
  - **TTS doble subproceso**: lazy-load sin lock → 2 workers spawn eran 2 subprocesos Piper (log: doble load 23:06:05/06 → audio repetido 10-20s). Fix: `_load_lock` threading.Lock + `_ensure_piper_loaded()` con doble-check; si `stop()` ocurre durante la carga se mata el manager y se resetea.
  - **Subtítulos fuera de orden**: workers en paralelo entregaban chunks desordenados a `SubtitleGenerator`, que escribía en orden de llegada → playlist rolling saltaba fragmentos (subtítulos desaparecían). Fix: buffer `_pending` + `_drain_pending_locked()` en `modules/subtitle_generator_pkg/__init__.py` — `idx == expected` escribe directo (cero latencia en orden), `idx > expected` se bufferiza, `idx < expected` se descarta (duplicado/stale), gap `> expected+128` (MAX_PENDING) escribe con warning (escape tras watchdog restart). Fragmentos estrictamente ascendentes.
  - **Crossfade no atómico**: `AudioMixer._prev_end_sample` leído/escrito sin lock → cola del chunk tardío sangraba en la cabeza del previo. Fix: `_mix_lock` alrededor del bloque read-blend-write.
- **F185 cerrado** (SRT congelado tras watchdog restart): FFmpeg renumera `chunk_%06d.ts` desde 0 en cada proceso nuevo, pero `_last_chunk_index` quedaba alto → chunks nuevos ignorados hasta alcanzar el contador. Fix: `_start_ffmpeg_process()` resetea `_last_chunk_index = -1` y purga `chunk_*.ts` antes de lanzar FFmpeg.
- **F186 cerrado** (dashboard grid irregular): CSS grid `repeat(auto-fit, minmax(280px, 1fr))` (era flex-wrap → 4/3/1 layout), móduloMap sin el replace roto, `mod.extra.encoder_mode` (snake_case) en las cards, `collapsible-card` añadido en las 9 cards.
- **F187 cerrado**: `stop()` lanzaba WinError 10042 (WSAEOPNOTSUPP) en `setsockopt(SO_LINGER)` sobre socket UDP → bind se skipeaba → "port still in use" ×3 + taskkill agresivo. Fix: `with contextlib.suppress(OSError)` (SO_LINGER es opcional).
- **Tests**: `tests/unit/test_f183_f187_startup_races.py` (17 tests: warmup, concurrencia `_ensure_piper_loaded`, orden de fragmentos con threads, crossfade atómico con contenido verificado, reset de índice+purge, SO_LINGER falla/soporta). Verificación: 1594 passed; los 45 failed son todos pre-existentes confirmados vía `git stash` (auth/JWT "HMAC key must not be empty", WebRTC, mypy `core/paths.py:163`, f108 master playlist ×2); mypy --strict sin errores nuevos (solo el pre-existente); ruff limpio en archivos tocados; frontend 240 tests passed, tsc 0 errores, lint 0 errores.
- Detalles en `harness.db` (sesión #29).

### 13/06 — Refactor: extraer loops a strategies (F132)

- **F132 cerrado**: `unified_pipeline.py` reducido de 1106 → 599 líneas (-46%). Los 5 métodos de loop (sequential, input/worker/output threads, async) movidos a `core/pipeline/strategies.py` con `PipelineContext` dataclass para compartir estado. `pipeline_helpers.py` nuevo con output status y reconfigure. Lazy imports vía `importlib` para romper dependencia circular. 48 tests pipeline pasan, mypy --strict 0 errores en 3 archivos.
- Detalles en `harness.db` (sesión del día).

### 07/06 — Editor visual de pipeline en /graph (F116)

- **F116 cerrado**: segunda versión del dashboard en `/graph` basada en React Flow. Cada módulo se ve como un nodo con handles tipados (video / audio / transcript / subtitles) en colores. Conectando nodos el usuario define el pipeline; la topología se valida y se aplica como preset al backend.
- **Stack añadido**: `@astrojs/react@^4`, `react@^18`, `react-dom@^18`, `@xyflow/react@^12`, `@testing-library/react`. Astro config: integración `react()` + `manualChunks` para `vendor-xyflow` y `vendor-react` (convive con Preact signals del resto del frontend).
- **Catálogo de 8 nodos**: input, audio_extractor, transcriber (Whisper), translator (Argos), subtitle_generator, tts_engine (Piper/Edge), audio_mixer (admite 2 entrantes audio-orig + audio-dub), output (admite 3: video + audio + subtitles).
- **Validador `isValidConnection`**: rechaza tipo mismatch, ciclos (`getOutgoers`), exceso de entrantes por nodo, source sin salidas / sink sin entradas.
- **Topología**: DAG lineal o con un único branch convergente en `audio_mixer`. `validateTopology` valida + `graphToConfig` genera `Partial<Config>` listo para `PUT /api/config`.
- **Toolbar**: Start, Stop, Apply, Reset, Save preset, Load preset (sobre `POST /api/presets` existente).
- **Inspector**: auto-genera form desde `configFields` (boolean / select / number / text). Para `input` y `output` muestra "configurar fuera del grafo".
- **Live status**: `useLiveModuleStatus` hook con polling `GET /api/modules` cada 2s + WebSocket `WS /ws/logs` para detectar el nodo activo y pintar un pulse verde de 1.5s.
- **Astro page**: `frontend/src/pages/graph.astro` con `<PipelineGraph client:only="react" />` dentro de `BaseLayout`. Build estático → `server/static/graph/index.html`.
- **Tests**: 5 archivos nuevos — `nodeCatalog.test.ts` (10), `typedEdge.test.ts` (15), `serialize.test.ts` (17), `ModuleNode.test.tsx` (6), `InspectorPanel.test.tsx` (7). Total: 249/249 pass.
- **Verificación**: `tsc --noEmit` 0 errores, `npm run build` 6 páginas OK (`/graph/index.html` generado), `mypy --strict core/ server/ modules/` 0 errores, `npm run lint` sin warnings nuevos.
- **No se toca**: `index.astro`, `index_new.astro`, `core/`, `modules/`, `server/` (salvo `tests/unit/test_logging_setup.py` que se ejecutó para verificar subset del backend).
- Detalles completos en `harness.db` (sesión del día).

### 11/06 — Fix critical bugs (F117) + Security hardening (F118)

- **F117 cerrado**: 3 bugs críticos — hardware.py GPU auto-detect no-op (wrong key lookup), Dockerfile runtime COPY path wrong, config_manager.py non-atomic save on Windows
- **F118 cerrado**: Security hardening — PBKDF2-HMAC-SHA256 (600K iter) for passwords, removed hardcoded JWT fallback, `secrets.compare_digest` for timing-safe compare, AuthMiddleware returns 503 when unconfigured. Auto-migration from legacy SHA-256 hashes. `SRT2WEB_TESTING` env var bypass for test suite.
- **Tests**: 1271 unit tests pass, 0 failures; mypy --strict 0 errors
- Detalles completos en `harness.db` (sesión del día)

### 04/06 — Subtítulos desincronizados F108

- F108 cerrado: 3 capas de causas (polling+wipe, monitor muerto, drift mtime) sustituidas por HLS.js native subtitle track.
- Detalles completos en `harness.db` (sesión del día)

### 03/06 — Pipeline init timeout (F107)

- F107 cerrado: "Cannot start pipeline in state: starting" eran **3 bugs distintos** en `UnifiedPipeline.start()`:
  - **Bug 1 (mensaje mentiroso)**: el `init_thread.join(timeout=120)` esperaba 120s pero el `PipelineError` decía "60 seconds". Copy-paste viejo.
  - **Bug 2 (state huérfano)**: cuando el init thread tardaba más que el timeout, `start()` lanzaba `PipelineError` pero `_state` quedaba en `STARTING` para siempre. `reset_error_state()` solo maneja `ERROR`, no `STARTING` → ningún retry funcionaba sin reiniciar el server.
  - **Bug 3 (excepciones tragadas)**: `run_init()` envolvía `loop.run_until_complete(self.initialize())` con un try/except que descartaba la variable de captura. Si init crash instantáneo, usuario siempre veía "timed out" — el error real nunca llegaba.
- **Fix**: `_DEFAULT_INIT_TIMEOUT_S=300` (antes 120s, configurable via `SRT2WEB_PIPELINE_INIT_TIMEOUT`); `__init__` trackea `_init_thread` y `_init_error`; `start()` rechaza start concurrente con "already in progress", setea ERROR en timeout/excepción, reraisea `PipelineError(__cause__=init_error)` para que el error real llegue al usuario.
- **Log real que confirmó el bug**: `21:59:13 Starting` → `22:01:14 Pipeline initialization timed out after 60 seconds` → `22:01:23 Cannot start pipeline in state: starting`.
- **Tests**: 11 nuevos en `tests/unit/test_f107_pipeline_init_timeout.py` — env-var override, timeout→ERROR, exception surfacing, retry-after-error, concurrent rejection, happy path, already-initialized skip.
- **Verificación**: 11/11 pasan en 3.3s; mypy --strict 0 errores; ruff clean; sin regresiones. 4 fallos pre-existentes en main confirmados via git stash (no introducidos por F107).
- Detalles completos en `harness.db` (sesión del día)

### 02/06 — Bugfixes UI dashboard (F104) + stop/reconnect (F105) + Piper voice (F106)

- F104 cerrado: 6 bugs en dashboard corregidos — LogPanel, presets, shortcuts, docs, SRT URL, Metrics
- F105 cerrado: `composite_output._schedule_reconnect` Timer sobrevivía a `stop()` → reanimaba outputs parados. Fix: tracking dict + `_stopped` flag + cancel en `stop()`
- F106 cerrado: "Piper TTS ignora la voz" eran en realidad 2 bugs distintos:
  - **Bug 1 (config 400)**: `OutputFactory.resolve_type('HLSOutput')` devolvía `"webplayer"` (primer alias registrado) y `_sync_outputs_to_config` lo guardaba tal cual. `OutputTypeEnum` solo acepta `"web"` → PUT /api/config fallaba 400 y la UI mostraba "voz no cambió". Fix: `_canonical_types` en `OutputFactory` + `_normalize_output_type` en outputs route (defensa en 2 capas).
  - **Bug 2 (Piper crash)**: `PiperSubprocessManager._send_command` no serializaba concurrentes; synth + heartbeat (cada 30s) se peleaban por el mismo `proc.stdout.readline()` y producía "Invalid JSON response: Extra data: line 1 column 22652". Subprocess "murió" pero el código no recargaba → chunks subsiguientes sin audio. Fix: `_cmd_lock = threading.Lock()` envolviendo todo el ciclo send→read→parse.
  - 9 tests en `tests/unit/test_f106_piper_voice.py`. Honrando F106 mitigation: NO se tocó `tts_engine.py` (la chain ya funcionaba).
- Detalles completos en `harness.db` (sesión del día)

### 14/05 — Plan de compatibilidad macOS

- Análisis completo del código para soporte Mac Silicon (ARM64)
- Identificados 7 bloques de trabajo: init script, subprocess, GPU, deps, paths, TUI terminal, docs
- ~50 ocurrencias de código platform-specific (CREATE_NO_WINDOW, nvidia-smi, paths Windows)
- Mac scripts existentes (install_Mac.sh, start_Mac.sh, stop_Mac.sh) pero incompletos

### 14/05 — CLI + TUI interactiva (F34)

- `cli/` package completo: client HTTP/WS, 5 one-shot commands, TUI Textual
- `srt2web-tui` entry point con 6 subcomandos: status, start/stop/restart, config, logs, health, tui
- TUI replica dashboard web: header, status bar, metrics, module grid 4×2, config panel, log panel
- WebSocket con exponential backoff + jitter para logs en vivo
- Polling adaptativo 1s/3s según estado del pipeline
- Tests unitarios para modelos de datos y comandos
- Ambos frontend web + TUI funcionan simultáneamente

### 12/05 — Plan de mejoras F15-F29

- Análisis completo del repo: rendimiento, estabilidad, mantenibilidad, arquitectura, UX
- Actualización de AGENTS.md y feature_list.json con 15 nuevas features
- Orden de implementación priorizado por impacto/riesgo

### 27/04 — Documentación MkDocs

- 4 docs creados (mkdocs.yml, index, deployment, architecture, contributing)
- Diagramas Mermaid para arquitectura visual
- GitHub Actions CI/CD + pre-commit hooks

### 22/04 — Arreglar Frontend Outputs

- OutputCard + OutputsPanel inline (sin modal)
- ProcessGrid con 8 cards uniformes
- Formulario de creación expandible inline

### 14/04 — Refactoring Mantenibilidad

- `main.py` reducido 547→430 líneas (-21%)
- Módulos nuevos: `core/cuda_paths.py`, `core/logging_setup.py`, `frontend/clock.ts`
- Logging con file rotation + WebSocket broadcast

### 12/04 — Suite Tests Limpia

- 527 tests passing, 0 failing. Fixes en api_routes, config_manager, unified_pipeline
- Config low-latency: chunk=10s, segment=10s, list_size=2

### 01-02/04 — Latency Reduction

- Audio mixing: FFmpeg→numpy (1.2s→20ms, 60x)
- Piper TTS: GPU via subprocess persistente
- Latencia total ~12-15s. OBS keyframe constraint ~10s

### 30/03 — Fix Pipeline Data Flow

- Fix PipelineData creation (dict→dataclass syntax en SRT input)
- Logging persistente con RotatingFileHandler (10MB, 3 backups)
- cuDNN 9.x incompatible con ONNX Runtime GPU (issue #23519)

---

### 12/08 — Subtítulos estables: ventana subs alineada al video + fix índice chunk silencioso (F193)

- **Síntoma**: subtítulos se saltan trozos, a veces no salen, audio traducido va perfecto.
- **Causas raíz (4)**:

  1. Subs 1 fragmento por delante del video (sin ancla tras eliminar sync F167).
  2. `#EXT-X-PLAYLIST-TYPE:EVENT` en `subs.m3u8` (rolling window + seq avanzando = contradictorio, RFC 8216: EVENT nunca recorta).
  3. EXTINF dispares: video 12.043/6.043 vs subs 11.4; TARGETDURATION subs 13.
  4. **Bug crítico** `if not text: return data` en `__init__.py:204`: chunk sin voz no avanza `_last_chunk_index` → chunks con texto siguientes atrapados en buffer pending "out-of-order" → subs congelados ~128 chunks (~10 min).

- **Fix v1 (backend, commit ad6bb28)**:

  - `_fragment_writer.py`: sin EVENT; ventana y EXTINF alineados con `stream.m3u8` del video (patrón `_detect_video_media_seq` de F108 reintroducido, lee EXTINF reales del video como fuente compartida; fallback intacto si no hay stream.m3u8).
  - `__init__.py`: chunk sin texto ya no rompe la secuencia — escribe fragmento vacío (WEBVTT sin cues) y avanza el índice, con `is_loop` (pause loop) chequeado antes.
  - `hls_output.py`: comentario muerto 531-532 actualizado.
  - +11 tests de regresión en `test_f108_subtitle_hls_sync.py`.

- **Fix v2 (backend, tras "reiniciado y va mejor pero sigue fallando")**:

  - Evidencia en vivo: video `MEDIA-SEQUENCE:15` (seg 15–20) vs subs `MEDIA-SEQUENCE:11` (frag 11–19) — 4 fragmentos fantasma en la base.
  - F193 v1 recortaba solo el **techo** de la ventana de subs (`<= max_video_idx`) pero no la **base**.
  - `_fragment_writer.py`: intersección completa de ventanas `[min_video_idx, max_video_idx]` (replica la ventana del video en AMBOS extremos). Sin solapamiento (p.ej. tras restart que renumera segmentos), sirve playlist vacío anclado a la `MEDIA-SEQUENCE` del video en vez de cues stale. Nuevo helper `_write_empty_playlist()`.
  - `test_f108_subtitle_hls_sync.py`: +3 tests de regresión (base alineada al video, playlist vacío sin solapamiento, EXTINF del video tras recorte de base).
  - Verificación: 46/46 (f108 + subtitle_generator); 17/17 (f183-f187); mypy 0 errores; ruff 0 errores; pre-commit verde.

- **Fix frontend (watchdog agresivo)**:

  - Síntoma residual: "aparecen y desaparecen al recargar" — HLS.js resetea TextTrack.mode a "hidden" tras cada recarga de playlist de subtítulos.
  - `player.ts`: watchdog original solo en `timeupdate` (~4 Hz = 250ms gaps) + handlers de eventos (SUBTITLE_TRACK_LOADED, SUBTITLE_TRACKS_UPDATED, LEVEL_UPDATED) que pueden disparar ANTES del reset.
  - **Nuevo watchdog triple**: `timeupdate` + intervalo agresivo 200ms (`SUBTITLE_WATCHDOG_INTERVAL_MS`) + evento `addtrack` (dispara cuando HLS.js crea nuevos `<track>` tras playlist reload). Fuerza `mode="showing"` inmediatamente en los 3 vectores.
  - `stopSubtitleWatchdog()` limpia interval + removeEventListener de `addtrack`.

- **Fix frontend r2 (auditoría hls.js 1.5.7)**: al leer el bundle real de hls.js se confirmó que `toggleTrackModes` (el único motor de modo de TextTrack) solo corre desde `setSubtitleTrack`/setter `subtitleDisplay`, y que **en un reload de playlist hls.js NO toca el mode** — el "hidden" lo crea el propio TimelineController al crear `<track>` nuevos (`media.addTextTrack(...)` con `mode='disabled'`, línea ~21827) cuando el nivel/subtitle group cambia tras re-parse del master. Además `_appendCues` DROPEA cues si el track está `'disabled'` en el momento de parse. Correcciones:

  - **Bug `addtrack`**: el evento `addtrack` se dispara sobre `video.textTracks` (TextTrackList), NO sobre el elemento `<video>` — el listener anterior era código muerto. Ahora: `videoEl.textTracks.addEventListener("addtrack", ...)` con handler con nombre y `removeEventListener` correcto en `stop()` (antes se intentaba quitar con `_subtitleWatchdogHandler` → leak).
  - **Hardening `SUBTITLE_TRACKS_UPDATED`**: si `hls.subtitleTrack === -1` (hls.js pierde la selección interna tras re-parse del master; SubtitleStreamController deja de cargar subs.m3u8 → no llegan cues aunque el track DOM esté `showing`) → se re-activa con `activateFirstSubtitleTrack`. Si no, se fuerza mode.
  - **Ruido**: `forceSubtitleTrackMode` ahora devuelve nº de tracks cambiados y loguea un summary de una línea (`idx:mode/cues | ...`); el intervalo solo loguea cuando cambia algo (antes logueaba 5×/seg en debug).
  - **Tests**: +4 en `player-subtitles.test.ts` (retorno cambiado, hidden→showing, capa captions/metadata ignorados, sin tracks). Verificación: 252 passed | 8 skipped, `tsc --noEmit` 0, eslint 0, `build:local` 6 páginas OK (fallo solo en mkdocs, pre-existente), código verificado en bundle `player.astro_astro_type_script_index_1_lang.*.js`.

- **Estado actual**: Backend OK (MEDIA-SEQUENCE coinciden, EXTINF idénticos). Frontend construido con fix r2. **Pendiente verificación en vivo** — con OBS + server: revisar logs WS del player ("Subtitle selection lost after track update - re-activating", "textTrack added", summary de tracks) para confirmar si el mecanismo era mode reset (watchdog lo atrapa) o selección interna perdida (re-activación lo cura).
- \*\*Detalles en `harness.db` (sesión #35, feature F193).

## 9. Plan de implementación macOS (F59–F65)

Basado en auditoría de código del 14/05/2026. ~50+ ocurrencias de código platform-specific, 3 scripts Mac existentes pero incompletos.

### Orden de implementación sugerido

```
F59 → F60 → F62 → F63 → F61 → F64 → F65
       ↓
    F55-F58 (TUI/CLI en paralelo, independiente)
```

Razonamiento:

- **F59 primero**: init_Mac.sh permite verificar el entorno antes de cualquier cambio
- **F60 segundo**: Subprocess hardening evita crashes en Mac al ejecutar el pipeline
- **F62 tercero**: Dependencias correctas necesarias para todo lo demás
- **F63 cuarto**: Paths cross-platform necesarios para cache/config/logs
- **F61 quinto**: GPU acceleration (depende de F62 para deps correctas)
- **F64 sexto**: TUI terminal (puede probarse con F59 habilitado)
- **F65 último**: Documentación y CI cierran el ciclo

Las TUI features (F55-F58) son **independientes** y pueden implementarse en paralelo.

---

### F59 — Script init_Mac.sh de verificación del harness (Alta prioridad)

**Qué**: Crear `init_Mac.sh` como equivalente funcional de `init.ps1` para macOS.

**Problema**: No hay script de verificación para Mac. `install_Mac.sh` solo instala pero no verifica.
`check_mac_deps.py` existe pero no es un harness ejecutable.

**Archivos**: `init_Mac.sh` (nuevo), `scripts/check_mac_deps.py` (mejorar output)

**Riesgo**: Bajo. Script nuevo que no modifica código existente.

**Acceptance**:

- `./init_Mac.sh` exit code 0 = entorno listo
- Verifica Python 3.12, venv, pip deps, feature_list.json
- Ejecuta `pytest tests/unit/ -q --tb=short -m "not slow"`
- Ejecuta mypy core/ server/ (informativo)
- `--quick` flag salta mypy

### F60 — Hardening cross-platform de subprocess (Alta prioridad)

**Qué**: Crear helper `get_creation_flags()` y reemplazar todos los accesos directos a `subprocess.CREATE_NO_WINDOW`.

**Problema**: 31+ ocurrencias de `CREATE_NO_WINDOW`. Varias sin guardia `sys.platform == "win32"`.
En macOS, `subprocess.CREATE_NO_WINDOW` no existe → `AttributeError` y crash.

**Archivos**: `core/subprocess_utils.py` (NUEVO helper), más 14 archivos a modificar
(listados en feature_list.json F60).

**Riesgo**: **Alto** — toca 14+ archivos. Mitigación: cambios mecánicos uno a uno, cada uno testeable.

**Acceptance**:

- `get_creation_flags()` retorna 0 en macOS/darwin
- Cero `AttributeError` por `CREATE_NO_WINDOW` en macOS
- Tests unitarios para el helper

### F61 — Aceleración GPU Apple Silicon (Alta prioridad)

**Qué**: Verificar MPS (PyTorch), CoreML (ONNX Runtime), VideoToolbox (FFmpeg) en Mac.

**Problema**: `hardware.py` detecta MPS pero no hay tests de integración en Mac.
`hardware_monitor.py` usa pynvml que no existe en Mac. Sin badge MPS en frontend.

**Archivos**: `core/hardware.py`, `core/hardware_monitor.py`, `core/ffmpeg_utils.py`,
`install_Mac.sh`, `frontend/*`, `tests/integration/test_hardware_mac.py` (NUEVO)

**Riesgo**: Medio. GPU acceleration es deseable pero no crítica (CPU fallback existe).

**Acceptance**:

- MPS, CoreML, VideoToolbox detectados correctamente
- Fallback graceful a CPU si no hay GPU
- Badge 'MPS' en frontend para Mac

### F62 — Flujo de dependencias para Mac (Media prioridad)

**Qué**: Mejorar `install_Mac.sh` para instalar grupos opcionales (cli, dev) y dependencias platform-specific.

**Problema**: `install_Mac.sh` solo instala `config/requirements.txt` (core). CLI/TUI no se instalan.
`nvidia-ml-py` es core dep pero no funciona en Mac.

**Archivos**: `install_Mac.sh`, `config/requirements.txt`, `pyproject.toml`, `docs/*`

**Riesgo**: Bajo.

**Acceptance**:

- `install_Mac.sh` instala core + processing + tts + cli + dev
- Instala `onnxruntime-silicon` (no `onnxruntime-gpu`)
- No instala `nvidia-ml-py`
- `srt2web-tui --help` funciona post-instalación

### F63 — Paths cross-platform (Media prioridad)

**Qué**: Estandarizar paths usando `platformdirs` para cache, config y logs en Mac.

**Problema**: `model_cache.py` usa `%LOCALAPPDATA%` (Windows). `cuda_paths.py` es Windows-only.
No hay detección de directorios estándar en Mac (`~/Library/Caches/`, `~/.config/`).

**Archivos**: `core/model_cache.py`, `core/cuda_paths.py`, `core/paths.py` (NUEVO),
`core/logging_setup.py`, `pyproject.toml` (platformdirs dep)

**Riesgo**: Medio. platformdirs es librería madura. Compatibilidad hacia atrás mantenida.

**Acceptance**:

- Cache en `~/Library/Caches/srt2web/` en Mac
- Config en `~/.config/srt2web/` en Mac (XDG compatible)
- Logs en `~/Library/Logs/srt2web/` en Mac
- Windows sigue igual (no regresión)

### F64 — TUI en terminales macOS (Media prioridad)

**Qué**: Verificar TUI (Textual) en Terminal.app, iTerm2, Warp. Ajustar bindings, rendering, sparklines.

**Problema**: TUI desarrollada y testeada solo en Windows. Terminal.app tiene soporte limitado de true color.
Keyboard bindings (cmd vs ctrl) pueden diferir. `stop_Mac.sh` no mata procesos TUI.

**Archivos**: `cli/tui/app.py`, `stop_Mac.sh`, `cli/main.py`, `docs/compatibility.md`

**Riesgo**: Bajo. Textual es cross-platform.

**Acceptance**:

- TUI funciona en Terminal.app, iTerm2, Warp
- Sparklines renderizan correctamente
- q, space, s, ? bindings funcionan
- `stop_Mac.sh` mata también procesos `srt2web-tui`

### F65 — Documentación y CI/CD macOS (Media prioridad)

**Qué**: Actualizar docs y agregar GitHub Actions workflow para macOS.

**Problema**: README.md no cubre Mac. No hay CI en macOS. No hay troubleshooting guide.

**Archivos**: `README.md`, `docs/compatibility.md`, `docs/deployment.md`,
`docs/troubleshooting-mac.md` (NUEVO), `.github/workflows/ci-mac.yml` (NUEVO)

**Riesgo**: Bajo. Solo documentación y CI.

**Acceptance**:

- README.md con sección Mac install
- GitHub Actions corre pytest en macOS (sin slow tests)
- Troubleshooting guide para Mac

---

## 10. Plan de mejora CLI/TUI (F55–F58)

Basado en auditoría de código del 14/05/2026. ~1,012 líneas de CLI/TUI, ~13% cobertura de tests, múltiples bugs y gaps de funcionalidad.

### F55 — TUI/CLI Bug Fixes & Code Quality (Alta prioridad)

**Qué**: Corrección de bugs funcionales, eliminación de dead code, mejora de manejo de errores.

**Bugs identificados**:

| #   | Gravedad   | Archivo                                      | Descripción                                                                                                                                                                                                                             |
| --- | ---------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **HIGH**   | `cli/tui/screens/module_detail.py:166-174`   | `_get_nested()` parte las keys por `_` y recorre el dict como path anidado. Keys multi-word como `chunk_duration_sec`, `encoder_mode`, `source_lang` → nunca encuentran su valor. Todos los campos multi-word del form aparecen vacíos. |
| 2   | **HIGH**   | `cli/tui/widgets/module_card.py` (74 líneas) | `TUIModuleCard` duplicado — nunca importado por ningún archivo. La versión en `module_grid.py` es la real. `module_card.py` es dead code.                                                                                               |
| 3   | **MEDIUM** | `cli/tui/app.py`                             | 20+ bloques `except Exception: pass` silenciosos. Errores de polling, toggle, save, refresh se tragan sin feedback al usuario.                                                                                                          |
| 4   | **MEDIUM** | `cli/tui/app.py`                             | Tareas fire-and-forget en `action_toggle_pipeline`, `action_save_config`, `on_unmount` → excepciones no manejadas se pierden.                                                                                                           |
| 5   | **MEDIUM** | `cli/tui/app.py:137-138`                     | `_on_ws_status()` es un no-op. Los eventos de estado vía WS se ignoran completamente, solo se usa HTTP polling.                                                                                                                         |
| 6   | **MEDIUM** | `cli/tui/widgets/log_panel.py:36-38`         | `set_filter()` definido pero jamás llamado. No hay dropdown de filtro de logs en la UI.                                                                                                                                                 |
| 7   | **LOW**    | `cli/commands/status.py:29-31`               | `_state_dot()` definida pero nunca usada.                                                                                                                                                                                               |
| 8   | **LOW**    | `cli/tui/app.py:108`                         | `_module_info_map` inicializado pero nunca usado (módulos se leen de `status.modules`).                                                                                                                                                 |
| 9   | **LOW**    | `cli/tui/widgets/module_grid.py:142-152`     | `_move_selection()` y `focus_card()` definidos pero jamás llamados. Sin navegación por teclado.                                                                                                                                         |
| 10  | **LOW**    | `cli/commands/config.py:86-99`               | `run_config_set` usa patrón read-modify-write → riesgo de race condition si config cambia entre `get_config()` y `update_config()`.                                                                                                     |
| 11  | **LOW**    | `cli/tui/screens/dashboard.py`               | `_dict_to_yaml()` no escapa strings con caracteres especiales, puede producir YAML inválido.                                                                                                                                            |

**Archivos**: `cli/tui/screens/module_detail.py`, `cli/tui/widgets/module_card.py` (eliminar), `cli/tui/app.py`, `cli/tui/widgets/log_panel.py`, `cli/widgets/module_grid.py`, `cli/commands/status.py`, `cli/commands/config.py`

**Riesgo**: Medio. Los bugs funcionales (1) afectan directamente UX del TUI.

### F56 — CLI One-Shot Commands Expansion (Media prioridad)

**Qué**: Agregar comandos faltantes para cubrir toda la API del servidor.

**Comandos a agregar**:

| Comando                                                 | Endpoint API                      | Descripción                        |
| ------------------------------------------------------- | --------------------------------- | ---------------------------------- |
| `srt2web-tui module list`                               | `GET /api/modules`                | Lista todos los módulos con estado |
| `srt2web-tui module toggle <name> [--enable/--disable]` | `PUT /api/modules/{name}/toggle`  | Activa/desactiva módulo            |
| `srt2web-tui module debug <name>`                       | `GET /api/modules/{name}/debug`   | Estado raw del módulo              |
| `srt2web-tui output list`                               | `GET /api/outputs`                | Lista outputs activos              |
| `srt2web-tui output add <type> [--name] [--config]`     | `POST /api/outputs`               | Agrega output                      |
| `srt2web-tui output remove <name>`                      | `DELETE /api/outputs/{name}`      | Elimina output                     |
| `srt2web-tui output toggle <name>`                      | `POST /api/outputs/{name}/toggle` | Activa/desactiva output            |
| `srt2web-tui preset list`                               | `GET /api/presets`                | Lista presets                      |
| `srt2web-tui preset save <name>`                        | `POST /api/presets`               | Guarda preset                      |
| `srt2web-tui preset apply <name>`                       | `POST /api/presets/{name}/apply`  | Aplica preset                      |
| `srt2web-tui preset delete <name>`                      | `DELETE /api/presets/{name}`      | Elimina preset                     |
| `srt2web-tui recording list`                            | `GET /api/recordings`             | Lista grabaciones                  |
| `srt2web-tui recording delete <name>`                   | `DELETE /api/recordings/{name}`   | Elimina grabación                  |
| `srt2web-tui input info`                                | `GET /api/input-info`             | Info de input actual               |
| `srt2web-tui input play/pause/seek`                     | `POST /api/input/control/*`       | Control de reproducción            |
| `srt2web-tui network info`                              | `GET /api/network/info`           | Info de red                        |

**SDK gaps a cubrir**:

- `APIClient.update_output(name, config?, enabled?)` → `PUT /api/outputs/{name}` (endpoint existe, método falta)
- `APIClient.download_recording(name)` → `GET /api/recordings/{name}/download`

**Archivos**: `cli/client/http_client.py`, `cli/commands/` (nuevos archivos o extensión), `cli/main.py`

**Riesgo**: Bajo. Comandos nuevos que siguen patrones existentes, sin cambios en infraestructura.

### F57 — TUI Feature Completeness (Media prioridad)

**Qué**: Cerrar gaps funcionales entre el dashboard web y el TUI.

**Paneles/screens faltantes**:

| Funcionalidad                   | Estado web                    | TUI actual                                   | Acción                                  |
| ------------------------------- | ----------------------------- | -------------------------------------------- | --------------------------------------- |
| Presets management              | ✅ Panel PresetsPanel         | ❌ No existe                                 | Agregar pantalla de presets             |
| Recordings management           | ✅ RecordingManagerCard       | ❌ No existe                                 | Agregar pantalla de grabaciones         |
| Input control (play/pause/seek) | ✅ En StatusCard (file mode)  | ❌ No existe                                 | Agregar pantalla de control de input    |
| Log level filter                | ✅ En LogPanel (dropdown)     | ❌ `set_filter()` definido pero no conectado | Conectar dropdown a `set_filter()`      |
| Module detail auto-refresh      | ✅ N/A (no hay detail screen) | ❌ Datos estáticos al abrir                  | Agregar polling/WS push a module detail |
| GPU metrics display             | ✅ GPU badge en process cards | ❌ No se muestran en grid                    | Agregar info de GPU a las cards         |
| Keyboard navigation grid        | ✅ N/A (web)                  | ❌ Arrow keys no funcionan                   | Conectar `_move_selection()` a bindings |
| Output list keyboard nav        | ✅ N/A (web)                  | ❌ Sin navegación                            | Agregar focus/keyboard a outputs        |

**Archivos**: `cli/tui/app.py`, `cli/tui/screens/` (nuevos screens), `cli/tui/widgets/`, `cli/tui/screens/help.py`

**Riesgo**: Medio. Nuevas pantallas siguen patrones existentes (module_detail.py como referencia).

### F58 — CLI/TUI Test Coverage (Alta prioridad)

**Qué**: Elevar cobertura de tests de ~13% a >70% en cli/.

**Objetivos por módulo**:

| Módulo                                  | Cobertura actual | Objetivo | Tests a agregar                                                                  |
| --------------------------------------- | :--------------: | :------: | -------------------------------------------------------------------------------- |
| `cli/client/ws_client.py`               |        0%        |   85%    | Mock WS server, test connect/reconnect/backoff/message routing/ping              |
| `cli/client/http_client.py` (APIClient) |       ~10%       |   75%    | Test cada método HTTP con `respx` mock. Test auth, errores, timeouts             |
| `cli/commands/start.py, stop.py`        |        0%        |   90%    | Test start/stop con mock. Test JSON output, errores                              |
| `cli/commands/logs.py`                  |        0%        |   80%    | Mock WSClient, test follow/non-follow/level filter/Ctrl+C                        |
| `cli/commands/status.py`                |       ~8%        |   80%    | Test JSON output, table rendering, error paths                                   |
| `cli/commands/config.py`                |       ~42%       |   85%    | Test `_build_tree`, `_format_value`, `run_config_show`, value parsing edge cases |
| `cli/main.py`                           |        0%        |   70%    | Click CliRunner tests para todos los comandos                                    |
| `cli/tui/` (total)                      |        0%        |   50%    | Smoke tests con pytest-textual, test de screens individuales                     |

**Infraestructura de test a agregar**:

- `tests/cli/conftest.py` con fixtures de mock API/WS
- `tests/cli/test_ws_client.py` (nuevo)
- `tests/cli/test_cli_commands_full.py` (nuevo, expande test_cli_commands.py)
- `tests/cli/test_cli_entry.py` (nuevo, CliRunner)
- `tests/cli/test_tui_screens.py` (nuevo, opcional, pytest-textual)

**Archivos**: Múltiples en `tests/`

**Riesgo**: Bajo. Tests nuevos no modifican código de producción.

**Dependencia**: Idealmente después de F55 (bugs corregidos) para no testear bugs conocidos.

### Orden de implementación sugerido (TUI)

```
F55 (bugs + code quality) → F58 (tests) → F56 (commands) → F57 (TUI features)
```

- **F55 primero**: Corrige bugs existentes antes de agregar funcionalidad nueva
- **F58 segundo**: Tests dan seguridad para cambios posteriores
- **F56 tercero**: Comandos nuevos son seguros con tests en su lugar
- **F57 último**: Feature compleja que puede depender de F55 y F56

## 11. Plan de compatibilidad macOS (F59–F65)

### Resumen del plan

| ID  | Área  | Nombre corto                                   | Prioridad | Estado  | Dependencias |
| --- | ----- | ---------------------------------------------- | --------- | ------- | ------------ |
| F59 | macOS | Script init_Mac.sh de verificación del harness | Alta      | pending | —            |
| F60 | macOS | Hardening cross-platform de subprocess         | Alta      | pending | F59          |
| F61 | macOS | Aceleración GPU Apple Silicon (MPS/CoreML/VT)  | Alta      | pending | F62          |
| F62 | macOS | Flujo de dependencias para Mac                 | Media     | pending | F59          |
| F63 | macOS | Estandarización de paths cross-platform        | Media     | pending | F62          |
| F64 | macOS | Verificación TUI en terminales macOS           | Media     | pending | F59, F55     |
| F65 | macOS | Documentación y CI/CD para macOS               | Media     | pending | F59-F64      |

### Orden de implementación sugerido

```
F59 ──→ F60 ──→ F62 ──→ F63 ──→ F61 ──→ F64 ──→ F65
                ↓
         F55-F58 (independiente, paralelo)
```

### Dependencia con TUI

- **F55** (bugs TUI) debe completarse **antes** de **F64** (TUI en Mac) porque los bugs existentes afectarían la experiencia en Mac de igual forma
- **F58** (tests) debe completarse **antes** de **F56** y **F57** (seguridad para cambios)
- Las features macOS (F59-F65) y TUI (F55-F58) comparten solo la dependencia F55→F64

### Métricas de éxito

- `./init_Mac.sh` pasa verde en Mac M1/M2/M3 con macOS 14+
- `srt2web-tui tui` se lanza sin errores en Terminal.app, iTerm2, Warp
- Pipeline corre end-to-end en Mac con aceleración MPS/CoreML/VideoToolbox
- Cero `AttributeError` por `CREATE_NO_WINDOW` o `pynvml` en Mac
- Cobertura de tests >70% en cli/ (F58)
- GitHub Actions corre tests en macOS en cada PR

---

## 12. Plan de acción: correcciones post-análisis de logs (F181–F182)

Basado en análisis de `server_test_err.log` del 11/07/2026. Dos problemas críticos identificados durante la ejecución del pipeline en modo SRT.

### Resumen del plan

| ID   | Área     | Nombre corto                                      | Prioridad | Estado  | Dependencias |
| ---- | -------- | ------------------------------------------------- | --------- | ------- | ------------ |
| F181 | pipeline | Manejo graceful de SRT input sin fuente de video  | Alta      | pending | —            |
| F182 | modules  | Instalar dependencias faltantes (whisper + argos) | Alta      | pending | —            |

```
F182 (deps) → F181 (SRT hang) — F182 es prerequisito lógico para probar F181 con pipeline completo
```

### Orden de implementación sugerido

```
F182 → F181
```

**F182 primero**: Las dependencias de transcripción/traducción deben estar instaladas para que al probar F181 el pipeline funcione end-to-end y se pueda verificar que la corrección no rompe el flujo normal.

---

### F182 — Instalar dependencias faltantes: faster-whisper y argostranslate (Alta prioridad)

**Qué**: Activar/instalar `faster-whisper` y `argostranslate`, actualmente comentados en `config/requirements.txt` como "Phase 2 - Processing (uncomment when needed)".

**Problema**: Los módulos `transcriber` y `translator` no cargan porque sus dependencias no están instaladas. El pipeline funciona pero esas funciones esenciales están caídas, forzando el uso de DMR translator (AI local) como única alternativa.

**Archivos**: `config/requirements.txt`, `pyproject.toml`

**Riesgo**: Bajo. Dependencias ya especificadas, solo activar y verificar compatibilidad.

**Acceptance**:

- `pip install -e .[processing]` o equivalent instala faster-whisper y argostranslate sin errores
- `pip install -r config/requirements.txt` incluye ambas (directamente)
- Al reiniciar servidor, los módulos `transcriber` y `translator` cargan correctamente (no más "package not installed")
- `tests/unit/test_transcriber.py` y `tests/unit/test_translator.py` pasan

---

### F181 — Manejo graceful de SRT input sin fuente de video (Alta prioridad)

**Qué**: Detectar cuando el input SRT está activo pero no recibe datos de ningún emisor (OBS/encoder desconectado), detener el reinicio en bucle del watchdog y notificar al usuario.

**Problema**: Cuando no hay fuente enviando video al puerto SRT 9000:

1. FFmpeg se ejecuta pero no produce chunks ni stderr
2. `_monitor_ffmpeg()` se bloquea en `readline()` (sin datos) → no llama a `notify_activity()`
3. Watchdog detecta "hang" tras 60s sin actividad → mata FFmpeg y lo reinicia
4. Ciclo infinito de reinicio (hasta 10 intentos, ~10-12 minutos)
5. El usuario no recibe feedback de que no hay señal entrante

**Causa raíz**: El watchdog solo monitorea actividad de stderr y existencia del proceso. No tiene concepto de "input source sin datos". El reinicio es un side-effect accidental, no un comportamiento diseñado.

**Arquitectura**:

```
OBS/Encoder ──SRT──→ FFmpeg (listener) ──chunks──→ get_next_chunk() ──→ Pipeline
                          │
                          └── stderr ──→ _monitor_ffmpeg() ──→ watchdog.notify_activity()
                                                                    │
                                                                    └── _last_output_time reset
```

Cuando no hay OBS: FFmpeg no escribe chunks, stderr no produce líneas → `_last_output_time` nunca se actualiza → watchdog detecta hang → restart loop.

**Archivos a modificar**:

| Archivo                       | Cambio                                                                    |
| ----------------------------- | ------------------------------------------------------------------------- |
| `core/input/srt_input.py`     | Añadir timeout en `get_next_chunk()` que detecte "sin datos nunca"        |
| `core/watchdog.py`            | Añadir `first_data_time` + `_has_ever_received_data` flag                 |
| `core/watchdog.py`            | Si `_has_ever_received_data == False`: no reiniciar, solo log y notificar |
| `core/pipeline/strategies.py` | Añadir timeout de "no chunks recibidos en N segundos"                     |
| `core/unified_pipeline.py`    | Nuevo estado o flag `waiting_for_source`                                  |
| `modules/inputs/srt_input.py` | `notify_activity()` con flag de datos recibidos                           |

**Cambios específicos**:

1. **En `core/watchdog.py`**:

   - Añadir `_has_ever_received_data = False` en `__init__`
   - Añadir `first_data_time = None` para tracking opcional
   - En `notify_activity()`, si es primera vez, setear `_has_ever_received_data = True`
   - En `_check_health()`, si el proceso no ha muerto y `not _has_ever_received_data`: loguear `WARNING "SRT input active but no data received yet (expected: OBS/encoder connected to port 9000)"` y **NO reiniciar** (solo log cada 30s)
   - Si `_has_ever_received_data == True` y luego hay hang: comportamiento actual (restart, porque hubo datos antes)

2. **En `modules/inputs/srt_input.py`**:

   - `_monitor_ffmpeg()`: después de cada `readline()` que devuelva datos llamar `watchdog.notify_activity(data_received=True)`
   - `_start_ffmpeg_process()`: al arrancar, llamar `watchdog.notify_activity()` para reset inicial
   - Añadir `_idle_timeout = 30` segundos: si `get_next_chunk()` devuelve `None` consistentemente y `not _has_ever_received_data`, loguear estado "waiting_for_source" en `get_status()`
   - `get_status()`: añadir campo `waiting_for_source: bool`

3. **En `core/pipeline/strategies.py`**:

   - `_input_thread_loop`: si `get_next_chunk()` devuelve `None` por más de `max_idle_seconds` (default 120s configurable), loguear advertencia y notificar cambio de estado via `ctx.on_state_change`

4. **En `core/unified_pipeline.py`**:
   - `get_status()`: incluir `waiting_for_source` del input source
   - No cambiar la máquina de estados principal, solo exponer el flag

**Riesgo**: Medio

- **Mitigación 1**: No cambiar comportamiento para casos donde SRT funciona correctamente (solo afecta cuando `_has_ever_received_data == False` y hay hang)
- **Mitigación 2**: Tests unitarios para watchdog que verifiquen comportamiento distinto con/s sin datos previos
- **Mitigación 3**: Los cambios en watchdog no afectan otras fuentes de input (file, rtmp) porque solo se activa para SRT

**Acceptance**:

- Cuando no hay fuente SRT, el watchdog **NO reinicia** FFmpeg en bucle
- Aparece log `WARNING` claro: "SRT input active but no data received yet — waiting for source on port 9000"
- `GET /api/status` muestra `waiting_for_source: true` en el status del input
- Cuando OBS se conecta y empieza a enviar, `_has_ever_received_data` se setea y el watchdog vuelve al comportamiento normal
- Tests que verifiquen:
  - Watchdog sin datos previos: no restart, solo warning
  - Watchdog con datos previos + hang posterior: restart (comportamiento actual)
  - `_has_ever_received_data` se setea correctamente al recibir primer chunk/stderr

### 11/08 — Auditoría + mejoras de calidad (F188–F192)

Auditoría técnica del repo completa (tests/unit 1599P+40F, tests/cli 78P+25F, ruff 128 errores en tests+harness, mypy --strict limpio, frontend tsc+vitest 248 limpio). 5 features implementadas una a una:

- **F188** ✅ Fix `init.ps1`: em-dash `—` (UTF-8 sin BOM) en la línea 30 rompía el parseo en PowerShell 5.1 (byte 0x94 → `”` → cascada de errores). Verificado con `Parser::ParseFile` → PARSE-OK.
- **F189** ✅ Fix 40 tests auth: `tests/conftest.py` activaba `SRT2WEB_TESTING` sin setear `SRT2WEB_JWT_SECRET` → "HMAC key must not be empty" en todo el clúster F121/F122/F123. Una línea `os.environ.setdefault` → suite unit **1639 passed, 0 failed**.
- **F190** ✅ 25 tests CLI obsoletos → API real: `ConfigData` (no dicts), `PipelineStatus`, URL con `/ws/logs`, `json()` síncrono de httpx, firmas reales de screens TUI. Suite CLI **110 passed**.
- **F191** ✅ f108 flaky aislado: el patch `modules.outputs.hls_output.subprocess.run` es global → `find_ffprobe()` → `platform.system()` → `_syscmd_ver()` → `check_output()` → `run()` → MagicMock. Fix: parchear `core.ffmpeg_utils.find_ffprobe` con `return_value=""` + test `test_warm_up_auto_detects_cuda` robusto aislado (stub propio de `sys.modules["torch"]`).
- **F192** ✅ Ruff cleanup: **128 → 0 errores** en `tests/` + `harness/` (auto-fix + RUF059/E402 noqa deliberados + SIM105/117/115 + B017 tipadas: ValueError/ValidationError/TimeoutError + RUF012 ClassVar). `ruff check tests/ harness/ core/ modules/ server/ cli/` → todo verde.

**Verificación final**: unit 1639 + cli 110 passed, mypy --strict 100 archivos sin errores, ruff global 0 errores, frontend tsc+vitest 248 pass. Detalles en `harness.db` (sesión #34).

### 11/08 — Fix venv pre-commit (mypy hook roto)

- **Síntoma**: `git commit` falla con `ModuleNotFoundError: No module named 'librt.internal'` en el hook mypy.
- **Causa raíz (investigada a fondo)**: el venv de Hermes está SANO (`import mypy`, `import librt.internal` OK bajo su Python 3.11). El problema es el `PYTHONPATH` global que el runtime de codex/hermes inyecta en los procesos hijo (`...\hermes-agent;...\hermes-agent\venv\Lib\site-packages`). pre-commit crea sus py_env con Python 3.12 y su propio mypy 1.15 cp312, pero al heredar ese PYTHONPATH, `import mypy` resuelve al 2.1.0 cp311 del venv de Hermes → el `.pyd` de `librt` no carga bajo cp312 → falso "No module named".
- **Fix**: `unset PYTHONPATH` en `.git/hooks/pre-commit` (solo para procesos del hook; no toca el entorno). Verificado: `env -u PYTHONPATH pre_commit run mypy` → **Passed** en core/ server/ modules/ cli/.
- **Bonus**: el mismo PYTHONPATH global es el que rompía los workers xdist de pytest (`pydantic_core` ausente) — `env -u PYTHONPATH pytest ...` es el workaround si reaparece.

### 12/08 — Subtítulos estables: ventana subs alineada al video (F193)

- **Síntoma reportado**: "los subtítulos a veces no salen, salen un poco y desaparecen".
- **Diagnóstico en pipeline vivo** (evidencia filesystem en `output/hls/` + `output/subtitles/`): 4 causas raíz:
  - **Subs 1 fragmento por delante del video**: la ventana de `subs.m3u8` exponía `subs_seg_000060.vtt` cuando el video solo había publicado `seg_000059.ts` → el player descartaba las cues del fragmento punta.
  - **`#EXT-X-PLAYLIST-TYPE:EVENT` en `subs.m3u8`** (escrito por `_fragment_writer.py`) con `MEDIA-SEQUENCE` avanzando y rolling window de 10: contradicción de spec (RFC 8216: EVENT nunca recorta ni avanza seq) → HLS.js podía descartar/resetear el track → "salen un poco y desaparecen".
  - **EXTINF dispares**: `subs.m3u8` con duraciones calculadas del chunk vs `stream.m3u8` con las reales (11.4 vs 12.043) → desfase temporal progresivo de las cues.
  - **Bug de índice con chunk silencioso** (`__init__.py` ~204): `if not text: return data` no avanzaba `_last_chunk_index`; todos los chunks con texto siguientes quedaban atrapados en `_pending` como out-of-order → subtítulos congelados hasta superar `MAX_PENDING` (~128 chunks, ~10 min). Causa del "a veces no salen".
- **Fix** (4 archivos):
  - `_fragment_writer.py`: eliminado `#EXT-X-PLAYLIST-TYPE:EVENT`; nueva `set_video_playlist_path()` — `rewrite_playlist()` alinea la ventana de subs con el video por **intersección completa** `[min_video_idx, max_video_idx]` (`stream.m3u8` como fuente de verdad compartida) y reutiliza sus EXTINF reales (`_read_video_durations`). El recorte del techo (v1 del fix) dejaba la base desalineada (subs seq 11 vs video seq 15 en vivo → HLS.js descartaba cues); la intersección recorta también fragmentos stale de la base y sirve un playlist vacío anclado a la seq del video cuando no hay solapamiento (restart/renumeración). Fallback intacto si no hay `stream.m3u8`.
  - `subtitle_generator_pkg/__init__.py`: `start()` conecta el video playlist al writer; chunk sin texto ya no rompe la secuencia — se escribe un fragmento VTT vacío y avanza el índice (correspondencia 1:1 con el video), salvo pause loop (`is_loop`) que se chequea antes.
  - `hls_output.py`: comentario obsoleto 531-532 actualizado ("media_seq=0" ya no aplica).
  - `tests/unit/test_f108_subtitle_hls_sync.py`: +11 tests de regresión (ventana recortada al video, EXTINF del video, sin tag EVENT, chunk silencioso avanza el índice / escribe vacío / no congela el siguiente, loop skip).
- **Verificación**: `test_f108_subtitle_hls_sync` + `test_subtitle_generator` **46/46** (+3: base alineada, playlist vacío sin solapamiento, EXTINF tras recorte de base); `test_f183_f187_startup_races` **17/17**; fallos de `test_hls_output`/`test_hls_remux` confirmados **pre-existentes** (git stash, patrones F191/mock); ruff 0 errores; mypy 0 errores en los 3 módulos. Detalles en `harness.db` (sesión #35, F193 done).

### 12/08 — Subs siguen saltando trozos: re-sync del playlist tras publicar segmento (F193 2ª ronda)

- **Síntoma**: tras el fix de intersección de ventanas y reinicio, "el audio traducido va perfecto pero los subtítulos se saltan muchos trozos".
- **Diagnóstico en vivo** (mtimes de `subs.m3u8` vs `stream.m3u8`): el generador de subs escribe `subs.m3u8` ~1s **ANTES** de que `HLSOutput` publique el segmento de video del mismo índice (va antes en el pipeline: audio→…→subtitle_generator→tts→mixer→HLSOutput). `rewrite_playlist()` recorta entonces a `max_video_idx = N-1` y la ventana de subs queda congelada 1 fragmento por detrás cuando el video avanza (evidencia: video `MEDIA-SEQUENCE:64` con seg 64–69 vs subs `63` con frag 63–68). Dos playlists con `MEDIA-SEQUENCE` distintas → HLS.js correlaciona mal y descarta/mezcla cues → "saltos". Los VTT en disco estaban llenos de cues (el texto llega bien); el problema era la **entrega del playlist**, no la generación.
- **Fix (3 archivos + tests)**:
  - `modules/outputs/hls_output.py`: `set_subtitle_resync_callback()` + invocación al final de `_update_manifest()` (se llama en los 3 paths de `write()`) — tras publicar cada segmento, dispara el re-write del playlist de subs LEYENDO el `stream.m3u8` ya actualizado.
  - `modules/subtitle_generator_pkg/__init__.py`: método público `sync_playlist()` bajo `self._lock` → `_fragment_writer.rewrite_playlist()`.
  - `core/app_context.py`: wiring tras `_register_modules` — `pipeline.get_module("subtitle_generator")` + `composite_sink.get_output_names()`/`get_output_by_name()` registran el callback en cada output que lo soporte (duck-typing con `getattr`).
- **Verificación**: 69/69 (test_f108 +test_subtitle_generator 52 = 46 + 4 re-sync + 2 callback HLSOutput; test_f183_f187 17 intacto); smoke test de `create_app_context` en vivo: "WIRING OK wired callback on web_1"; mypy 0 errores; ruff 0 errores.

---
