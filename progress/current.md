# Sesión activa — 2026-05-12

**Estado:** F19 DONE
**Iniciada:** 2026-05-12

## Resumen de la sesión

### Feature 19 (pipeline_presets_profiles): COMPLETADA

- **Backend:**
  - `core/config_manager.py`: Métodos `save_preset`, `load_preset`, `delete_preset`, `list_presets`, `built_in_presets`
  - `server/routes/config.py`: 4 endpoints nuevos — GET /presets, POST /presets, POST /presets/{name}/apply, DELETE /presets/{name}
  - 3 presets built-in: low_latency, high_quality, spanish_stream

- **Frontend:**
  - `signals.ts`: Signals `presets` y `selectedPreset`
  - `pipeline-control.ts`: `loadPresets`, `applyPreset`, `savePreset`, `exportConfig`
  - `Header.astro`: Botón Save Preset con dropdown + botón Export YAML

- **Tests:**
  - `tests/unit/test_presets_api.py`: 12 tests unitarios (12/12 passing)
  - 72 tests existentes sin regresión

## Features completadas en esta sesión

- F19: pipeline_presets_profiles

## Próxima

- F20: output_health_monitoring
- F21: config_push_via_websocket