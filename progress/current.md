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

---

## Backlog pendiente

| ID  | Plan  | Título                                   | Deps |
| --- | ----- | ---------------------------------------- | ---- |
| F78 | B3    | Refactor `unified_pipeline`              | F75  |
| F79 | B4    | Extraer `piper_worker`                   | F75  |
| F80 | B5,B6 | Modularizar pipeline-control + i18n JSON | F77  |
