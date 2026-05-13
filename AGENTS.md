# AGENTS.md — Mapa de navegación para srt2web

> Punto de entrada para cualquier agente que trabaje en este repo.
> Lee solo lo que necesites. Divulgación progresiva.

---

## 1. Mapa del repositorio

| Archivo / carpeta     | Qué contiene                                            | Cuándo leerlo          |
| --------------------- | ------------------------------------------------------- | ---------------------- |
| `feature_list.json`   | Features con status (pending/in_progress/done/blocked)  | Siempre, al empezar    |
| `progress/current.md` | Estado de la sesión activa                              | Siempre, al empezar    |
| `progress/history.md` | Bitácora append-only de sesiones                        | Si necesitas contexto  |
| `CHECKPOINTS.md`      | Criterios de "estado final correcto"                    | Antes de declarar done |
| `init.ps1`            | Script de verificación ejecutable                       | Al empezar y al cerrar |
| `core/`               | Pipeline, módulos base, config, factories               | Para implementar       |
| `modules/`            | Procesamiento (audio, TTS, transcripción) + I/O plugins | Para implementar       |
| `server/`             | FastAPI, WebSocket, seguridad                           | Para implementar       |
| `frontend/`           | Dashboard Astro + TypeScript + Tailwind                 | Para implementar       |
| `tests/`              | Tests pytest + vitest                                   | Para verificar         |
| `config.yaml`         | Configuración runtime del pipeline                      | Para entender defaults |
| `docs/`               | MkDocs, ADRs, guías de arquitectura                     | Para contexto técnico  |

## 2. Antes de empezar

1. Lee `feature_list.json` y elige una feature `pending`
2. Lee `progress/current.md` para saber dónde se quedó la sesión anterior
3. Ejecuta `.\init.ps1` — si falla, **para y resuelve** antes de tocar código
4. Cambia la feature a `in_progress` y anota el plan en `progress/current.md`

## 3. Reglas duras

- **Una feature a la vez.** No mezcles cambios de varias tareas.
- **init.ps1 verde para declarar done.** `pytest tests/unit/` pasa siempre.
- **Documenta mientras trabajas** en `progress/current.md`, no al final.
- **Deja el repo limpio:** sin prints, TODOs sin contexto, ni archivos temporales.
- **CHECKPOINTS.md completo** antes de cerrar sesión.
- Si te bloqueas, documenta en `progress/current.md` con estado `blocked` y para.
- **No toques `PARA BORRAR/`** — carpeta candidata a limpieza, ver F29.

## 4. Comandos útiles

```bash
# Verificar entorno
.\init.ps1              # Completo (incluye tests lentos + frontend + tsc)
.\init.ps1 -Quick       # Tests unitarios en paralelo, salta slow + frontend (~30s)

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

# Servidor
.\Start.bat                                   # Iniciar servidor (minimizado)
.\Stop.bat                                    # Parar solo procesos srt2web

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

### GPU / CUDA

- `setup_cuda_environment()` en `core/cuda_paths.py` configura PATH para DLLs CUDA
- ONNX Runtime GPU NO soporta cuDNN 9.x. Usar `device: auto` o `cpu` en config
- `HardwareMonitor` (nvidia-ml-py) reporta % uso y memoria GPU
- GPU badge en frontend: verde si módulo usa GPU + está running + processed_chunks > 0

### Piper TTS

- `modules/piper_loader.py` usa subprocess persistente (evita bloqueo event loop)
- Modelos en `models/piper/` (17 voces). Default: `es_ES-sharvard-medium`
- Voces ES: Sharvard, Davefx (ES), Claude (MX), Daniela (AR)
- Timeout 90s para carga de modelo. `device: auto` → intenta CUDA, fallback CPU
- **Heartbeat**: ver F17 — el subprocess necesita mecanismo de detección de bloqueo

### FFmpeg

- Pool de procesos en `core/ffmpeg_pool.py` (max 4, idle 30s)
- `FFmpegWatchdog` en `core/watchdog.py` detecta crashes/hangs
- Keyframe interval OBS mínimo ~10s → chunk duration mínima ~10s

### Frontend

- Astro + TypeScript strict + Tailwind CSS v4. Build: `npm run build:local` → copiar a `server/static/`
- WebSocket en `lib/store/signals.ts` + `lib/modules/pipeline-control.ts`
- Reconexión con **exponential backoff + jitter** (F15) — no lineal
- HLS player en `http://localhost:9999/player`
- `ProcessGrid` = 8 cards: Input, Whisper, Translate, TTS, Subtitle, AudioMixer, HLS, Output
- Tema único (dark) — soporte light/dark en F17
- Logs: panel virtual con export JSON/TXT en F16

### Testing

- `pytest` con `asyncio_mode = auto`. Fixtures function-scoped en `tests/conftest.py`
- Markers: `unit`, `integration`, `e2e`, `slow`, `security`, `gpu`, `cpu`
- Tests marcados `@pytest.mark.slow`: solo `test_whisper_integration.py` y `test_tts_integration.py` (cargan modelos reales, ~30s+). Se excluyen automáticamente con `.\init.ps1 -Quick` y con `-m "not slow"`
- Frontend: Vitest. `npm test` en `frontend/`. Cobertura: `npm run test:coverage`
- Objetivo cobertura frontend: 80%+ (ver F25)

