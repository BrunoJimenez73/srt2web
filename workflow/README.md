# Workflow de Desarrollo SRT2Web

## Cómo pedir una implementación

Solo dile al agente:

> `implementa F47` o `implementa la siguiente feature`

El agente ejecutará automáticamente el pipeline completo.

## Pipeline completo

```
1. python -m workflow.run --id F47
   → Selecciona feature, corre init.ps1, marca in_progress

2. El agente implementa el código
   (lee AGENTS.md, feature spec, progress files)

3. python -m workflow.run --validate-only
   → pytest + mypy + ruff + tsc + checkpoints

4. python -m workflow.session close --feature F47 --push
   → feature_list.json: done, actualiza progress/, commit + push
```

## Comandos rápidos

| Comando                                                 | Qué hace                                        |
| ------------------------------------------------------- | ----------------------------------------------- |
| `python -m workflow.run`                                | Inicia ciclo con próxima feature pendiente      |
| `python -m workflow.run --id F47`                       | Inicia ciclo con F47                            |
| `python -m workflow.run --validate-only`                | Solo validación (pytest, mypy, ruff, tsc, etc.) |
| `python -m workflow.run --status`                       | Estado actual del proyecto                      |
| `python -m workflow.validator --category python`        | Solo checks Python                              |
| `python -m workflow.validator --json`                   | Validación en formato JSON                      |
| `python -m workflow.session close --feature F47`        | Cierra sesión manualmente                       |
| `python -m workflow.session close --feature F47 --push` | Cierra + push                                   |

## Para el agente (IA)

Cuando te pidan implementar una feature:

1. Corre `python -m workflow.run --id F47` o simplemente te dicen "implementa F47"
2. Lee `AGENTS.md` para las reglas
3. Lee `progress/current.md` para el contexto de la sesión
4. Lee la spec en `feature_list.json` (problems_identified, acceptance, files_to_touch)
5. Implementa el código
6. Corre `python -m workflow.run --validate-only` para validar
7. Si todo pasa, corre `python -m workflow.session close --feature F47`
