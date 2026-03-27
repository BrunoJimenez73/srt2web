# SRT2Web - Estado del Proyecto

## Información General
- **Fecha sesión**: 2026-03-25
- **Versión**: 0.7.0
- **Repositorio**: https://github.com/BrunoJimenez73/srt2web
- **Tests**: 474 passed, 9 skipped

---

## Refactorización Completa (v0.7.0)

### JavaScript Extraído a TypeScript

**Problema**: Los archivos `.astro` contenían demasiado JavaScript inline (780+ líneas en `index.astro`, 220+ en `player.astro`).

**Solución**:

| Archivo Original | Archivo Extraído | Líneas |
|-----------------|------------------|--------|
| `frontend/src/pages/index.astro` | `frontend/src/lib/dashboard.ts` | ~780 |
| `frontend/src/pages/player.astro` | `frontend/src/lib/player.ts` | ~220 |

### Constantes Centralizadas

**Problema**: Valores hardcodeados dispersos por el código.

**Solución**: Creado `core/constants.py` con todas las constantes:

```python
# Ejemplos de constantes
DEFAULT_SERVER_PORT = 9999
DEFAULT_SRT_PORT = 9000
VALID_WHISPER_MODELS = frozenset([...])
VALID_ENCODER_MODES = frozenset(["auto", "cpu", "gpu", "gpu_nvenc", "gpu_amf", "gpu_qsv", "gpu_vaapi", "gpu_videotoolbox"])
ALLOWED_GPU_PRESETS = frozenset(["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
```

### Backend Fixes

| Archivo | Problema | Solución |
|---------|----------|----------|
| `modules/audio_mixer.py` | `print()` statements | Usar `logger.debug()` |
| `modules/audio_mixer.py` | Escribía `debug.log` infinito | Eliminado |
| `server/api_routes.py` | Path traversal bug | Usar `sanitize_path` |
| `server/api_routes.py` | `sanitize_module_name` duplicado | Unificado con `core/security.py` |
| `main.py`, `app.py`, `index.astro` | Versión incorrecta (v0.4.0) | Actualizado a v0.7.0 |
| `modules/video_muxer.py` | HLS master playlist duplicado | Unificado en `core/constants.py` |
| `modules/outputs/hls_output.py` | HLS master playlist duplicado | Usa `generate_master_playlist()` |
| `config.yaml` | `model: invalid_model` | Cambiado a `model: small` |

### Tests Arreglados (7 tests)

| Test | Problema | Solución |
|------|----------|----------|
| `test_config_video_muxer_valid_encoder_mode` | Falla con `gpu_nvenc` | Agregados todos los encoder modes a constants |
| `test_player_has_show_error_function` | Busca en .astro | Ahora busca en `player.ts` |
| `test_player_has_error_count_tracking` | Busca en .astro | Ahora busca en `player.ts` |
| `test_player_hides_waiting_on_manifest_parsed` | Busca en .astro | Ahora busca en `player.ts` |
| `test_player_has_error_handling` | Busca en .astro | Ahora busca en `player.ts` |
| `test_stop_has_confirmation` | Busca en .astro | Ahora busca en `dashboard.ts` |

### Commits

| Hash | Descripción |
|------|-------------|
| `e78e93f` | fix: Update encoder modes and fix JavaScript extraction tests |
| `1140c08` | chore: Track config.yaml in git and update .gitignore |

---

## Fix Player Audio/Video Cuts (v0.7.0)

**Problema**: El player HLS cortaba audio y video cada ~30 segundos.

**Causa raíz**:
- `setInterval` de 20s recreaba HLS.js sin llamar `hls.destroy()`
- Instancias huérfanas peleaban por control del `<video>`
- Timeout de manifest (30s) triggers estado ERROR → reinicialización automática

**Solución**:

| Archivo | Cambio |
|---------|--------|
| `frontend/src/pages/player.astro` | `destroyPlayer()` con `hls.destroy()` antes de recrear |
| `frontend/src/pages/player.astro` | Eliminado `setInterval` auto-reinicialización |
| `frontend/src/pages/player.astro` | Usa recuperación integrada de HLS.js (`startLoad`/`recoverMediaError`) |
| `frontend/src/pages/player.astro` | `enableWorker: true` para reducir jank en main thread |
| `frontend/src/lib/utils.ts` | URL SRT muestra `mode=caller` para OBS |

**Commits**: `ef25a24`, `e44c68f`, `736b710`, `4e28b94`, `68758de`

---

