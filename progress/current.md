# Sesión activa — 2026-05-11

**Feature:** 1 — fix_dependency_management
**Inicio:** 00:00
**Estado:** en_progreso

## Plan

- [x] Leer archivos clave a modificar
- [x] Arreglar pyproject.toml (pydantic, entry point)
- [x] Crear requirements.txt raíz
- [x] Resolver conflicto config.yaml raíz vs config/config.yaml
- [x] Arreglar CI (node version, pip install)
- [x] Limpiar artifacts raíz (package.json, package-lock, requirements_drm.txt)
- [ ] Verificar con init.ps1

## Archivos tocados

- `pyproject.toml` — agregado pydantic>=2.0.0 a core deps, removido entry point `scripts.cli:main`
- `requirements.txt` — creado en raíz (ref a config/requirements.txt)
- `config/config.yaml` — sincronizado con root config.yaml (SRT port 9000, módulos enabled)
- `.github/workflows/ci.yml` — node 20→22, pip install ruta fija, continue-on-error limpiado
- `package.json` — eliminado (accidental npm install en raíz)
- `package-lock.json` — eliminado
- `requirements_drm.txt` — eliminado (orphan)
