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
| `tests/`              | 590 tests (pytest + vitest)                             | Para verificar         |
| `config.yaml`         | Configuración runtime del pipeline                      | Para entender defaults |

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

## 4. Comandos útiles

```bash
# Verificar entorno
.\init.ps1              # Completo
.\init.ps1 -Quick       # Solo checks obligatorios (salta frontend)

# Tests
python -m pytest tests/unit/ -v              # Unit tests
python -m pytest tests/unit/test_X.py -v     # Test específico
cd frontend && npm test                       # Frontend tests

# Frontend
cd frontend && npx tsc --noEmit              # TypeScript check
cd frontend && npm run build:local           # Build + copiar a server/static/

# Servidor
.\start.bat                                   # Iniciar servidor (minimizado)
```

## 5. Arquitectura rápida

```
SRT/RTMP → AudioExtractor → Transcriber (Whisper) → Translator (Argos)
                                                          ↓
HLS ← CompositeOutput ← AudioMixer ← TTS (Piper) ← SubtitleGenerator
```

**Pipeline** (`core/unified_pipeline.py`): 3 modos (sequential/thread_parallel/asyncio). Por defecto `thread_parallel` con 2 workers concurrentes.

**Módulos registrados** en `core/app_context.py`:

- `audio_extractor`, `transcriber`, `translator`, `subtitle_generator`, `tts_engine`, `audio_mixer`
- `video_muxer` NO está registrado como módulo del pipeline (es OutputSink, se reporta via `_get_output_module_status()`)

**I/O plugins** (auto-registro via `InputFactory`/`OutputFactory`):

- Inputs: SRT, RTMP, File
- Outputs: HLS, RTMP, SRT, File, Recording, WebRTC (composite delegado)

**Config**: Pydantic (`core/config_schema.py` → `SRT2WebConfig`). `ConfigManager` carga `config.yaml`, valida, permite get/set por dotted keys.

**Seguridad**: AuthMiddleware (token query param), RateLimiter, SecurityHeaders. WebSocket con autenticación propia.

## 6. Notas técnicas

### GPU / CUDA

- `setup_cuda_environment()` en `core/cuda_paths.py` configura PATH para DLLs CUDA
- ONNX Runtime GPU NO soporta cuDNN 9.x. Usar `device: auto` o `cpu` en config
- `HardwareMonitor` (nvidia-ml-py) reporta % uso y memoria GPU
- GPU badge en frontend: verde si módulo usa GPU + está running + processed_chunks > 0

### Piper TTS

- `modules/piper_loader.py` usa subprocess persistente (evita bloqueo event loop)
- Modelos en `models/piper/` (17 voces). Default: `en_US-ryan-low`
- Voces ES: Sharvard, Davefx (ES), Claude (MX), Daniela (AR)
- Timeout 90s para carga de modelo. `device: auto` → intenta CUDA, fallback CPU

### FFmpeg

- Pool de procesos en `core/ffmpeg_pool.py` (max 4, idle 30s)
- `FFmpegWatchdog` en `core/watchdog.py` detecta crashes/hangs
- Keyframe interval OBS mínimo ~10s → chunk duration mínima ~10s

### Frontend

- Astro + TypeScript strict + Tailwind CSS. Build: `npm run build:local` → copiar a `server/static/`
- WebSocket en `api.ts` con reconexión lineal. Auth token vía query param `?token=xxx`
- HLS player en `http://localhost:9999/player`
- `ProcessGrid` = 8 cards: Input, Whisper, Translate, TTS, Subtitle, AudioMixer, HLS, Output

### Testing

- `pytest` con `asyncio_mode = auto`. Fixtures function-scoped en `tests/conftest.py`
- Markers: `unit`, `integration`, `e2e`, `slow`, `security`, `gpu`, `cpu`
- Frontend: Vitest. 151 test blocks. `npm test` en `frontend/`

## 7. Features pendientes

Ver `feature_list.json` para lista completa. Actual: 8 features:

1. Arreglar gestión de dependencias
2. Corregir bugs críticos del pipeline
3. Arreglar Stop.bat y scripts
4. Agregar tests para módulos sin cobertura
5. Limpiar console.logs y race conditions frontend
6. Estandarizar manejo de errores API
7. Arreglar WebRTC y limpiar dead code
8. Arreglar CI y config inconsistencies

## 8. Historial compacto (post-Abril 2026)

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

### Commits recientes

```
d8888f4 perf: Replace FFmpeg atempo with Piper native length_scale
d154642 fix: Set HLS list_size to 2 (20s buffer)
0604cab perf: Replace FFmpeg with numpy for audio mixing (~100x faster)
1b2d72e fix: Re-add duration verification in audio_mixer for A/V sync
18f57a8 fix: Fix pipeline data flow and add logging persistence
89c9538 Fix GPU detection and pipeline processing issues
85f96d9 feat: Change default TTS voice to es_ES-sharvard-medium
99b9654 feat: Use nvidia-ml-py and add FFmpeg process pool
```