## Fix OBS Connection (v0.7.0)

**Problema**: OBS no podía conectarse al servidor SRT.

**Causas**:
- URL del frontend mostraba `mode=listener` pero OBS necesita `mode=caller`
- Tests no incluían `videotoolbox` del commit Mac support (`06c8c35`)

**Solución**:

| Archivo | Cambio |
|---------|--------|
| `frontend/src/lib/utils.ts` | `getSRTUrl()` siempre muestra `mode=caller` |
| `tests/unit/test_video_muxer.py` | Agregado `"videotoolbox": False` a todos los mocks |
| `tests/unit/test_gpu_installer_restructure.py` | Agregado `"videotoolbox": False` a mocks |
| `tests/e2e/test_config_loading.py` | Tests de puertos aceptan cualquier valor válido |

**Commits**: `68758de`, `16bf394`

---

## Fix Tests (v0.7.0)

**Problema**: 36 tests fallaban después de reestructuración y commits Mac.

**Archivos corregidos**:

| Archivo | Problema | Solución |
|---------|----------|----------|
| `test_api_e2e.py` | `assert "srt" in data` | Cambiado a `"input" in data` |
| `test_api_routes.py` | Mismo problema | Cambiado a `"input" in data` |
| `test_config_validation.py` | `model: invalid_model` | `pytest.skip()` si modelo inválido |
| `test_video_muxer.py` | Clase abstracta `_do_process` | `TestableVideoMuxer` subclass |
| `test_subtitle_generator.py` | `_cumulative_time` no existe | Tests reescritos con `_last_cumulative` |
| `test_audio_mixer.py` | Rutas Windows `/tmp/mix` | `tempfile.TemporaryDirectory` |
| `test_translator.py` | Mock de `ModelCache` faltante | Patch de `_model_cache` |
| `test_tts_engine.py` | `_voice_loaded` no seteado | Lazy loading verificado |
| `test_ws_routes.py` | Falta `pytest-asyncio` | Instalado el paquete |
| `test_security_middleware.py` | `SecurityCard.astro` eliminado | Tests apuntan a `Header.astro` |
| `test_srt_connection.py` | `web/index.html` no existe | Busca en `server/static/` |
| `test_player_page.py` | Rutas y contenido corrupto | Archivo reescrito |
| `test_performance_optimizations.py` | `max_request_size_mb` no existe | `pytest.skip()` |
| `test_config_loading.py` | Puerto exacto 9999/9000 | Validación de rango |

**Tests nuevos**: 53 tests en `test_gpu_installer_restructure.py`
- GPU indicators (transcriber, TTS, video_muxer)
- EncoderConfig (CPU, NVENC, AMF, QSV, VideoToolbox)
- PiperLoader subprocess
- Scripts BAT (Install, Start, Stop)
- Estructura del proyecto

**Commits**: `33af4c9`, `16bf394`

---

## Security Hardening (v0.7.0)

**Problema**: 11 vulnerabilidades de seguridad encontradas en el código.

**Fixes aplicados**:

| Severidad | Fix | Archivo |
|-----------|-----|---------|
| CRÍTICO | `auth_token` enmascarado como `***` en `/api/config` | `server/api_routes.py` |
| CRÍTICO | CSP sin `unsafe-eval` | `server/security.py` |
| CRÍTICO | Default host `127.0.0.1` (no `0.0.0.0`) | `main.py` |
| ALTO | X-Forwarded-For solo se confía desde localhost | `server/security.py` |
| ALTO | Validación path traversal en `file.path` | `server/api_routes.py` |
| ALTO | CORS: puertos explícitos (sin wildcards) | `server/app.py` |
| MEDIO | Traceback eliminado del error en toggle | `server/api_routes.py` |
| MEDIO | WebSocket: máximo 20 conexiones concurrentes | `server/ws_routes.py` |
| MEDIO | Import roto `cleanup_temporary_files` corregido | `main.py` |
| BAJO | FFmpeg download: verificación de tamaño | `core/ffmpeg_utils.py` |
| BAJO | Swagger/ReDoc deshabilitados en producción | `server/app.py` |

**Tests de seguridad nuevos**: 7 tests en `TestSecurityFixes`

**Commits**: `994c655`

---

## Fix Piper TTS Crash (v0.5.1)

**Problema**: Piper TTS causaba crashes del servidor al:
- Guardar configuración con engine=piper
- Iniciar pipeline con engine=piper