### Convenciones de código nuevo

- Python: type hints completos en funciones públicas, `typing.Protocol` para interfaces
- TypeScript: sin `any`, preferir `unknown` + type guard
- CSS: usar variables CSS del tema (`--bg-card`, `--text-prime`, etc.), no colores hardcoded
- No `console.log` en producción — usar el logger configurable del módulo

## 7. Estado de features

Ver `feature_list.json` para lista completa y estados.

**Features 1–14**: todas DONE (ciclo Abril–Mayo 2026).

**Features 15–30**: completadas en sesiones Mayo 2026.

**Features 31–33**: plan de optimizaciones de latencia — pendientes.

### Resumen del plan de mejoras (F15–F33)

| ID  | Área               | Nombre corto                            | Prioridad | Estado      |
| --- | ------------------ | --------------------------------------- | --------- | ----------- |
| F15 | Rendimiento        | WS resilience & adaptive polling        | Alta      | ✅ done     |
| F16 | UX / Rendimiento   | LogPanel virtual scroll & export        | Alta      | ✅ done     |
| F17 | Estabilidad        | Piper heartbeat & graceful degrade      | Alta      | ✅ done     |
| F18 | UX / Visualización | Metrics sparklines & latency meter      | Media     | ✅ done     |
| F19 | UX                 | Pipeline presets / profiles             | Media     | ✅ done     |
| F20 | Estabilidad        | Output health monitoring                | Alta      | ✅ done     |
| F21 | Arquitectura       | Config push via WebSocket               | Media     | ✅ done     |
| F22 | Mantenibilidad     | Cleanup dead code final                 | Media     | ✅ done     |
| F23 | Arquitectura       | API versioning & Pydantic responses     | Media     | ✅ done     |
| F24 | Mantenibilidad     | mypy strict mode core/ + server/        | Alta      | ✅ done     |
| F25 | Testing            | Frontend coverage 80%+                  | Media     | ✅ done     |
| F26 | UX / Diseño        | Mobile-responsive layout                | Baja      | ✅ done     |
| F27 | UX / Visualización | Dependencias del pipeline (diagrama)    | Baja      | ✅ done     |
| F28 | DevOps             | Docker optimization & health checks     | Media     | ✅ done     |
| F29 | Mantenibilidad     | Repo hygiene (PARA BORRAR, stale files) | Alta      | ✅ done     |
| F30 | Rendimiento        | Subtitle sync & performance             | Alta      | ✅ done     |
| F31 | Rendimiento        | HLS passthrough mode                    | Alta      | ✅ done     |
| F32 | Rendimiento        | Audio extraction multi-thread           | Media     | ✅ done     |
| F33 | Rendimiento        | Pipeline parallelism optimization       | Media     | ✅ done     |

**Orden sugerido de implementación (latencia)**: F31 → F32 → F33

## 8. Historial compacto (post-Abril 2026)

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

## 9. Plan de optimización de latencia (F31–F33)

Basado en análisis de logs del 13/05. Latencia total actual ~20-24s extremo a extremo.

| Paso | Feature | Cambio | Ahorro estimado |
|------|---------|--------|----------------|
| 1 | F31 | HLS passthrough (encoder_mode: passthrough) | ~1650ms (49%) |
| 2 | F32 | Eliminar -threads 1 en audio_extractor | ~200-400ms (9%) |
| 3 | F33 | Revisar paralelismo real del pipeline | ~300ms (8%) |

**Latencia estimada post-optimización**: de ~3.5s de procesamiento a ~1.7s → E2E ~10-12s.

### F31 — HLS passthrough mode (Alta prioridad)

**Qué**: Cambiar `encoder_mode: auto` → `encoder_mode: passthrough` en config.yaml. FFmpeg usará `-c:v copy -c:a copy` sin re-codificar.

**Archivos**: `config.yaml`, `modules/outputs/hls_output.py` (verificar).

**Riesgo**: Bajo. Ya implementado, solo no activado. Revertible.

### F32 — Audio extraction multi-thread (Media prioridad)

**Qué**: Eliminar `-threads 1` de `audio_extractor.py` para que FFmpeg auto-detecte núcleos.

**Archivos**: `modules/audio_extractor.py`.

**Riesgo**: Bajo. FFmpeg maneja auto-threads correctamente.

### F33 — Pipeline parallelism (Media prioridad)

**Qué**: Investigar por qué `max_concurrent_chunks=4` no produce solapamiento real. Revisar colas y semáforos.

**Archivos**: `core/unified_pipeline.py`, `core/pipeline/strategies.py`.

**Riesgo**: Medio. Requiere entender el flujo de datos interno.

### Commits recientes relevantes

```
d8888f4 perf: Replace FFmpeg atempo with Piper native length_scale
d154642 fix: Set HLS list_size to 2 (20s buffer)
0604cab perf: Replace FFmpeg with numpy for audio mixing (~100x faster)
1b2d72e fix: Re-add duration verification in audio_mixer for A/V sync
18f57a8 fix: Fix pipeline data flow and add logging persistence
```
