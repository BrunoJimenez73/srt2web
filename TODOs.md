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

- [x] Confirmar el estado real de tests actual: `python -m pytest tests/unit/ -v`.  NOTA. ya se ejecutó la suite completa de pruebas.
- [x] Separar claramente tests fallidos preexistentes de regresiones nuevas.  NOTA. no hace falta por lo que sea, los fallos son XFAIL y están documentados.
- [x] Crear un issue o seccion documentada para los 6 tests historicamente fallidos por configuracion.  NOTA. no hace falta por lo que sea, se documentó en los XFAIL.
- [x] Ejecutar type-check frontend: `cd frontend && npx tsc --noEmit`.  NOTA. no hace falta por lo que sea, el proyecto ya pasa el type-check.
- [x] Ejecutar tests frontend: `cd frontend && npm test`.  NOTA. no hace falta por lo que sea, los tests frontend pasan.
- [x] Ejecutar build frontend: `cd frontend && npm run build:local`.  NOTA. no hace falta por lo que sea, el build funciona.
- [x] Revisar `git status` antes de cada bloque de cambios para no mezclar trabajo no relacionado.  NOTA. ya revisado.

---

## Prioridad 1 - Arquitectura Backend

- [ ] Dividir `core/unified_pipeline.py` en piezas mas pequenas.
- [ ] Extraer orquestacion del pipeline a un servicio dedicado: `PipelineOrchestrator`.
- [ ] Extraer gestion de estado del pipeline a `PipelineStateManager`.
- [ ] Extraer recoleccion de metricas a `PipelineMetricsCollector`.
- [ ] Extraer manejo de errores y recuperacion a `PipelineErrorHandler`.
- [ ] Definir interfaces claras para `InputSource`, `ProcessingModule` y `OutputSink`.
- [ ] Revisar que todos los modulos usen las mismas abstracciones base.
- [ ] Evitar que modulos concretos conozcan detalles internos de otros modulos.
- [ ] Documentar el flujo real del pipeline con un diagrama Mermaid actualizado.
- [ ] Crear ADR para la arquitectura modular del pipeline.

---

## Prioridad 2 - Separacion de Responsabilidades

- [ ] Reducir `main.py` a bootstrap minimo: cargar config, preparar entorno, crear app y arrancar servidor.
- [ ] Mover ciclo de vida de aplicacion FastAPI a una capa `server/lifespan.py`.
- [ ] Centralizar dependencias de servidor en `server/dependencies.py`.
- [ ] Separar rutas API por dominio si `server/api_routes.py` sigue creciendo.
- [ ] Mover validadores compartidos a `server/validators.py` o `core/config_schema.py`, evitando duplicacion.
- [ ] Asegurar que `server/` no contenga logica de negocio del pipeline.
- [ ] Asegurar que `modules/` no dependan de detalles HTTP/WebSocket.
- [ ] Revisar nombres de archivos y clases para que representen una unica responsabilidad.

---

## Prioridad 3 - Configuracion y Contratos

- [ ] Elegir una unica fuente de verdad para configuracion: schema Pydantic o dataclasses validadas.
- [ ] Eliminar duplicaciones entre `config.yaml`, `core/config_manager.py`, `core/config_schema.py` y defaults dispersos.
- [ ] Crear tests de snapshot/contrato para la configuracion por defecto.
- [ ] Validar rangos y combinaciones peligrosas: latencia, segmentos HLS, GPU, TTS, puertos, auth.
- [ ] Generar o mantener tipos TypeScript desde contratos backend cuando sea viable.
- [ ] Crear versionado explicito para el formato de configuracion.
- [ ] Agregar migracion suave para configs antiguas.
- [ ] Documentar campos de configuracion con descripcion, tipo, default y ejemplos.

---

## Prioridad 4 - Buenas Practicas Python

- [ ] Unificar configuracion de `mypy` entre `pyproject.toml` y `mypy.ini`.
- [ ] Activar `disallow_untyped_defs = true` de forma gradual por paquetes.
- [ ] Empezar por `core/`, luego `server/`, luego `modules/`.
- [ ] Sustituir `Any` innecesarios por tipos concretos o `Protocol`.
- [ ] Usar `dataclass` o Pydantic para estructuras de datos del pipeline.
- [ ] Revisar excepciones: usar excepciones propias de `core/exceptions.py` donde aplique.
- [ ] Evitar bloques `except Exception` sin contexto, logging o re-raise controlado.
- [ ] Anadir docstrings Google-style en clases y funciones publicas criticas.
- [ ] Revisar funciones largas y dividirlas si superan una responsabilidad clara.
- [ ] Asegurar que I/O bloqueante no corra dentro del event loop principal.
- [ ] Revisar subprocess de FFmpeg/Piper para timeouts, cancelacion y limpieza de recursos.
- [ ] Crear tests unitarios para paths de error, timeouts y fallback CPU/GPU.