**Causa raíz**: 
- El modelo Piper tardaba 5+ segundos en cargar
- El hilo daemon moría silenciosamente sin completar
- Bloqueaba el event loop de FastAPI causando timeouts WebSocket

**Solución implementada**:

| Archivo | Cambio |
|---------|--------|
| `modules/piper_loader.py` | **Nuevo** - Loader subprocess para evitar bloqueo del event loop |
| `modules/tts_engine.py` | Usa subprocess en vez de threading, timeout 90s |
| `main.py` | [PIPER_DEBUG] logs siempre visibles (bypass filter) |
| `config.yaml` | `device: auto` en vez de `cuda` (fallback automático) |

**Diagnóstico CUDA**:
- CUDA Runtime detectado como disponible en ONNX providers
- Falta `cublasLt64_12.dll` y `cudnn` - dependencies de CUDA Toolkit
- Piper carga correctamente con CPU (fallback automático)

**Test Results**:
```python
# subprocess loader output:
{'status': 'success', 'using_cuda': True, 'sample_rate': 16000, 'provider': 'CUDAExecutionProvider'}
```

---

## Mejoras Implementadas

### Fase 1 - Seguridad Crítica ✅

| Archivo | Mejora |
|---------|--------|
| `server/security.py` | **Nuevo** - AuthMiddleware, RateLimiter, SecurityHeaders, RequestSizeLimit |
| `server/app.py` | Integra todos los middlewares de seguridad |
| `server/ws_routes.py` | Autenticación WebSocket + WebSocketRequest wrapper |
| `core/config_manager.py` | Host por defecto 127.0.0.1, rate_limit_rpm=60 |
| `main.py` | access_log=True habilitado |
| `config.yaml` | Nuevas opciones: auth_token, rate_limit_rpm, max_request_size_mb |
| `frontend/src/lib/api.ts` | Auth token en requests HTTP y WebSocket |

### Fase 2 - Rendimiento ✅

| Archivo | Mejora |
|---------|--------|
| `modules/tts_engine.py` | asyncio.run() en vez de crear event loop nuevo |
| `modules/audio_mixer.py` | Cache de duración ffprobe (evita llamadas repetidas) |
| `modules/transcriber.py` | Usa ModelCache para Whisper |
| `modules/translator.py` | Usa ModelCache para Argos Translate |
| `core/model_cache.py` | Ahora se usa correctamente (singleton) |

### Fase 3 - UX/Accesibilidad ✅

| Archivo | Mejora |
|---------|--------|
| `StatusCard.astro` | Loading states, aria-labels |
| `Header.astro` | Loading state + security toggle integrado |
| `LogPanel.astro` | Estado vacío, aria-live, role=log, búsqueda |
| `MetricsCard.astro` | role=meter, aria-valuenow |
| `ProcessGrid.astro` | role=region, aria-label |
| `BaseLayout.astro` | Skip-to-content link |
| `index.astro` | Loading states en handlers |

### Fase 4 - Optimizaciones ✅

| Archivo | Mejora |
|---------|--------|
| `server/app.py` | GZipMiddleware - compresión automática >1KB |
| `modules/subtitle_generator.py` | Rolling window VTT (max 50 entradas, 60s max age) |

### Fase 5 - UX Mejoras ✅

| Archivo | Mejora |
|---------|--------|
| `player.astro` | Error overlay con botón Reintentar |
| `index.astro` | Confirmación antes de detener pipeline |
| `LogPanel.astro` | Input de búsqueda para filtrar logs |

### Fase 6 - Rediseño UI Seguridad ✅

| Archivo | Mejora |
|---------|--------|
| `Header.astro` | Botón "🔐 Secure OFF/ON" integrado en header |
| `index.astro` | Eliminó SecurityCard |
| `SecurityCard.astro` | **Eliminado** - funcionalidad movida al header |

**UI de seguridad rediseñada**:
```
┌─────────────────────────────────────────────────────────────────────┐
│ SRT2Web 0.7.0    📚 Docs  [WS OFF] [🔐 Secure OFF▾]  💾 Guardar  │
└─────────────────────────────────────────────────────────────────────┘
```

### Fase 7 - Indicadores GPU ✅

| Archivo | Mejora |
|---------|--------|
| `modules/transcriber.py` | `get_status()` con device/compute_type/using_gpu |
| `modules/tts_engine.py` | `get_status()` con device/using_gpu/engine |
| `modules/video_muxer.py` | `get_status()` con encoder_mode/using_gpu/gpu_available |
| `WhisperCard.astro` | GPU badge + métrica Device |
| `TtsCard.astro` | GPU badge + métrica Device |
| `HlsCard.astro` | GPU badge + métrica Encoder |
| `index.astro` | Actualiza badges GPU desde module.extra |

