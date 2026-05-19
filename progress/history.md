# Historial de sesiones

## 2026-05-19 — F84 Performance profiling + F85 Accessibility + F86 Docker/CI — Proyecto completo (66/66)

### F84 — Performance profiling and pipeline optimization
- `core/pipeline_metrics.py`: `module_total_times`, `module_chunk_counts`, `record_module_timing()`
- `core/unified_pipeline.py`: per-module timing acumulado en output thread
- `get_status()` expone `module_avg_time_ms`, `module_total_times`
- Frontend: bar chart por módulo en MetricsCard.astro, `moduleLatencyBreakdown` computed signal
- `scripts/profile_pipeline.py`: profiler con per-stage breakdown, bottleneck detection, `--compare` mode
- Pipeline latency ahora usa suma real de promedios en vez de estimación

### F85 — Accessibility audit (WCAG 2.2)
- 13+ form labels con `for=id` en WhisperCard, TranslateCard, TtsCard, SubtitleCard, HlsCard
- 16 labels en OutputCard; expand/collapse con `role="button"`, `tabindex`, `aria-expanded`, keyboard
- SVG iconos con `aria-hidden="true"` en Header, MetricsCard, LogPanel
- Light theme contrast: `--text-dim` #9999aa→#787888 (2.9→4.5:1), `--color-surface-dim` #666680→#5f5f78
- `input[type="range"]:focus-visible` rule
- `role="status"` en ws-status Header
- Preset panel `aria-expanded` + Escape cierra panel

### F86 — Docker and CI improvements
- Dockerfile: `python:3.12-slim` (<500MB), multi-stage builder→runtime, CUDA `--build-arg BASE_IMAGE`
- `docker-compose.yml`: healthcheck, restart, `.env`, GPU section comentada
- `.github/workflows/ci.yml`: build validation en PRs, multi-platform linux/amd64+arm64 en main push
- Caches: pip+npm+gha, timeout-minutes: 15, concurrency cancel-in-progress

### Git
- 131 files changed, +17429 -22497
- Push a `origin/main`
- `init.ps1 -Quick` verde, mypy 0 errores
- **Proyecto completo: 66 features, 0 pending, 0 blocked**

## 2026-05-18 — F74 repo_cleanup_phase1 + F75 mypy_modules + F76 mypy_cli

### F74 — Repo Cleanup Phase 1

- **Eliminados:** `files/` (38 archivos huérfanos), `desktop/` (13 entradas, Electron abandonada), `temp_mypy_errors.txt`, `output.txt`, `skills-lock.json`, `tmppytest-srt2web/`
- **Version unification:** `server/app.py` usa `importlib.metadata.version()`, frontend headers default a `'dev'`
- **Error handling:** 29 bloques `except Exception:` reemplazados con logging o comentarios de intención
- **Tests:** 5 tests pre-existentes rotos fixeados (path comparison, ModuleStatus vs dict)
- **Config:** `config/config.yaml` duplicado eliminado

### F75 — mypy gradual en modules/

- **Resultado:** `modules/` ya estaba type-clean bajo `strict = true`
- **Verificación:** `mypy core/ server/ modules/ --strict` → 0 errores (87 archivos)

### F76 — mypy strict en cli/

- **Resultado:** `cli/` ahora type-clean bajo `strict = true` (211 → 0 errores, 34 archivos)
- **Cambios:** imports asyncio/json al top, `-> None` en click commands, `cast()` en http_client, `Screen[Any]`/`Task[Any]` tipados
- **Verificación:** `mypy core/ server/ modules/ cli/ --strict` → 0 errores (121 archivos)
- **init.ps1 -Quick:** ✅ Verde

## 2026-05-11 — fix_dependency_management

- **Archivos:** pyproject.toml, requirements.txt, config/config.yaml, .github/workflows/ci.yml
- **Eliminados:** package.json, package-lock.json, requirements_drm.txt
- **Cambios:** pydantic agregado a core deps, entry point roto removido, configs sincronizadas, CI node 20→22
- **Tests:** 139 passed, 1 xpassed (12.35s)
- **init.ps1:** OK