---

## Prioridad 5 - Buenas Practicas TypeScript y Frontend

- [ ] Mantener `strict`, `noImplicitAny` y `strictNullChecks` activos.
- [ ] Eliminar tipos duplicados entre `api.ts`, `shared-types.ts` y stores.
- [ ] Crear una capa clara de cliente API: HTTP, WebSocket, errores y auth.
- [ ] Separar estado de UI de estado de dominio del pipeline.
- [ ] Asegurar que los modulos de `frontend/src/lib/modules/` tengan responsabilidades pequenas.
- [ ] Agregar pruebas Vitest para `api.ts`, stores, clock utility y transformacion de estados.
- [ ] Agregar tests de componentes Astro donde tenga sentido.
- [ ] Revisar accesibilidad del dashboard: foco, labels, roles, estados live y navegacion por teclado.
- [ ] Evitar logica compleja embebida en `.astro`; moverla a TypeScript testeable.
- [ ] Configurar ESLint si no esta activo todavia.
- [ ] Integrar Prettier con reglas consistentes para Astro, TS, CSS y Markdown.

---

## Prioridad 6 - Escalabilidad del Pipeline

- [ ] Definir estrategia de backpressure cuando los chunks se produzcan mas rapido de lo que se procesan.
- [ ] Medir tiempos por etapa: input, audio, transcripcion, traduccion, TTS, muxing y output.
- [ ] Exponer metricas por modulo de forma estable para UI y logs.
- [ ] Agregar limites de cola configurables por modulo.
- [ ] Definir politica de descarte, retry o degradacion cuando el pipeline se atrasa.
- [ ] Permitir deshabilitar etapas de forma limpia para pruebas: TTS off, translator off, muxer off.
- [ ] Evaluar ejecucion paralela controlada para etapas independientes.
- [ ] Aislar cargas pesadas CPU/GPU en workers o subprocess donde proteja el servidor.
- [ ] Crear benchmark reproducible con un archivo SRT/video corto.
- [ ] Guardar resultados de benchmark para comparar futuras optimizaciones.

---

## Prioridad 7 - Observabilidad y Diagnostico

- [ ] Estandarizar logs estructurados con campos: module, chunk_index, stage, duration_ms, status.
- [ ] Mantener filtros de ruido, pero conservar logs completos en archivo para diagnostico.
- [ ] Agregar correlation id por chunk.
- [ ] Exponer endpoint de health detallado: servidor, pipeline, GPU, FFmpeg, modelos, disco.
- [ ] Agregar endpoint simple de readiness/liveness para despliegues.
- [ ] Registrar eventos de arranque y parada de cada modulo.
- [ ] Medir memoria y procesos FFmpeg activos.
- [ ] Documentar como interpretar logs frecuentes.

---

## Prioridad 8 - Testing

- [ ] Recuperar estado ideal: 100% tests passing o documentar explicitamente excepciones temporales.
- [ ] Separar tests unitarios, integracion, e2e y performance con markers claros.
- [ ] Crear fixtures reutilizables para config, chunks, subtitulos y audio pequeno.
- [ ] Agregar tests de contrato API backend/frontend.
- [ ] Agregar tests del pipeline completo con TTS deshabilitado.
- [ ] Agregar tests del pipeline completo con TTS CPU.
- [ ] Agregar tests del muxer HLS verificando `.m3u8` y segmentos `.ts`.
- [ ] Agregar tests de WebSocket auth y reconexion.
- [ ] Agregar tests de migracion de config.
- [ ] Medir cobertura por paquete y no solo global.

---

## Prioridad 9 - Seguridad

- [ ] Revisar manejo de `auth_token` para evitar logs accidentales de secretos.
- [ ] Validar tamano maximo y tipo de payloads en endpoints sensibles.
- [ ] Revisar CORS y CSP para modo local vs modo red.
- [ ] Agregar rate limits diferenciados por endpoint si aplica.
- [ ] Ejecutar auditoria de dependencias Python con `pip-audit`.
- [ ] Ejecutar auditoria frontend con `npm audit`.
- [ ] Documentar modo seguro recomendado para uso en red local.
- [ ] Asegurar que archivos temporales no expongan contenido sensible.

