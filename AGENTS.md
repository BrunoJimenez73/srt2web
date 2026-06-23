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
- **No toques `PARA BORRAR/`** — carpeta candidata a limpieza, ver F29.
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

Ver `feature_list.json` para lista completa y estados. Total actual: 126 features.

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

**Siguiente pendiente**: F123 — session security (JWT expiry, refresh tokens, token blacklist).

## 8. Historial compacto (post-Abril 2026)

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
