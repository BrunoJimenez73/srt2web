# CHECKPOINTS — Criterios de estado final

> Para decidir si una sesión está correctamente cerrada.
> Un revisor (humano o IA) recorre esta checklist.

## C1 — feature_list.json consistente

- [x] ≤ 1 feature en `in_progress` (ninguna actualmente)
- [x] Toda feature `done` tiene tests asociados que pasan
- [x] No hay features con status inválido

## C2 — init.ps1 pasa (checks obligatorios)

- [x] Python 3.12 disponible
- [x] Archivos base del arnés existen
- [x] feature_list.json válido
- [x] `pytest tests/unit/ -q --tb=short` → 0 failures

## C3 — init.ps1 pasa (checks opcionales)

- [x] `npx tsc --noEmit` (WARN ok)
- [x] `npm test` (WARN ok)
- [x] `npm run build:local` (WARN ok)

## C4 — Código limpio

- [x] Sin `print()`, `console.log()`, TODOs sin contexto en código nuevo
- [x] Sin archivos temporales ni `__pycache__` fuera de `.gitignore`
- [x] Sin archivos sueltos en raíz (package.json, package-lock.json, skills-lock.json)

## C5 — Sesión cerrada correctamente

- [x] `progress/current.md` refleja estado real
- [x] `progress/history.md` tiene entrada de la última sesión
- [x] `feature_list.json` actualizado — todas las features implementadas están en `done`
- [x] Sin cambios sin commit — todos los cambios pusheados