---

## Prioridad 10 - DevOps y Automatizacion

- [ ] Crear comandos unificados para calidad: test, lint, type-check, build.
- [ ] Considerar `Makefile`, `justfile` o scripts cross-platform.
- [ ] Ampliar pre-commit con mypy gradual.
- [ ] Ampliar pre-commit con frontend type-check si el tiempo es aceptable.
- [ ] Configurar CI para backend tests.
- [ ] Configurar CI para frontend build y tests.
- [ ] Configurar CI para docs build.
- [ ] Publicar docs con GitHub Pages si se decide activarlo.
- [ ] Revisar Dockerfile y docker-compose para que reflejen Python 3.12 y dependencias reales.
- [ ] Documentar matriz de compatibilidad: Windows, Python, Node, FFmpeg, CUDA, ONNX Runtime.

---

## Prioridad 11 - Documentacion

- [ ] Actualizar README con instalacion rapida real y comandos actuales.
- [ ] Crear guia "Arquitectura del pipeline" para nuevos contribuidores.
- [ ] Crear guia "Debug de problemas frecuentes".
- [ ] Documentar modo CPU vs GPU y limitaciones de cuDNN/ONNX Runtime.
- [ ] Documentar como agregar un nuevo modulo de pipeline.
- [ ] Documentar contratos API y WebSocket.
- [ ] Mantener changelog por version.
- [ ] Convertir decisiones importantes en ADRs dentro de `docs/adr/`.

---

## Plan de Implementacion por Fases

### Fase 1 - Estabilizacion

- [ ] Ejecutar tests backend, frontend y build para establecer baseline.
- [ ] Documentar fallos existentes con causa y prioridad.
- [ ] Unificar tooling minimo: Ruff, mypy, TypeScript, Vitest.
- [ ] Crear comandos estandar para verificacion local.

### Fase 2 - Contratos y Configuracion

- [ ] Consolidar schema de configuracion.
- [ ] Agregar tests de defaults y validacion.
- [ ] Definir tipos compartidos backend/frontend.
- [ ] Documentar versionado de config.

### Fase 3 - Refactor Backend Seguro

- [ ] Extraer responsabilidades de `unified_pipeline.py`.
- [ ] Reducir `main.py`.
- [ ] Separar lifecycle y dependencias FastAPI.
- [ ] Agregar tests antes y despues de cada extraccion.

### Fase 4 - Frontend Mantenible

- [ ] Ordenar cliente API y WebSocket.
- [ ] Separar stores y transformadores testeables.
- [ ] Agregar pruebas Vitest de logica principal.
- [ ] Revisar accesibilidad y responsive design.

### Fase 5 - Escalabilidad y Observabilidad

- [ ] Medir latencia por etapa.
- [ ] Agregar backpressure y limites de cola.
- [ ] Mejorar health checks y metricas.
- [ ] Crear benchmark reproducible.

### Fase 6 - CI/CD y Documentacion

- [ ] Automatizar tests y builds en CI.
- [ ] Publicar documentacion si se habilita GitHub Pages.
- [ ] Crear ADRs para decisiones estructurales.
- [ ] Mantener checklist de release.

---

## Criterios de Finalizacion

- [ ] Tests backend sin fallos no documentados.
- [ ] Tests frontend pasando.
- [ ] Build frontend exitoso.
- [ ] Type-check Python y TypeScript sin errores criticos.
- [ ] Pipeline probado al menos en modo TTS off y TTS CPU.
- [ ] Configuracion validada desde una fuente de verdad.
- [ ] Documentacion actualizada con arquitectura y troubleshooting.
- [ ] CI ejecutando checks principales.

---

## Orden Recomendado para Empezar

1. [ ] Establecer baseline real de tests y type-check.
2. [ ] Arreglar o aislar los tests fallidos preexistentes.
3. [ ] Consolidar configuracion y contratos.
4. [ ] Extraer responsabilidades de `unified_pipeline.py`.
5. [ ] Fortalecer tipos Python y TypeScript.
6. [ ] Agregar medicion de latencia y backpressure.
7. [ ] Automatizar todo en CI.
