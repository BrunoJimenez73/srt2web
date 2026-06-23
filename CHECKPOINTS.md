# CHECKPOINTS — Criterios de estado final

> Para decidir si una sesión está correctamente cerrada.
> Un revisor (humano o IA) recorre esta checklist.

## C1 — harness.db consistente

- [ ] `python -m harness health` → OK (sin issues)
- [ ] ≤ 1 feature en `in_progress`
- [ ] Toda feature `done` tiene tests asociados que pasan
- [ ] No hay features con status inválido
- [ ] Audit trail tiene cambios de la sesión actual (`python -m harness audit <id>`)

## C2 — init.ps1 pasa (checks obligatorios)

- [ ] Python 3.12 disponible
- [ ] Archivos base del arnés existen
- [ ] harness.db existe y es saludable
- [ ] `pytest tests/unit/ -q --tb=short` → 0 failures

## C3 — init.ps1 pasa (checks opcionales)

- [ ] `npx tsc --noEmit` (WARN ok)
- [ ] `npm test` (WARN ok)
- [ ] `npm run build:local` (WARN ok)

## C4 — Código limpio

- [ ] Sin `print()`, `console.log()`, TODOs sin contexto en código nuevo
- [ ] Sin archivos temporales ni `__pycache__` fuera de `.gitignore`
- [ ] Sin archivos sueltos en raíz (package.json, package-lock.json, skills-lock.json)

## C5 — Sesión cerrada correctamente

- [ ] `progress/current.md` refleja estado real
- [ ] `progress/history.md` tiene entrada de la última sesión
- [ ] `harness.db` actualizado — feature status refleja estado real
- [ ] `python -m harness session end` ejecutado con features trabajadas
- [ ] Sin cambios sin commit — todos los cambios pusheados
