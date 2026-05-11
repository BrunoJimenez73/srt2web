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
