# Historial de sesiones

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

| ID | Feature | Commits |
|----|---------|---------|
| F34 | i18n Integration UI | `0824dbd` |
| F35 | Reactive Components Refactor | `0824dbd` |
| F36 | HLS Audio Passthrough Fix | `0824dbd` |
| F37 | Robust Config Validation | `0824dbd` |
| F38 | Webhook Notifications | `0824dbd` |
| F39 | Recording Manager | `2f00207` |
| F40 | Theme Switcher UI | `a580171` |
| F41 | Keyboard Shortcuts UI | `3c9aa4a` |
| F42 | PWA Support | `3c38ecd` |
| F43 | Prometheus Metrics | `07cf25d` |
| F44 | API Caching Layer | `1d1efb0` |
| F45 | Multi-Language Subtitles | `6a889ad` |
| F46 | User Management & Auth | `592875a` |
| F49 | Load Testing Suite | `d882644` |
| F52 | E2E Playwright Tests | `1d1efb0` |

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
