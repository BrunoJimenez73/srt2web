# QA Loop — 3 agentes en ciclo

Loop continuo Tester → Implementer → Verifier hasta estabilidad.

## Arquitectura

```
┌──────────┐    fallos     ┌──────────────┐    feature     ┌──────────┐
│  Tester  │──────────────▶│ Implementer  │───────────────▶│ Verifier │
│ (QA)     │  reporte      │ (Dev)        │  in_progress   │ (Review) │
└──────────┘               └──────────────┘                └──────────┘
      ▲                                                    │
      │              FAIL                                   │ PASS
      └─────────────────────────────────────────────────────┘
                         done (cierra feature)
```

### Tester (QA Agent)

Ejecuta batería determinística y produce reporte:

- `python -m harness health` — integridad DB (1 feature in_progress max)
- `pytest tests/unit -q -m "not slow" -x` — unit tests
- `npm test -- --run` (frontend vitest)
- `mypy core/ server/ modules/ --strict`
- `tsc --noEmit` (frontend)
- `ruff check` + `eslint`
- `astro build` — verifica build
- `harness stats` — progreso

Severidad `alta` bloquea el loop; `media`/`baja` permiten continuar con warning.
Salida: `TesterReport` con `passed` bool + lista de `CheckResult`.

### Implementer (Dev Agent)

- Lee `python -m harness next` → siguiente `pending` por prioridad (Alta > Media > Baja)
- Marca `status in_progress`, abre `session start`
- Implementa fix (un archivo a la vez, type hints, cross-platform, sin prints)
- Verificación local rápida: `pytest -k <feature>`, `tsc`, `ruff`

Sigue `AGENTS.md §3 Reglas duras`: una feature a la vez, `init.ps1 -Quick` verde para done, documenta en harness session.

### Verifier (Review Agent)

Re-ejecuta checks críticos:

- `pytest unit quick`, `mypy --strict`, `tsc`, `harness health`
- Si PASS → `harness update <id> status done --agent <nombre>` + `session end`
- Si FAIL → reabre feature (`status blocked` + notas) y vuelve a Tester

## Uso

```bash
# Una iteración completa
python scripts/qa_loop.py --once

# Solo tester (para CI / diagnóstico)
python scripts/qa_loop.py --tester-only --json-report report.json

# Loop hasta 10 iteraciones o estabilidad
python scripts/qa_loop.py --max-iterations 10

# Forzar feature
python scripts/qa_loop.py --once --feature 194

# Tester full (sin --quick)
python scripts/qa_loop.py --tester-only --full
```

## Integración CI

Añadir a `.github/workflows/ci.yml`:

```yaml
- name: QA Loop — Tester
  run: python scripts/qa_loop.py --tester-only
```

## Backlog actual (7 features nuevas)

| ID   | Título                                     | Área        | Prioridad |
| ---- | ------------------------------------------ | ----------- | --------- |
| F194 | Fix polling desfasado y HLS buffer gigante | frontend    | Alta      |
| F195 | Alinear chunk_duration a GOP OBS (5s→10s)  | performance | Alta      |
| F196 | Hardening seguridad round 2                | security    | Alta      |
| F197 | Refactor UnifiedPipeline God Object        | core        | Alta      |
| F198 | WS reconexión infinita                     | frontend    | Alta      |
| F199 | Fix races FFmpeg/model_cache/piper         | core        | Alta      |
| F200 | Cerrar gaps testing                        | testing     | Media     |

Más ~140 hallazgos de menor severidad documentados en auditoría 2026-08-23 (ver `harness.db` y reporte de sesión).

## Criterio de estabilidad

Proyecto estable cuando:

- `harness health` → healthy
- `pending == 0`, `blocked == 0`, `in_progress <= 1`
- `pytest unit quick` + `vitest` + `mypy --strict` + `tsc` + `ruff` + `astro build` todos PASS
- `harness next` → "No pending features."

## Notas

- El loop respeta `CHECKPOINTS.md` antes de declarar done.
- Cada iteración debe ser atómica y dejar repo limpio (sin prints/TODOs).
- Para Mac, usar `init_Mac.sh --quick` en lugar de `init.ps1 -Quick`.
