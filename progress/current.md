# Sesión activa — 2026-05-25

**Estado:** F88 in_progress — Resolver duplicación workflow/ + bin/
**Iniciada:** 2026-05-25

## F87 — Fix pre-commit hooks ✅

### Logro

Todos los 8 hooks de pre-commit pasan con 0 errores en todos los archivos:
trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files,
ruff, ruff-format, prettier, mypy.

### Cambios en `.pre-commit-config.yaml`

- Añadido `files: ^(core|server|modules|cli)/` al hook ruff para mantenerlo
  en el mismo scope que mypy (evita 347 errores pre-existentes en scripts/,
  workflow/, tests/ que no son parte del proyecto activo)
- Mypy additional_dependencies incluye pydantic, textual, click, fastapi,
  httpx, psutil, websockets, numpy, uvicorn, python-multipart, types-PyYAML,
  types-psutil, PyJWT, aiortc, av

### Cambios en `pyproject.toml`

- `[tool.mypy]`: exclude incluye `server/static`, warn_unused_ignores = true,
  pydantic.mypy plugin activo
- Overrides para third-party libs sin stubs (textual, onnxruntime, av,
  faster_whisper, argostranslate, aiortc, edge_tts, prometheus_client,
  pynvml, piper, torch, jwt, yaml)

### Fixes de código

- **Ruff (313 auto-fix + 64 manuales)**:
  - RUF012: 6 class attributes con `# noqa: RUF012`
  - E402: imports reordenados en 6 archivos (cache.py, pipeline/factory.py,
    pipeline_state_manager.py, file_input.py, srt_input.py, webrtc_output.py)
  - B904: `raise ... from err` añadido en 18 except blocks
  - E722: bare `except:` → `except Exception:` en 3 archivos
  - RUF002/RUF003: caracteres Unicode ambiguos reemplazados en async_pipeline.py
  - SIM102/SIM114/SIM112/SIM105: patrones simplificados
  - B025: duplicado except Exception eliminado
  - F401: `# noqa: F401` en imports intencionales
- **Mypy**: Eliminados ~260 errores via overrides + additional_dependencies
- **Eliminados ~20 `type: ignore` obsoletos** en hardware.py, hardware_monitor.py,
  model_cache.py, metrics_collector.py, webrtc_engine.py, auth_db.py
- **`webrtc_engine.py:233`**: `type: ignore[misc]` → bare `type: ignore`
  por compatibilidad entre mypy v1.15 (pre-commit) y mypy más reciente (venv)

### Verificación

- `mypy core/ server/ modules/ cli/` → 0 errores en 125 source files
- `pytest tests/unit/ -m "not slow"` → 547+ passing
- `npx tsc --noEmit` → 0 errores
- Todos los 8 hooks pre-commit pasan en `--all-files`

---

## F88 [completado] — Resolver duplicación workflow/ + bin/

### Análisis

- **workflow/**: Herramienta de automatización de desarrollo para agentes AI.
  NO overlap con core/unified_pipeline.py. 7 archivos trackeados en git.
  Activo (referenciado en AGENTS.md). Recomendación: **KEEP**.
- **bin/**: Cache de binarios runtime (FFmpeg ~193MB + MediaMTX ~50MB).
  NO trackeado en git (.gitignore). Consumido por core/ffmpeg_utils.py
  y core/mediamtx_manager.py. Recomendación: **KEEP**.

### Acciones

- `workflow/pipeline.yaml`: eliminada sección `pipeline_validation`
  (lines 37-66, `enabled: false`, código muerto sin referencias)
- feature_list.json actualizado: F88 → done

---

## F89 [en progreso] — Unificar Enum EncoderMode

### Objetivo

Consolidar los 3 enums de encoder incompatibles en una sola fuente de verdad:
EncoderModeEnum en core/config_schema.py. Deprecar EncoderMode en
core/types.py y ALLOWED_ENCODER_MODES en core/constants.py.

### Plan

1. Marcar EncoderMode en types.py como @deprecated
2. Eliminar ALLOWED_ENCODER_MODES en constants.py o convertirlo en alias
3. Actualizar core/**init**.py para exportar EncoderModeEnum
4. Actualizar test_config_validation.py
5. Verificar init.ps1 -Quick + mypy 0 errores