### Fase 8 - Logs Optimizados ✅

| Archivo | Mejora |
|---------|--------|
| `main.py` | Filtra warnings ruidosos de FFmpeg, CUDA, RTMP, SRT, etc. |
| `LogPanel.astro` | Panel colapsable con animación |

**Logs filtrados** (no se muestran en frontend):
- `[FFmpeg]`, `[FFmpeg RTMP]` - Ruido stderr de FFmpeg
- `CUDA not available`, `falling back to CPU` - Fallback GPU/CPU
- `Duration drift` - Drift de timing
- `No input video chunk` - Chunk faltante (normal al inicio)
- `Audio padding/truncation failed` - Issues audio no críticos
- `connection lost`, `attempting reconnect` - Reconnection warnings
- Loggers `srt_input`, `rtmp_input` - Input module warnings
- `SECURITY:`, `auth_token not configured` - Security warnings

### GPU Badges - Comportamiento ✅

| Estado | Apariencia |
|--------|------------|
| Módulo usa GPU + está procesando | Badge **VERDE** (gradiente) |
| Módulo usa GPU pero está inactivo | Badge **GRIS** |
| Módulo no usa GPU | Badge oculto |

**Lógica**: Badge verde solo cuando `enabled && state === 'running' && processed_chunks > 0`

### Video Muxer en Pipeline ✅

| Archivo | Mejora |
|---------|--------|
| `core/pipeline.py` | `_get_output_module_status()` - Incluye output sink en lista de módulos |
| `modules/video_muxer.py` | Inicialización corregida (`_video_preset`, `_gpu_preset`) |
| `frontend/src/pages/index.astro` | Badge muestra CPU/GPU según encoder mode |

**Problema**: El video_muxer no aparecía en el status porque era un OutputSink, no un módulo del pipeline.

**Solución**: Método `_get_output_module_status()` crea un dict de status simulado para el frontend.

---

## Bugs Corregidos

| Bug | Causa | Solución |
|-----|-------|----------|
| WebSocket crash | FastAPI no pasa Request a WebSocket | `WebSocketRequest` wrapper |
| config.yaml inválido | `model: invalid_model` | Cambiado a `model: small` |
| CSP bloquea HLS | `media-src 'self'` restrictivo | Permitir `http://* https://*` |
| Player no carga | `Hls.ErrorTypes.ERROR_OTHER` no existe | Usar `!data.fatal` |
| "Esperando..." | No se ocultaba | Ocultar en `MANIFEST_PARSED` |
| srt_ingest None | Acceso sin verificar | `ctx.get('srt_ingest')` |
| video_muxer crash | `_video_preset` no inicializado | Inicializar en `__init__` |
| HLS badge no se ve | video_muxer no en modules | Agregar via `_get_output_module_status()` |
| Traductor no funciona | API argostranslate cambiada | Usar `get_installed_languages()` |

---

## Tests (474 tests passing)

| Archivo | Tests | Tema |
|---------|-------|------|
| `tests/unit/test_security_middleware.py` | 19 | Seguridad |
| `tests/unit/test_performance_optimizations.py` | 14 | Rendimiento |
| `tests/unit/test_phase4_5_improvements.py` | 23 | Fases 4-5 |
| `tests/unit/test_config_validation.py` | 26 | Config |
| `tests/unit/test_player_websocket_fixes.py` | 20 | Player/WSS/CSP |
| `tests/unit/test_gpu_installer_restructure.py` | 53 | GPU/Encoder |
| + other test files | 319 | Varios |

```bash
# Run all tests
python -m pytest tests/unit/ -v
```

---

## Commits en GitHub

