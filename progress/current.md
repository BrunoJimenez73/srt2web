# Sesión activa — 2026-05-12

**Feature:** 8 — fix_ci_and_config_inconsistencies
**Inicio:** now
**Estado:** done

## Cambios realizados

### CI node version

- `.github/workflows/ci.yml`: ya usaba `node-version: "22"` (compatible con `>=22.12.0`)
- `files/ci.yml`: ejemplo actualizado de `NODE_VERSION: '18'` → `'22'`

### pip install en CI / docs

- `docs/index.md`, `docs/contributing.md`, `docs/deployment.md`: `pip install -r requirements.txt` → `config/requirements.txt`
- `Dockerfile`: `COPY requirements.txt` + `RUN pip install -r requirements.txt` → `config/requirements.txt`

### CI frontend tests

- `.github/workflows/ci.yml`: `npm test || true` → `npm test` (ya no oculta fallos)

### player.astro SRI

- Versión HLS.js unificada: `1.5.1` → `1.5.7` (match con `core/constants.py`)
- Atributo `integrity="sha384-..."` agregado con hash SHA-384 + `crossorigin="anonymous"`

### audio_samplerate/audio_sample_rate

- `core/config_schema.py`: eliminado campo `audio_samplerate` (string, no usado en código)
- `config.yaml`, `config/config.yaml`, `frontend/config.yaml`, `config.yaml.backup`: eliminada línea `audio_samplerate: '48000'`
- `docs/deployment.md`: eliminada línea `audio_samplerate: "48000"`

### Tests

- `test_complete_refactor.py::test_10_modules_integrated`: actualizado para verificar que stubs muertos fueron eliminados y módulos activos existen

## Resultados

- 0 new failures. Pre-existentes: 10 failures (idénticos)
- Config tests: 101 passed, 1 xpassed
- Full suite: sin cambios en failures
