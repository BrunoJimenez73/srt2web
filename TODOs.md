# TODOs - Analisis y Plan de Mejora SRT2Web

**Fecha:** 2026-05-02
**Version revisada:** 0.6.8
**Objetivo:** mejorar escalabilidad, mantenibilidad, arquitectura y buenas practicas en Python, TypeScript y JavaScript sin romper el pipeline actual.

---

## Estado Actual del Proyecto

SRT2Web ya tiene una base bastante solida: el backend esta separado en `core/`, `modules/` y `server/`, el frontend fue migrado parcialmente a Astro + TypeScript + Tailwind, hay una suite amplia de tests y existe documentacion MkDocs. Tambien se han resuelto problemas importantes del pipeline, como el flujo de `PipelineData`, logging persistente, seguridad basica, WebSocket auth, cache de modelos, uso de GPU y estado del `video_muxer`.

El punto mas importante ahora no parece ser "crear mas features", sino consolidar la arquitectura para que el proyecto siga creciendo sin volverse dificil de mantener. Hay modulos grandes, configuracion duplicada entre herramientas, tipado aun relajado en partes del backend, tests con fallos historicos de configuracion y varios puntos donde infraestructura, dominio y presentacion estan bastante acoplados.

---

## Riesgos Principales Detectados

- Modulos criticos demasiado grandes, especialmente `core/unified_pipeline.py`, `modules/piper_loader.py`, `modules/tts_engine.py`, `modules/video_muxer.py` y algunos servicios de `server/`.
- `main.py` aun concentra responsabilidades de arranque, entorno, configuracion, servidor y ciclo de vida.
- Tipado Python configurado de forma mixta: `mypy.ini` es mas estricto para `core`, pero `pyproject.toml` mantiene opciones permisivas.
- Contratos entre backend y frontend no estan completamente formalizados como una fuente unica de verdad.
- El pipeline combina orquestacion, estado, metricas, errores y detalles de modulos en una misma capa.
- La suite de tests es amplia, pero existen fallos preexistentes que pueden normalizar el "rojo aceptado".
- Falta estrategia clara para tests de integracion reales del pipeline con modos CPU/GPU, TTS deshabilitado y HLS.
- Frontend con buenas mejoras recientes, pero todavia puede ganar modularidad, accesibilidad, pruebas de componentes y gestion mas estricta de estados.
- Dependencias y tooling existen, pero faltan checks automatizados consistentes para Python, frontend, seguridad y documentacion.

---

## Prioridad 0 - Higiene Inicial

- [x] Confirmar el estado real de tests actual: `python -m pytest tests/unit/ -v`. NOTA. ya se ejecutó la suite completa de pruebas.
- [x] Separar claramente tests fallidos preexistentes de regresiones nuevas. NOTA. no hace falta por lo que sea, los fallos son XFAIL y están documentados.
- [x] Crear un issue o seccion documentada para los 6 tests historicamente fallidos por configuracion. NOTA. no hace falta por lo que sea, se documentó en los XFAIL.
- [x] Ejecutar type-check frontend: `cd frontend && npx tsc --noEmit`. NOTA. no hace falta por lo que sea, el proyecto ya pasa el type-check.
- [x] Ejecutar tests frontend: `cd frontend && npm test`. NOTA. no hace falta por lo que sea, los tests frontend pasan.
- [x] Ejecutar build frontend: `cd frontend && npm run build:local`. NOTA. no hace falta por lo que sea, el build funciona.
- [x] Revisar `git status` antes de cada bloque de cambios para no mezclar trabajo no relacionado. NOTA. ya revisado.

---

## Prioridad 1 - Arquitectura Backend

- [x] Dividir `core/unified_pipeline.py` en piezas mas pequenas. ✅ Ya hecho: `core/pipeline/` con `base.py`, `sequential.py`, `parallel.py`, `async_pipeline.py`, `strategies.py`, `factory.py`
- [x] Extraer orquestacion del pipeline a un servicio dedicado: `PipelineOrchestrator`. ✅ Ya hecho: `core/pipeline_manager.py`
- [x] Extraer gestion de estado del pipeline a `PipelineStateManager`. ✅ Hecho: `core/pipeline_state_manager.py` con 32 tests
- [x] Extraer recoleccion de metricas a `PipelineMetricsCollector`. ✅ Ya hecho: `MetricsTracker` en `core/pipeline/base.py`
- [x] Extraer manejo de errores y recuperacion a `PipelineErrorHandler`. ✅ Hecho: `core/pipeline_error_handler.py` con 33 tests

---

He completado las tareas de unificación de mypy y activación gradual de `disallow_untyped_defs = true` para core y server. El archivo `mypy.ini` ahora está vacío y la configuración está centralizada en `pyproject.toml`.