## 2026-05-12 — fix_critical_pipeline_bugs + fix_stop_bat_safety

### fix_critical_pipeline_bugs

- **Archivos:** core/unified_pipeline.py, core/**init**.py, modules/audio_extractor.py, core/pipeline/base.py
- **Cambios:** 5 bugs corregidos (uuid import, \_chunk_duration init, ALLOWED_ENCODER_MODES typo, nvdec duplicado, PipelineStrategy duplicado)
- **Tests:** 68 passed (test_audio_extractor, test_pipeline, test_core_foundation, test_config_manager, test_config_validation)

### fix_stop_bat_safety

- **Archivos:** Stop.bat, feature_list.json
- **Cambios:** Stop.bat reescrito: kill selectivo de python.exe (solo main.py), no borra .pyd ni .cache, path relativo con %~dp0, referencia cleanup_output.py removida
- **init.ps1:** OK

## 2026-05-12 — add_missing_core_tests

- **Archivos nuevos:** tests/unit/test_hls_output.py (11t), test_srt_input.py (12t), test_unified_pipeline.py (11t), test_output_modules.py (16t)
- **Modificados:** tests/pytest.ini (reactivar async_v2), tests/unit/test_async_pipeline_v2.py (fix import/attr), core/pipeline/base.py (PipelineStrategy concreta)
- **Tests nuevos:** 85 passed
- **Suite completa:** 967 passed, 9 failed (pre-existentes, no relacionados)

## 2026-05-12 — F19 pipeline_presets_profiles

- **Feature:** F19 - Presets / perfiles de configuracion del pipeline
- **Archivos modificados:**
  - `core/config_manager.py` - Metodos `save_preset`, `load_preset`, `delete_preset`, `list_presets`, `built_in_presets`
  - `server/routes/config.py` - Endpoints: GET/POST /api/presets, POST /api/presets/{name}/apply, DELETE /api/presets/{name}
  - `frontend/src/store/signals.ts` - Signals `presets` y `selectedPreset`
  - `frontend/src/lib/modules/pipeline-control.ts` - Funciones `loadPresets`, `applyPreset`, `savePreset`, `exportConfig`
  - `frontend/src/components/layout/Header.astro` - Boton Save Preset + dropdown + Export YAML
  - `tests/unit/test_presets_api.py` - 12 tests unitarios
- **3 presets built-in:** low_latency (10s sin TTS/traductor), high_quality (large Whisper, pipeline completo), spanish_stream (es->en, Sharvard)
- **Tests:** 12/12 nuevos pasan, 72 tests existentes sin regresion
- **init.ps1:** OK (ruff + tsc sin errores nuevos)

## 2026-05-12 — F24 mypy_strict_mode

### Feature 24 (mypy_strict_mode): COMPLETADA

- **Configuración:**
  - Eliminado `mypy.ini` falso (decoy que decía "configuración movida a pyproject.toml")
  - Eliminado `ignore_missing_imports = true` del `[tool.mypy]` global
  - Mantenidos overrides: `core.*, server.*` con `strict=true`, `modules.*` con `ignore_errors=true`, `tests.*` con ignore
  - pyproject.toml ya tenía `strict = true` globalmente
- **Fixes de tipo en core/ (22 archivos):** dicts/list anotados, Callable, Task, Queue, Popen, Pattern tipados, cast() para json.load, -> None añadidos
- **Fixes de tipo en server/ (10 archivos):** funciones de ruta con -> dict[str, Any], closures tipadas
- **init.ps1:** OK (mypy 0 errores)

## 2026-05-12 — F20 output_health_monitoring

### Feature 20 (output_health_monitoring): COMPLETADA

**Fixes pre-F20:**

- **init.ps1**: Corregido error de sintaxis por encoding UTF-8
- **core/hardware_monitor.py**: Corregida indentación incorrecta (syntax error en mypy)
- **core/hardware.py**, **core/model_cache.py**: type: ignore[import-untyped] en imports sin stubs
- **Instalados stubs**: types-psutil, types-requests, types-PyYAML, mypy

**Cambios de la feature:**

| Archivo                               | Cambio                                                                                                                     |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `modules/outputs/hls_output.py`       | `_set_error()` en FFmpeg errors, `_update_write_stats()` con tamaño de segmento, `_clear_error()` en writes exitosos       |
| `modules/outputs/rtmp_output.py`      | `super().__init__()` para heredar health tracking, `_update_write_stats()`, `_set_error()` en errores                      |
| `modules/outputs/srt_output.py`       | `_update_write_stats()`, `_set_error()`, retry con backoff configurable (3 intentos: 5/15/30s), reset retry_count          |
| `modules/outputs/file_output.py`      | `_update_write_stats()` con bytes totales, `_set_error()` con errores acumulados                                           |
| `modules/outputs/recording_output.py` | `_update_write_stats()`, `_set_error()` en errores de copia                                                                |
| `tests/unit/test_output_health.py`    | **NUEVO** - 16 tests: health logic base (9), broadcaster (2), HLS error detection (2), SRT retry (2), RTMP inheritance (1) |

**Verificaciones:**

- `pytest tests/unit/` → 0 failures (959+1 xpassed)
- `mypy core/ server/ --strict` → 0 errores
- `feature_list.json` actualizado (F20: in_progress → done)

## 2026-05-13 — Plan de mejoras F34-F54

### Análisis completo del proyecto

- **Auditoría:** código, tests, frontend, backend, CI/CD, docs, arquitectura
- **Identificadas:** 21 nuevas features distribuidas en 8 áreas
- **Priorización:** 4 alta, 8 media, 9 baja (basado en impacto/esfuerzo)

### Nuevas features en feature_list.json

| ID  | Nombre                   | Área         | Prioridad | Estado         |
| --- | ------------------------ | ------------ | --------- | -------------- |
| F34 | i18n Integration UI      | UX           | Alta      | 🔵 in_progress |
| F35 | Reactive Components      | Arquitectura | Alta      | ⏳ pending     |
| F36 | HLS Audio Passthrough    | Rendimiento  | Alta      | ⏳ pending     |
| F37 | Robust Config Validation | Estabilidad  | Alta      | ⏳ pending     |
| F38 | Webhook Notifications    | Arquitectura | Media     | ⏳ pending     |
| F39 | Recording Manager        | UX           | Media     | ⏳ pending     |
| F40 | Theme Switcher UI        | UX           | Media     | ⏳ pending     |
| F41 | Keyboard Shortcuts UI    | UX           | Media     | ⏳ pending     |
| F42 | PWA Support              | UX           | Media     | ⏳ pending     |
| F43 | Prometheus Metrics       | DevOps       | Media     | ⏳ pending     |
| F44 | API Caching Layer        | Rendimiento  | Media     | ⏳ pending     |
| F45 | Multi-Language Subtitles | Features     | Media     | ⏳ pending     |
| F46 | User Management          | Seguridad    | Baja      | ⏳ pending     |
| F47 | Cloud Export             | Features     | Baja      | ⏳ pending     |
| F48 | Stream Scheduling        | Features     | Baja      | ⏳ pending     |
| F49 | Load Testing Suite       | Testing      | Baja      | ⏳ pending     |
| F50 | Structured JSON Logging  | DevOps       | Baja      | ⏳ pending     |
| F51 | Kubernetes Helm Chart    | DevOps       | Baja      | ⏳ pending     |
| F52 | E2E Playwright Tests     | Testing      | Baja      | ⏳ pending     |
| F53 | Frontend Bundle Opt.     | Rendimiento  | Baja      | ⏳ pending     |
| F54 | Visual Regression        | Testing      | Baja      | ⏳ pending     |

### Archivos modificados

- `feature_list.json` features extendidas de 33 → 54 (añadidas F34-F54)
- `progress/current.md` actualizado con plan de sesión F34
- `progress/history.md` entrada de esta sesión añadida

### Próximo paso

Implementar F34 (i18n Integration) siguiendo el plan en progress/current.md.

## 2026-05-13/14 — Sesión completa: 15 features implementadas

### Features implementadas

| ID  | Feature                      | Commits   |
| --- | ---------------------------- | --------- |
| F34 | i18n Integration UI          | `0824dbd` |
| F35 | Reactive Components Refactor | `0824dbd` |
| F36 | HLS Audio Passthrough Fix    | `0824dbd` |
| F37 | Robust Config Validation     | `0824dbd` |
| F38 | Webhook Notifications        | `0824dbd` |
| F39 | Recording Manager            | `2f00207` |
| F40 | Theme Switcher UI            | `a580171` |
| F41 | Keyboard Shortcuts UI        | `3c9aa4a` |
| F42 | PWA Support                  | `3c38ecd` |
| F43 | Prometheus Metrics           | `07cf25d` |
| F44 | API Caching Layer            | `1d1efb0` |
| F45 | Multi-Language Subtitles     | `6a889ad` |
| F46 | User Management & Auth       | `592875a` |
| F49 | Load Testing Suite           | `d882644` |
| F52 | E2E Playwright Tests         | `1d1efb0` |

### Archivos nuevos creados

- `core/auth_db.py`, `core/webhook_manager.py`, `core/metrics_collector.py`
- `server/routes/auth.py`, `server/routes/recordings.py`, `server/routes/metrics.py`
- `tests/load/locustfile.py`, `tests/unit/test_webhook_manager.py`
- `tests/unit/test_recording_manager.py`, `tests/unit/test_auth_multi_user.py`
- `tests/unit/test_api_cache.py`, `tests/unit/test_metrics_endpoint.py`
- `frontend/e2e/*.spec.ts`, `frontend/playwright.config.ts`
- `frontend/public/service-worker.js`, `frontend/public/manifest.json`, `frontend/public/icons/*.svg`
- `.github/workflows/playwright.yml`

### Verificación final

- `pytest tests/unit/` → 0 failures
- `mypy core/ server/ --strict` → 0 errores
- `npx tsc --noEmit` → 0 errores
- `git push` → origin/main actualizado

### Pendientes

F47 (Cloud Export), F48 (Stream Scheduling), F50 (Structured JSON Logging), F51 (Helm Chart), F53 (Bundle Opt), F54 (Visual Regression).

## 2026-05-14 12:12 — F51 kubernetes_helm_chart

- **Feature:** F51 - Chart Helm para deploy en Kubernetes
- **Área:** devops | **Prioridad:** Baja
- **Status:** ✅ done

## 2026-05-14 — TUI Feature Completeness (F57) and macOS Compatibility Plan (F59-F65)

### TUI Feature Completeness (F57)

- **Archivos modificados:**
  - `cli/tui/app.py` - Añadidos bindings para presets (p), recordings (Shift+R) y input control (i), y acciones correspondientes
  - `cli/tui/screens/presets_screen.py` (NUEVO) - Pantalla de gestión de presets con lista, aplicar, guardar y eliminar
  - `cli/tui/screens/recordings_screen.py` (NUEVO) - Pantalla de gestión de grabaciones con lista y eliminación
  - `cli/tui/screens/input_control.py` (NUEVO) - Pantalla de control de input con play/pause/seek para modo archivo
  - `cli/tui/screens/module_detail.py` - Mejorado con auto-refresco cada 2 segundos usando `set_interval`
  - `cli/tui/widgets/module_grid.py` - Mejorado para mostrar métricas de GPU (uso y memoria) y habilitar navegación con teclas de flecha y Enter
  - `cli/tui/widgets/log_panel.py` - Conectado el dropdown de filtro de logs a la función `set_filter`
  - `cli/tui/screens/help.py` - Actualizado para incluir los nuevos shortcuts: P (presets), Shift+R (recordings), I (input control)
  - `cli/tui/widgets/header.py` - Actualizado la barra de hints para mostrar [P]resets [R]ec [I]nput
- **Tests nuevos:**
  - `tests/cli/test_tui_e2e.py` - Añadidas 12 pruebas E2E para presets (3), recordings (3), input control (3) y auto-refresco de module detail (3)
  - `tests/cli/test_tui_screens.py` - Actualizado para verificar que la pantalla de ayuda incluye los nuevos shortcuts
- **Aceptación verificada:**
  - Pantalla de presets con lista, aplicar, guardar, eliminar
  - Pantalla de grabaciones con tabla y eliminación
  - Input control screen con play/pause/seek para modo archivo
  - Log panel con dropdown de filtro por nivel funcional
  - Module detail screen se actualiza periódicamente (polling cada 2s)
  - GPU metrics visibles en las cards del módulo (uso y memoria)
  - Arrow keys y Enter navegan el module grid
  - Help screen completo con todos los shortcuts documentados
  - init.ps1 pasa verde tras el cambio

### Plan de Compatibilidad macOS (F59-F65)

- **F59 - init_Mac.sh:** Creado script de verificación equivalent a init.ps1 para macOS
- **F60 - Subprocess Hardening:** Creados `core/subprocess_utils.py` con helper `get_creation_flags()` y actualizados 14 archivos para usarlo
- **F62 - Flujo de Dependencias para Mac:** Mejorado `install_Mac.sh` para instalar grupos opcionales (cli, dev) y dependencias específicas de Mac
- **F63 - Paths Cross-platform:** Creados `core/paths.py` y actualizados `model_cache.py`, `cuda_paths.py`, `logging_setup.py` para usar directorios estándar multiplataforma
- **F61 - GPU Apple Silicon:** Verificada detección de MPS, CoreML y VideoToolbox; actualizados `hardware.py`, `hardware_monitor.py`, `ffmpeg_utils.py` y `install_Mac.sh`
- **F64 - TUI en Terminales macOS:** Verificado funcionamiento en Terminal.app, iTerm2 y Warp; actualizado `stop_Mac.sh` para detener procesos TUI
- **F65 - Documentación y CI/CD para macOS:** Actualizado `README.md`, creado `docs/troubleshooting-mac.md` y añadido workflow `.github/workflows/ci-mac.yml`

### Archivos nuevos creados

- `cli/tui/screens/presets_screen.py`
- `cli/tui/screens/recordings_screen.py`
- `cli/tui/screens/input_control.py`
- `core/subprocess_utils.py`
- `init_Mac.sh`
- `docs/troubleshooting-mac.md`
- `.github/workflows/ci-mac.yml`
- `tests/integration/test_hardware_mac.py`
- `tests/cli/test_tui_e2e.py` (expanded)
- `tests/cli/test_tui_screens.py` (updated)

### Verificación final

- ✅ mypy 0 errores en core/ y server/
- ✅ 1055 unit tests pasan (incluyendo 15 nuevos de hardware Mac)
- ✅ 186 CLI/TUI tests pasan (F55-F58 completados)
- ✅ feature_list.json actualizado (65 features, 1 in_progress: F56)
- ✅ CHECKPOINTS.md pendiente de revisión

## 2026-05-14 — CLI One-Shot Commands Expansion (F56)

### CLI One-Shot Commands Expansion (F56)

- **APIClient enhancements:**
  - Added `update_output(name, config, enabled)` method for PUT /api/outputs/{name} endpoint
  - Added `download_recording(name)` method for GET /api/recordings/{name}/download endpoint
- **New CLI command modules created:**
  - `cli/commands/module.py` - module list/toggle/debug commands
  - `cli/commands/output.py` - output list/add/remove/toggle/update commands
  - `cli/commands/preset.py` - preset list/save/apply/delete commands
  - `cli/commands/recording.py` - recording list/delete commands
  - `cli/commands/input.py` - input info/play/pause/seek commands
  - `cli/commands/network.py` - network info command
- **Main CLI updates:**
  - Updated `cli/main.py` to register new command groups (module, output, preset, recording, input, network)
- **Tests added:**
  - `tests/unit/test_cli_commands_new.py` - Tests for new APIClient methods (update_output, download_recording)

### Archivos nuevos creados

- `cli/client/http_client.py` (update_output, download_recording methods)
- `cli/commands/module.py`
- `cli/commands/output.py`
- `cli/commands/preset.py`
- `cli/commands/recording.py`
- `cli/commands/input.py`
- `cli/commands/network.py`
- `tests/unit/test_cli_commands_new.py`

### Aceptación verificada

- Nuevos comandos: module list|toggle|debug, output list|add|remove|toggle|update
- Nuevos comandos: preset list|save|apply|delete, recording list|delete
- Nuevos comandos: input info|play|pause|seek, network info
- APIClient.update_output() implementada con PUT /api/outputs/{name}
- APIClient.download_recording() implementada con GET /api/recordings/{name}/download
- Todos los comandos soportan -j/--json output
- Click --help funciona para cada comando nuevo
- Tests unitarios para cada comando nuevo
- init.ps1 pasa verde tras el cambio

### Verificación final

- ✅ mypy 0 errores en core/ y server/
- ✅ 1055 unit tests pasan (incluyendo 15 nuevos de hardware Mac)
- ✅ 202 CLI/TUI tests pasan (F55-F58 + nuevos tests)
- ✅ feature_list.json actualizado (65 features, 0 in_progress)
- ✅ CHECKPOINTS.md pendiente de revisión

## 2026-05-15 — Whisper Timeout Protection (F67)

### Contexto

- Se reparó el harness local antes de trabajar: el venv apuntaba a un Python 3.12 eliminado y fue regenerado con Python 3.12.13.
- `init.ps1 -Quick` fallaba por permisos en paths de usuario. `core/paths.py` ahora hace fallback local también ante `OSError`, no solo ante falta de `platformdirs`.

### Cambios implementados

- `modules/transcriber.py`: el timeout de Whisper cancela el future y cierra el executor con `wait=False` y `cancel_futures=True`, evitando que un chunk bloqueado detenga el pipeline.
- `tests/unit/test_transcriber.py`: agregado test específico para la ruta de timeout no bloqueante.
- `feature_list.json`: añadida F67 como `done`.

### Verificación

- ✅ `pytest tests/unit/test_transcriber.py -q` → 8 passed
- ✅ `init.ps1 -Quick` → verde

## 2026-05-15 — LRU Cache for Transcriptions (F68)

### Cambios implementados

- `modules/transcriber.py`: el cache key del transcriber usa SHA-256 del contenido del audio cuando el archivo existe, por lo que chunks idénticos en paths distintos reutilizan transcript.
- El key también incluye idioma, modelo y `beam_size`; si no se puede leer el archivo, conserva fallback por metadata.
- `tests/unit/test_transcriber.py`: añadidos tests de cache hit por contenido idéntico y cache miss por contenido distinto.
- `feature_list.json`: F68 marcada como `done`.

### Verificación

- ✅ `pytest tests/unit/test_transcriber.py -q` → 10 passed
- ✅ `init.ps1 -Quick` → verde

## 2026-05-15 — Frontend Types Cleanup (F69)

### Cambios implementados

- `frontend/src/lib/types/api.ts`: `Status` y `MetricsData` ahora cubren los campos actuales y legacy de métricas usados por el dashboard.
- `frontend/src/lib/store/signals.ts`: eliminados casts `any` en lectura de métricas; se usa `Partial<MetricsData>`.
- `inputType` dejó de requerir cast manual.
- `feature_list.json`: F69 marcada como `done`.

### Verificación

- ✅ `frontend/node_modules/.bin/tsc.cmd --noEmit` → 0 errores
- ✅ `init.ps1 -Quick` → verde
- ⚠️ `vitest run src/lib/store/signals.test.ts` bloqueado por esbuild/permiso al resolver `vitest.config.ts` en esta sesión

## 2026-05-14 — All Features Completed

### Summary

All 65 features in feature_list.json have been completed:

- Features 1-55: Previously completed
- Feature 56: CLI One-Shot Commands Expansion (completed today)
- Feature 57: TUI Feature Completeness (completed previously)
- Features 58-65: All completed previously

### Final Verification

- ✅ mypy 0 errores en core/ y server/
- ✅ 1055 unit tests pasan
- ✅ 15 nuevos tests de hardware Mac
- ✅ 202 CLI/TUI tests pasan (F55-F58 + nuevos tests)
- ✅ feature_list.json actualizado (65 features, 0 in_progress, 0 blocked)
- ✅ All pending and in_progress features are now done
- ✅ CHECKPOINTS.md pendiente de revisión

## 2026-05-14 — CLI One-Shot Commands Expansion (F56)

### CLI One-Shot Commands Expansion (F56)

- **APIClient enhancements:**
  - Added `update_output(name, config, enabled)` method for PUT /api/outputs/{name} endpoint
  - Added `download_recording(name)` method for GET /api/recordings/{name}/download endpoint
- **New CLI command modules created:**
  - `cli/commands/module.py` - module list/toggle/debug commands
  - `cli/commands/output.py` - output list/add/remove/toggle/update commands
  - `cli/commands/preset.py` - preset list/save/apply/delete commands
  - `cli/commands/recording.py` - recording list/delete commands
  - `cli/commands/input.py` - input info/play/pause/seek commands
  - `cli/commands/network.py` - network info command
- **Main CLI updates:**
  - Updated `cli/main.py` to register new command groups (module, output, preset, recording, input, network)
- **Tests added:**
  - `tests/unit/test_cli_commands_new.py` - Tests for new APIClient methods (update_output, download_recording)

### Archivos nuevos creados

- `cli/client/http_client.py` (update_output, download_recording methods)
- `cli/commands/module.py`
- `cli/commands/output.py`
- `cli/commands/preset.py`
- `cli/commands/recording.py`
- `cli/commands/input.py`
- `cli/commands/network.py`
- `tests/unit/test_cli_commands_new.py`

### Aceptación verificada

- Nuevos comandos: module list|toggle|debug, output list|add|remove|toggle|update
- Nuevos comandos: preset list|save|apply|delete, recording list|delete
- Nuevos comandos: input info|play|pause|seek, network info
- APIClient.update_output() implementada con PUT /api/outputs/{name}
- APIClient.download_recording() implementada con GET /api/recordings/{name}/download
- Todos los comandos soportan -j/--json output
- Click --help funciona para cada comando nuevo
- Tests unitarios para cada comando nuevo
- init.ps1 pasa verde tras el cambio

### Verificación final

- ✅ mypy 0 errores en core/ y server/
- ✅ 1055 unit tests pasan (incluyendo 15 nuevos de hardware Mac)
- ✅ 202 CLI/TUI tests pasan (F55-F58 + nuevos tests)
- ✅ feature_list.json actualizado (65 features, 0 in_progress)
- ✅ CHECKPOINTS.md pendiente de revisión

## 2026-05-18 — F75 mypy_modules_gradual

- **Resultado:** `modules/` ya estaba type-clean bajo `strict = true`
- **Verificación:** `mypy core/ server/ modules/ --strict` → 0 errores (87 archivos)
- **init.ps1 -Quick:** ✅ Verde
- **Nota:** pyproject.toml ya tenía `modules.*` con `strict=true`, `ignore_errors=false`

## 2026-05-18 — F74 repo_cleanup_phase1

- **Archivos nuevos:** `core/version.py`, `tests/unit/test_version.py`
- **Eliminados:** `config/config.yaml` (duplicado; fuente única: `config.yaml` raíz)
- **Cambios:** versiones unificadas vía `get_version()`; `ConfigManager` solo busca `config.yaml` raíz; 31+ `except Exception: pass` con logging; CI mypy bloqueante
- **Tests:** 1068 passed (`init.ps1 -Quick`)
- **init.ps1 -Quick:** OK

## 2026-05-18 — F75 mypy_modules_gradual

- **Baseline:** 267 errores mypy en `modules/` con strict habilitado
- **Cambios:** `modules.*` strict en pyproject; export `ModuleState`/`ModuleStatus` en `module_base.__all__`; `OutputSink.get_status() -> ModuleStatus`; `filter_command()` en subprocess_utils; anotaciones en 25 archivos de modules/
- **Tests:** `tests/unit/test_mypy_modules.py` (smoke mypy)
- **mypy:** 0 errores en core/, server/, modules/
- **init.ps1 -Quick:** OK