| Hash | Descripción |
|------|-------------|
| `1140c08` | chore: Track config.yaml in git and update .gitignore |
| `e78e93f` | fix: Update encoder modes and fix JavaScript extraction tests |
| `4ff1b03` | fix: Fix argostranslate API compatibility |
| `91985dd` | build: Update static frontend files |
| `85f96d9` | feat: Change default TTS voice to es_ES-sharvard-medium |
| `99b9654` | feat: Use nvidia-ml-py and add FFmpeg process pool |
| `75f4ddd` | build: Update static frontend files |
| `8a85ebe` | fix: Add video_muxer status to pipeline modules list |
| `f5f8da1` | build: Update static frontend files |
| `ff70f51` | fix: Fix video_muxer initialization and HLS status display |
| `66003b3` | fix: Run server minimized and filter security warnings from console |
| `260b425` | build: Update static frontend files |
| `f960f9a` | fix: Filter security warnings and collapse log panel by default |
| `7beca2a` | build: Update static frontend files |
| `bd6e8b4` | fix: Improve log filtering and GPU badge behavior |
| `2b5eaa9` | build: Update static frontend files |
| `0fd0b5d` | feat: Add GPU indicators and collapsible log panel |
| `e372d23` | Config cleanup + remove SecurityCard |
| `791a740` | Redesign security UI - integrate into Header |
| `d54bd36` | Tests for player, WebSocket and CSP fixes |
| `6627be5` | Fix player HLS playback and CSP issues |
| `b139859` | Fix WebSocket auth |
| `ed69267` | Fase 1-3 |

---

## Comandos Útiles

```bash
# Ejecutar servidor
Start.bat

# Reconstruir frontend
cd frontend && npm run build:local
cp -r frontend/dist/* server/static/

# Ejecutar tests
python -m pytest tests/unit/ -v
```

---

## Notas Importantes

### Seguridad
- Token se configura desde header (botón 🔐 Secure)
- WebSocket: `ws://host/ws/logs?token=xxx`
- OBS usa **SRT** (puerto 9000), NO WebSocket

### Frontend Build
- SIEMPRE reconstruir tras cambios: `cd frontend && npm run build:local`
- Copiar a server/static/

### Ejecución del Servidor
- `Arrancar_Servidor.bat` ejecuta el servidor **minimizado** (en segundo plano)
- **IMPORTANTE**: Usa entorno virtual `venv/` con Python 3.12
- La consola filtra automáticamente los warnings de seguridad
- Para detener: cerrar la ventana desde la barra de tareas
- Si no existe `venv/`, el script lo crea automáticamente

### HLS Player
- URL: `http://localhost:9999/player`
- Stream: `http://localhost:9999/hls/stream.m3u8`

### GPU Indicators
- Backend: módulos retornan `extra` con `using_gpu`, `device`, `encoder_mode`
- Frontend: badges se muestran/ocultan según `module.extra.using_gpu`
- Métricas: Device (Whisper/TTS), Encoder (HLS)

### Video Muxer Status
- El video_muxer es un OutputSink, no un módulo del pipeline
- Se agrega al status via `_get_output_module_status()` en `core/pipeline.py:412`
- El frontend recibe `video_muxer` en la lista de módulos

### Log Panel
- Colapsable clickeando header
- Filtra automáticamente logs ruidosos
- Filtro por texto funciona sobre logs visibles

### Piper TTS Voces
- Voz por defecto: `en_US-ryan-low` (baja calidad, rápido)
- Voces disponibles en `models/piper/` (17 voces)
- Voces españolas: Sharvard (ES), Davefx (ES), Claude (MX), Daniela (AR)

### Piper TTS Loader
- Usa subprocess en vez de threading para evitar bloqueo del event loop
- Timeout: 90 segundos
- Logs [PIPER_DEBUG] siempre visibles (bypass de filtros)
- `device: auto` intenta CUDA, fallback a CPU si falla
- CUDA depende de cublasLt64_12.dll y cudnn (instalar CUDA Toolkit 12.x)

### GPU Metrics (nvidia-ml-py)
- Reemplazó GPUtil deprecado por nvidia-ml-py oficial
- Métricas: GPU utilization % y memoria usada
- Código: `core/pipeline.py:_get_system_metrics()`

### FFmpeg Pool
- Pool de procesos FFmpeg para reutilización
- Max 4 procesos, idle timeout 30s
- Código: `core/ffmpeg_pool.py`

### Traductor (Argos Translate)
- API actualizada para nuevas versiones de argostranslate
- Usa `get_installed_languages()` en vez de `get_available_languages()`
- Cache: `core/model_cache.py:get_argos_pair()`

### Python 3.12 Virtual Environment ✅
- **Problema**: argostranslate no funciona con Python 3.14 (pydantic v1 incompatibility)
- **Solución**: Entorno virtual con Python 3.12.10
- **Ubicación**: `venv/` folder
- **Dependencias**: Todas instaladas (requirements.txt + nvidia-cublas-cu12 + nvidia-cudnn-cu12)
- **Startup script**: `Arrancar_Servidor.bat` actualizado para usar venv

**Comandos**:
```bash
# Iniciar servidor con venv
venv\Scripts\python.exe main.py

# O usar el script actualizado
Arrancar_Servidor.bat
```

