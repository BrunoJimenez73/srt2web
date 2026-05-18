# Sesión activa — 2026-05-18

**Estado:** F77 completada — TypeScript/ESLint strict frontend
**Iniciada:** 2026-05-18

## Features completadas

### F74: Repo Cleanup Phase 1

- Eliminados `files/` (38 archivos), `desktop/` (13 entradas), 4 archivos huérfanos en raíz
- Version unification: `server/app.py` usa `importlib.metadata.version()`
- 29 bloques `except Exception:` reemplazados con logging
- 5 tests pre-existentes rotos fixeados
- `init.ps1 -Quick`: ✅ Verde

### F75: mypy gradual en modules/

- `modules/` ya estaba type-clean bajo `strict = true`
- `mypy core/ server/ modules/ --strict`: 0 errores (87 archivos)

### F76: mypy strict en cli/

- `cli/` eliminado de `exclude` en pyproject.toml
- 211 → 0 errores mypy en `cli/` (34 archivos)
- Fixes: imports asyncio/json al top, `-> None` en click commands, `cast()` en http_client, `Screen[Any]`/`Task[Any]` tipados
- `mypy core/ server/ modules/ cli/ --strict`: 0 errores (121 archivos)

### F77: TypeScript/ESLint strict frontend

- `@typescript-eslint/no-explicit-any`: warn → error
- Eliminado `.eslintrc.json` legacy (flat config eslint.config.js es fuente única)
- Eliminado `ignoreDeprecations: "5.0"` de tsconfig.json — tsc sin warnings
- Reemplazado `console.log` en `api.ts:404` por comentario
- Fixeados parsing errors en InputCard.astro (comillas anidadas) y TtsCard.astro (extra `</div>`)
- Fixeados `any` en `outputs.ts:71` (`Record<string, unknown>`) y `astro.d.ts:5` (eslint-disable)
- `npm run lint`: 0 errores, 22 warnings (todo preexistente)
- `npx tsc --noEmit`: limpio
- `init.ps1 -Quick`: ✅ Verde

### F78: Refactor unified_pipeline — circuit breaker y metrics

- Extraído `CircuitBreaker`, `CircuitState`, `RetryStrategy`, `is_recoverable_error` a `core/circuit_breaker.py`
- Extraído `PipelineMetrics` a `core/pipeline_metrics.py`
- `core/unified_pipeline.py` importa y delega; API pública sin breaking changes
- Fix ruff: UP007 (`X | Y`), SIM102, SIM114, SIM110, E402
- Tests: `test_stability.py` y `test_pipeline_metrics.py` pasan
- `init.ps1 -Quick`: ✅ Verde

### F79: Extraer piper worker a módulo separado

- `modules/piper_worker.py` (NUEVO): worker persistente como módulo real (antes string inline de 178 líneas)
- `modules/piper_loader_script.py` (NUEVO): one-shot loader como módulo real (antes string inline de 73 líneas)
- `modules/piper_loader.py`: 805 → 458 líneas (-43%), solo manager + IPC
- Fix: duplicado "ping" handler en worker original eliminado
- Fix: `logger` no definido en worker original reemplazado por `_log()` a stderr
- `mypy modules/`: 0 errores (`# mypy: ignore-errors` en scripts de subprocess)
- `init.ps1 -Quick`: ✅ Verde

---

## Features completadas

### F79: Extraer piper worker a módulo separado

- Eliminado `PERSISTENT_WORKER_SCRIPT` de `piper_loader.py` (ya no necesita constante que lee el archivo entero en import)
- `piper_loader.py` reducido de 545 → 360 líneas (<500 ✅)
- `piper_worker.py`: eliminado `# mypy: ignore-errors`, añadidos type hints completos, import `Any` desde typing
- `piper_loader_script.py`: eliminado `# mypy: ignore-errors`, simplificada lógica condicional
- Tests actualizados: `test_piper_heartbeat.py` lee de `piper_worker.py` directamente; `test_latest_features.py` apunta a `piper_worker.py`
- `mypy modules/piper_loader.py modules/piper_worker.py modules/piper_loader_script.py --strict`: 0 errores
- 37 tests de piper/TTS pasan sin regresiones

### F80: Modularizar pipeline-control e i18n JSON

- `pipeline-control.ts` ya era barrel re-export (refactor pre-existente con ws-manager, polling, config-client, presets-client, config-collector)
- Extraídas traducciones inline de `i18n.ts` (577 líneas) a `frontend/src/lib/locales/en.json` (235 keys) y `es.json` (235 keys)
- `i18n.ts` refactorizado para importar desde JSON en lugar de tener diccionarios inline (80 líneas)
- `npx tsc --noEmit`: 0 errores
- 99 frontend tests pasan (18 failures pre-existentes en effects.test.ts no relacionados)

## Backlog pendiente

_(no hay features pendientes)_
