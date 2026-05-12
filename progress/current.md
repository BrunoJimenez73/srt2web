# Sesión activa — 2026-05-12

**Estado:** F17 DONE
**Iniciada:** 2026-05-12

## Siguiente feature: F22 (cleanup_dead_code) o F24 (mypy_strict_mode)

### Resumen de la sesión

- **Feature 17 (piper_heartbeat_and_graceful_degrade)**: COMPLETADA.
  - Piper heartbeat thread cada 30s con restart en 5s timeout
  - `is_critical` property en BaseModule (default True)
  - `_degraded_count` y `_max_degraded_allowed` (3) tracking
  - Módulos no críticos fallan → DEGRADED + pipeline continúa
  - ModuleState.DEGRADED en backend y frontend
  - Frontend: ModuleCard status-dot amber + pulse-degraded animation
  - Test file `tests/unit/test_piper_heartbeat.py`: 14/14 passing
- **Fixes**:
  - `unified_pipeline.py:529`: indentación extra del `try:` — corregida
  - `module_base.py`: agregado `is_critical` property, init `_degraded_count`/`_max_degraded_allowed`
- **Suite completa (no slow)**: 971 passed, 3 skipped, 2 xfailed, 1 xpassed
- **init.ps1 -Quick**: OK (verde)
- **Errores remanentes**: 2 integration tests (pre-existing, `PipelineOrchestrator` import fail — unrelated)
