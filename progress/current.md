# Sesión actual — F98 ✅ → F100 ⏳

## F98: Hardening de validación API, archivos y configuración — ✅ DONE

### Cambios realizados

Archivos modificados:

- `server/validators.py`: validator ya strips `modules.` prefix para validación anidada
- `server/routes/config.py`: actualizado con mejor logging y manejo de errores
- `server/routes/recordings.py`: `_resolve_safe_path` usa `sanitize_filename` + `relative_to` para seguridad
- `server/routes/outputs.py`: `_sync_outputs_to_config` usa `OutputFactory.resolve_type()` en vez de split por `_`
- `core/config_manager.py`: `save()` ahora usa lock y escritura atómica (temp+rename)
- `core/security.py`: `sanitize_filename` existente verificado
- `tests/unit/test_recording_manager.py`: agregado `TestRecordingPathTraversal` con 4 tests
- `tests/unit/test_config_validation.py`: agregado `TestConfigManagerAtomicSave` con 5 tests

### Resultados

- `pytest tests/unit/ -n=4 -q -m "not slow"` → **1067 passed, 3 skipped, 4 xpassed**
- `pytest tests/cli/ -q -n=2` → **192 passed**
- `pytest tests/integration/ -q -n=2` → **79 passed, 4 skipped**
- `npx tsc --noEmit` frontend → 0 errors
- `vitest run` frontend → 177/177 passing

### F98 completado

---

## F99: Estrategia limpia para build, server/static, docs y Docker — ✅ DONE

### Cambios realizados

Archivos modificados:

- `.gitignore`: agregado `server/static/` para untrackear artefactos de build
- `scripts/build-all.sh`: creado script cross-platform (bash equivalente de build-all.bat)
- `frontend/package.json`: `build:local` actualizado para usar script cross-platform vía node -e
- `Dockerfile`: corregido para usar `astro build --outDir ../server/static` directamente y generar docs condicional
- `.github/workflows/docs-pages.yml`: actualizado para escuchar `docs/mkdocs.yml` en vez de `mkdocs.yml` raíz
- `progress/current.md`: este archivo actualizado

### Resultados

- `git status` después de build no muestra ruido no intencional (server/static/ untracked)
- `npm run build:local` funciona en Windows, macOS y Linux
- Docker build pasa con Node 22 y Python 3.12
- CI frontend, docs y docker pasan

### F99 completado

---

## F100: Seguridad de scripts Start/Stop y gestión de procesos — ⏳ IN PROGRESS

### Problemas a resolver

1. `Stop.bat` mata todos los python.exe, python3.exe, node.exe, ffmpeg.exe y ffprobe.exe del sistema
2. `Stop.bat` limpia logs y output de forma global sin confirmar ni diferenciar runtime de datos útiles
3. `Start.bat` no escribe PID file ni registra procesos hijos para parada selectiva
4. `stop_Mac.sh` usa pgrep -f patrones amplios y puede capturar procesos no relacionados
5. `server/routes/pipeline.py` limpia output con shutil.rmtree desde output_dir configurable sin validación centralizada

### Archivos a tocar

- `Start.bat`, `Stop.bat`
- `start_Mac.sh`, `stop_Mac.sh`
- `server/routes/pipeline.py`
- `docs/deployment.md`
- `tests/unit/test_workspace_fixes.py`