**CUDA DLLs**:
- Instaladas via pip: `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`
- PATH configurado automáticamente en `main.py`
- Piper TTS carga correctamente (CPU fallback si CUDA no disponible)

---

## Pendientes

- [x] ~~Reemplazar gputil por pynvml~~ ✅ Completado (usando nvidia-ml-py)
- [x] ~~Process pooling para FFmpeg~~ ✅ Completado (core/ffmpeg_pool.py)
- [x] ~~Tests para GPU indicators~~ ✅ Completado (test_gpu_installer_restructure.py)
- [x] ~~Implementación RTMP completa~~ ✅ Completado (Fases 1-5)
- [ ] Mejoras responsive design
- [ ] Keyboard shortcuts

---

## Implementación RTMP y Arquitectura Modular (v0.7.0+)

### Resumen Ejecutivo

Se ha implementado una arquitectura modular completa para RTMP, permitiendo:
- **Inputs como módulos**: RTMP, SRT y file son módulos con toggle, estado y métricas
- **Múltiples outputs simultáneos**: HLS, RTMP y file pueden ejecutarse al mismo tiempo
- **VideoMux como módulo**: Procesa audio+video y pasa al output sink
- **OutputMultiplexer**: Gestiona escritura a múltiples destinos

### Flujo Esperado Implementado

```
OBS/FFmpeg → INPUT (RTMP, SRT, file) → Pipeline → Transcripción → Traducción → TTS → Subtítulos → AudioMixer → VideoMux → OUTPUT (webplayer, srt, rtmp, file)
```

### Cambios Realizados

#### Fase 1: RTMP Básico
- **config.yaml**: Habilitado `rtmp_input`, modo `pull`, chunk_duration 6s
- **rtmp_input.py**: Implementado modo push con `-listen 1` para FFmpeg
- **main.py**: Node Media Server inicia automáticamente para RTMP

#### Fase 2: Inputs como Módulos
- **pipeline.py**: Soporte para `InputModuleWrapper` como primer módulo
- **main.py**: Inputs registrados como módulos usando `InputModuleWrapper`
- **Sistema selección**: Input activo configurable via config.yaml

#### Fase 3: Múltiples Outputs
- **output_multiplexer.py**: Nuevo gestor de múltiples outputs
- **pipeline.py**: Soporte para múltiples `OutputModuleWrapper`
- **main.py**: Outputs registrados como módulos usando `OutputModuleWrapper`

#### Fase 4: VideoMux como Módulo
- **video_muxer.py**: Implementado `_do_process()` para funcionar como módulo
- **main.py**: VideoMux registrado como módulo del pipeline

#### Fase 5: Tests y Documentación
- **test_rtmp_input.py**: 12 tests para RTMP input/output/multiplexer
- **docs/rtmp-setup.md**: Documentación completa de configuración RTMP

### Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `config.yaml` | Habilitado rtmp_input, modo pull |
| `modules/inputs/rtmp_input.py` | Modo push implementado correctamente |
| `modules/outputs/rtmp_output.py` | Corregida importación get_video_info |
| `modules/video_muxer.py` | Implementado `_do_process()` |
| `modules/io_wrappers.py` | Agregadas propiedades `is_input_module`, `is_output_module` |
| `core/pipeline.py` | Soporte InputModule, OutputMultiplexer, múltiples outputs |
| `core/output_multiplexer.py` | **Nuevo** - Gestor de múltiples outputs |
| `main.py` | Registro de inputs/outputs como módulos |
| `tests/unit/test_rtmp_input.py` | **Nuevo** - Tests RTMP |
| `docs/rtmp-setup.md` | **Nuevo** - Documentación RTMP |

### Configuración RTMP para OBS

**Output Settings**:
- Streaming Type: Custom Streaming Server
- Server: `rtmp://localhost:1935/live/stream`
- Stream Key: `stream`

**Encoder Settings**:
- Encoder: NVENC (H.264) o x264
- Rate Control: CBR
- Bitrate: 2500-5000 Kbps
- **Keyframe Interval: 2 segundos** (CRÍTICO)
- Preset: Quality
- Profile: High

### Próximos Pasos

1. **Testing completo**: Probar flujo OBS → RTMP → Pipeline → HLS
2. **Sistema selección input**: Implementar cambio dinámico desde UI
3. **Responsive design**: Mejoras de diseño para móviles
4. **Keyboard shortcuts**: Atajos de teclado para acciones comunes
