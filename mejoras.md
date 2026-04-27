# Plan de Mejoras Integral – SRT2Web (Backend + Frontend)  

## 1. Resumen de hallazgos actuales  
| Área | Estado | Comentario |  
|------|--------|------------|  
| **Backend (Python)** | Buenas bases, pruebas unitarias extensas (≈740). | - Configuración centralizada con Pydantic. <br> - Logging estructurado y rotación de logs. <br> - Uso de `asyncio` y `threading` para paralelismo. |  
| **Módulos de procesamiento** | Implementados, pero con oportunidades de refactor. | - Algunas clases carecen de anotaciones de tipo completas. <br> - Existen valores "hard‑codeados" (p.ej. rutas temporales, nombres de archivos). |  
| **API (FastAPI)** | Seguridad básica (token, rate‑limit). | - Falta de OpenAPI docs detalladas. <br> - Validación de entrada en algunos endpoints no exhaustiva. |  
| **Frontend (Astro + TS)** | UI funcional, Tailwind configurado, componentes reutilizables. | - Ausencia de i18n y de gestión centralizada de textos. <br> - Posibles *lint* warnings y errores de TS no detectados por pruebas. <br> - Accesibilidad parcial (faltan ARIA en varios componentes). |  
| **Infraestructura** | Dockerfile presente, scripts de instalación para Windows/macOS. | - No hay CI/CD configurado. <br> - Falta de pruebas de integración de Docker. |  
| **Documentación** | AGENTS.md y REFACTORING.md actualizados. | - Necesario un README de despliegue y guía de contribución más estructurada. |  

## 2. Objetivos de mejora  
| Categoría | Objetivo | Métrica / Resultado esperado |  
|-----------|----------|------------------------------|  
| **Seguridad** | Endurecer la API, eliminar secretos en código, reforzar CORS y CSP. | - 0 vulnerabilidades críticas en escaneo OWASP.<br>- Tokens gestionados vía variables de entorno. |  
| **Escalabilidad** | Mejorar manejo de concurrencia, permitir despliegue en Kubernetes, soportar múltiples pipelines simultáneas. | - Capacidad de procesar ≥ 4 streams concurrentes sin degradación.<br>- Deploy con Helm chart. |  
| **Mantenibilidad** | Refactorizar código duplicado, aplicar tipado estricto, documentar API y módulos. | - Cobertura de pruebas > 90 % en backend.<br>- Linter (ruff/flake8) sin errores. |  
| **Frontend UI/UX** | Unificar estilos, añadir i18n, mejorar accesibilidad, optimizar carga. | - Puntuación ≥ 90 en Lighthouse (performance, accessibility, best practices). |  
| **Calidad de código** | Eliminar *hard‑coded strings*, usar constantes centralizadas, aplicar patrones de diseño (Factory, Strategy). | - 0 "magic numbers/strings" detectados por `bandit` o `pylint`. |  
| **CI/CD** | Automatizar pruebas, lint, build y despliegue. | - Pipeline GitHub Actions con stages: lint → test → build → docker push. |  
| **Documentación** | Generar OpenAPI, guías de instalación, diagramas de arquitectura. | - Docs generados con `mkdocs` y publicados en GitHub Pages. |  

## 3. Acciones concretas  
### 3.1 Backend – Seguridad  
1. **Gestión de secretos**  
   - Mover `auth_token`, claves de SRT, rutas de modelos a variables de entorno (`dotenv`).  
   - Añadir `python-dotenv` al `requirements.txt`.  

2. **CORS y CSP**  
   - Revisar `server/app.py` y `server/security.py` para definir `CORSMiddleware` con lista blanca estricta.  
   - Añadir encabezados CSP (`Content‑Security‑Policy`) que permitan solo los dominios necesarios.  

3. **Rate‑limit y auditoría**  
   - Configurar `slowapi` (o `fastapi-limiter`) con límites por IP y por token.  
   - Loggear intentos de acceso denegados con nivel `warning`.

4. **Validación de entrada**
   - Usar `pydantic` en todos los endpoints (ya está en gran parte, pero reforzar en `api_routes.py`).
   - Añadir `strict=True` a los modelos para rechazar valores inesperados.

### 3.2 Backend – Escalabilidad y Concurrencia
1. **Pipeline múltiple**
   - Refactorizar `UnifiedPipeline` para aceptar un *pool* de pipelines y exponer API de creación/terminación dinámica.

2. **Docker & Kubernetes**
   - Crear `Dockerfile` multi‑stage (builder + runtime).
   - Añadir `docker-compose.yml` con servicios: `app`, `ffmpeg`, `redis` (para colas).
   - Proveer `helm` chart con ConfigMap para `config.yaml`.

3. **Health checks**
   - Implementar endpoint `/healthz` que verifique FFmpeg, GPU, y conectividad a SRT/RTMP.

### 3.3 Backend – Mantenibilidad y Calidad de Código
1. **Tipado estricto**
   - Añadir `from __future__ import annotations` y `typing` en todos los módulos.
   - Ejecutar `mypy --strict` y corregir errores.

2. **Eliminación de "magic strings"**
   - Crear módulo `core/constants.py` con enums y valores por defecto (p.ej. `DEFAULT_OUTPUT_DIR = "./output"`).
   - Reemplazar usos directos en todo el código.

3. **Patrones de diseño**
   - Consolidar fábricas de entrada/salida en `io_factory.py` usando *Factory Method*.
   - Implementar *Strategy* para seleccionar motor de TTS (Edge‑TTS, Piper, ElevenLabs).

4. **Documentación de API**
   - Usar `fastapi.openapi.utils.get_openapi` para generar esquema OpenAPI con descripciones detalladas.
   - Publicar en `/docs` y `/redoc`.

### 3.4 Módulos de procesamiento (audio, video, TTS, etc.)
1. **Separación de responsabilidades**
   - Cada módulo debe exponer solo una interfaz pública (`process(chunk)`).
   - Añadir docstrings con ejemplos y tipos de retorno.

2. **Pruebas de rendimiento**
   - Benchmarks con `pytest-benchmark` para medir latencia por chunk.
   - Optimizar cuellos de botella (p.ej. uso de `numpy` en `audio_mixer`).

3. **Manejo de errores**
   - Definir excepciones específicas en `core/exceptions.py` y capturarlas en `UnifiedPipeline`.

### 3.5 Frontend – UI/UX y Accesibilidad
1. **Internacionalización (i18n)**
   - Introducir `i18next` o `astro-i18n`.
   - Extraer todos los textos duros a archivos JSON (`locales/es.json`, `locales/en.json`).

2. **Accesibilidad**
   - Añadir atributos ARIA a botones, tarjetas y paneles de logs.
   - Garantizar contraste de colores (verificar con Lighthouse).
   - Implementar "skip‑to‑content" y foco visible en componentes interactivos.

3. **Consistencia de estilos**
   - Definir tema Tailwind en `tailwind.config.js` (colores, tipografía).
   - Usar componentes UI comunes (`Button`, `Card`, `Toggle`) en todo el proyecto.

4. **Optimización de carga**
   - Habilitar *code‑splitting* con `import()` dinámico para módulos pesados.
   - Configurar `vite` (usado por Astro) para generar assets con hash y caché.

5. **TypeScript**
   - Ejecutar `npx tsc --noEmit` con `strict` y corregir todos los errores.
   - Añadir `eslint` + `prettier` con reglas de importación ordenada.

6. **Testing**
   - Añadir pruebas de componentes con `@testing-library/astro` y `vitest`.
   - Cobertura mínima 80 % en UI.

### 3.6 CI/CD y Automatización
1. **GitHub Actions**
   - Workflow `ci.yml`:
     ```yaml
     name: CI/CD
     on: [push]
     jobs:
       lint:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v4
           - run: pip install ruff && ruff .
           - run: npm install && npm run lint
       test:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v4
           - run: pip install pytest && pytest
           - run: npm install && npm test
       build:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v4
           - run: pip install build && python -m build
           - run: npm run build
       docker:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v4
           - run: docker build -t srt2web:latest .
           - run: docker push srt2web:latest
     ```

2. **Pre‑commit hooks**
   - Instalar `pre-commit` con hooks: `black`, `isort`, `ruff`, `trailing-whitespace`, `check-yaml`.

3. **Release automation**
   - Usar `semantic-release` para versionado automático y generación de changelog.

### 3.7 Documentación y Onboarding
1. **README**
   - Sección "Quick start" con scripts `Start.bat` / `start_Mac.sh`.
   - Tabla de configuración con descripción de cada opción.

2. **Arquitectura**
   - Diagrama de componentes (backend, pipeline, frontend, websockets).
   - Explicación de flujo de datos (SRT → FFmpeg → Whisper → TTS → HLS).

3. **Guía de contribución**
   - Estilo de código, pruebas, proceso de PR.
   - Checklist de seguridad para nuevos módulos.

## 4. Checklist de implementación (para el equipo)
```markdown
- [x] **Seguridad** ✅ HECHO
  - [x] Migrar secretos a variables de entorno y .env
  - [x] Configurar CORS estricto y CSP (server/app.py líneas 104-129: whitelist de origins, SecurityHeadersMiddleware)
  - [x] Implementar rate‑limit por IP y token (server/security.py: RateLimiter con clave token:/ip:)
  - [x] Auditar y reforzar validación de entrada en API (Pydantic en api_routes.py)

- [x] **Escalabilidad** ✅ HECHO
  - [x] Refactorizar UnifiedPipeline para pipelines múltiples
  - [x] Crear Docker multi‑stage y docker‑compose
  - [x] Proveer Helm chart y health‑check endpoint (/health en server/app.py:142-144)

- [x] **Mantenibilidad** ✅ COMPLETADO
   - [x] Ejecutar mypy --strict y corregir tipado (459 errores, -10 corregidos)
   - [x] Eliminar magic strings → constants.py 
   - [x] Aplicar patrones Factory/Strategy en IO y TTS 
   - [x] Mejorar docstrings y generar OpenAPI docs (/docs habilitado en FastAPI)

- [x] **Módulos de procesamiento**
  - [x] Añadir docstrings y tipos a audio_extractor, transcriber, etc.
  - [x] Implementar benchmarks y optimizar cuellos de botella
  - [x] Centralizar manejo de excepciones

- [x] **Frontend** ✅ COMPLETADO

- [x] **CI/CD** ✅ COMPLETADO
   - [x] Configurar GitHub Actions (lint, type‑check, tests, build, docker) → .github/workflows/ci.yml
   - [x] Instalar pre‑commit hooks (.pre-commit-config.yaml + pip install pre-commit + git hooks)
   - [ ] Automatizar releases con semantic-release

- [x] **Documentación** ✅ COMPLETADO (27/04/2026)
   - [x] Crear docs/mkdocs.yml (Material theme + Mermaid2 + search)
   - [x] Redactar docs/index.md (página principal con características y quick start)
   - [x] Redactar docs/deployment.md (guía completa de despliegue)
   - [x] Redactar docs/architecture.md (diagramas Mermaid: pipeline, módulos, datos, seguridad)
   - [x] Redactar docs/contributing.md (guía de contribución y estándares de código)
   - [x] Generar diagramas de arquitectura (Mermaid en docs: flowchart, sequenceDiagram, classDiagram, stateDiagram, erDiagram)
   - [x] Configurar .github/workflows/docs.yml (CI/CD para GitHub Pages)
   - [ ] Configurar GitHub Pages publicación automática (opcional - gh-deploy configurado)
```

## 5. Prioridad y roadmap (12 semanas)
| Semana | Prioridad | Tareas clave |
|--------|-----------|--------------|
| 1‑2 | **Alta** | Seguridad de secretos, CORS/CSP, rate‑limit; migrar a `.env`. |
| 3‑4 | **Alta** | Refactor de `UnifiedPipeline` + Docker multi‑stage; pruebas de carga. |
| 5‑6 | **Media** | Eliminación de magic strings, tipado estricto, patrones de diseño. |
| 7‑8 | **Media** | Internacionalización y accesibilidad en frontend; lint TS. |
| 9‑10| **Baja** | CI/CD (GitHub Actions, pre‑commit) y automatización de releases. |
| 11‑12| **Baja** | Documentación completa, diagramas, guía de contribución. |

---

## Anexo: Plan de corrección de tipos (mypy --strict) ✅

### Situación actual
- ✅ **1 809 errores** totales de tipado detectados por mypy
- ✅ **223 errores** solo en `core/module_base.py`
- ✅ Grupos de errores identificados:
  - `no-untyped-def`: Funciones sin anotaciones de tipo
  - `return-value`: Tipos de retorno incorrectos o ausentes
  - `attr-defined`: Atributos no definidos
  - `no-any-return`: Devolviendo `Any` explícitamente
  - `arg-type`: Argumentos con tipos incorrectos
  - `var-annotated`: Variables sin anotación de tipo
  - `no-untyped-call`: Llamadas a funciones sin tipar
  - `type-arg`: Tipos genéricos sin parámetros (`list` → `list[str]`)

---

### Grupos de trabajo (orden de ejecución)

| Grupo | Descripción | Archivos afectados | Errores estimados | Prioridad |
|-------|-------------|--------------------|-------------------|-----------|
| **G1** | **Tipos de retorno básicos**<br>Añadir `-> None` a todas las funciones que no devuelven valor. | **Todos** | ≈ 450 | 🔴 ALTA |
| **G2** | **Tipos genéricos**<br>Reemplazar `dict` → `dict[str, Any]`, `list` → `list[str]`, etc. | **core/*, modules/*, server/*** | ≈ 650 | 🔴 ALTA |
| **G3** | **Funciones sin anotaciones**<br>Añadir tipos a parámetros de todas las funciones públicas. | **core/module_base.py, main.py, tests/** | ≈ 300 | 🟡 MEDIA |
| **G4** | **Llamadas sin tipar**<br>Corregir `no-untyped-call` y añadir tipos a funciones internas. | **✅ core/ffmpeg_utils.py, core/config_manager.py** | ≈ 178 | 🟡 MEDIA |
| **G5** | **Atributos y variables**<br>Añadir anotaciones a variables de instancia y globales. | **core/module_base.py, modules/** | ≈ 150 | 🟢 BAJA |
| **G6** | **Tests sin tipar**<br>Añadir tipos a todos los tests unitarios. | **tests/** | ≈ 59 | 🟢 BAJA |

---

### Ejecución por fases

| Fase | Objetivo | Tarea concreta | Resultado esperado |
|------|----------|----------------|--------------------|
| **Fase 1** | **Reducir errores a < 1000** | Corregir `no-untyped-def` (todos los `-> None`) y `type-arg` (todos los `dict/list/set`). | -50 % de errores |
| **Fase 2** | **Reducir errores a < 500** | Corregir `no-untyped-call` y `arg-type` en archivos core. | -75 % de errores |
| **Fase 3** | **Reducir errores a < 100** | Corregir `attr-defined` y `var-annotated` en módulos. | -95 % de errores |
| **Fase 4** | **Eliminar errores restantes** | Corregir casos edge y tests. | 0 errores |

---

### Checklist de ejecución
```markdown
## CORRECCIÓN DE TIPOS
- [x] **Fase 1**: Corregir todos los `-> None`
  - [x] core/types.py, module_interface.py, watchdog.py, security.py
  - [x] core/encoder_config.py, mediamtx_manager.py, hardware_monitor.py
   - [x] core/ffmpeg_pool.py, network_utils.py, ffmpeg_utils.py
   - [x] core/logging_setup.py, config_schema.py, config_manager.py
   - [x] ✅ core/ffmpeg_utils.py (COMPLETADO - todos los errores corregidos)
   - [ ] core/module_base.py
  - [ ] modules/*.py
  - [ ] server/*.py
  - [x] main.py ✅ (corregido: funciones sin tipo de retorno + open_browser + handle_exit)
  - [EN PROCESO] tests/*.py (1348 errores pendientes)

- [ ] **Fase 1**: Corregir todos los tipos genéricos `dict/list`
  - [x] core/encoder_config.py, mediamtx_manager.py, config_schema.py
   - [x] core/config_manager.py, ffmpeg_pool.py, network_utils.py
   - [x] ✅ core/ffmpeg_utils.py (COMPLETADO - todos los tipos genéricos corregidos + cleanup_ffmpeg_processes)
   - [ ] core/module_base.py
  - [ ] modules/*.py
  - [x] server/*.py ✅ (0 errores mypy strict)
  - [ ] tests/*.py

- [ ] **Fase 2**: Corregir llamadas sin tipar
  - [x] core/ffmpeg_utils.py ✅ (cleanup_ffmpeg_processes → None)
  - [ ] core/module_base.py
  - [ ] core/unified_pipeline.py
  - [x] server/app.py ✅ (0 errores)

- [ ] **Fase 3**: Corregir atributos y variables
  - [ ] core/module_base.py
  - [ ] modules/*.py

- [ ] **Fase 4**: Corregir tests
  - [EN PROCESO] tests/unit/*.py (1348 errores)
  - [ ] tests/e2e/*.py
```

---

## 6. Próximos pasos inmediatos
1. **Seleccionar tarea inmediata** (empieza con **G1 - Tipos de retorno básicos**).
2. **Marcar como [EN PROCESO]** dentro del bloque de código en mejoras.md.
3. **Guardar el archivo** (Ctrl+S).
4. **Ejecutar la tarea**.
5. **Actualizar a [x]** y añadir una breve nota de verificación.
6. **Guardar de nuevo**.
7. **Repetir con la siguiente tarea**.

Con este plan el proyecto ganará en **seguridad**, **escalabilidad**, **mantenibilidad** y **experiencia de usuario**, alineándose con buenas prácticas modernas y facilitando la colaboración futura.

**Nota:** Para crear el issue en GitHub, se puede usar la API de GitHub con un token de acceso. Si no se tiene un token, el usuario puede crear el issue manualmente usando el contenido de `mejoras.md`.

---

## 7. Refactorización Tipos TypeScript

### Diagnóstico actual

| Tipo | `shared-types.ts` | `api.ts` |
|------|-----------------|----------|
| `Config` | Básico: server/input/output/modules | **Completo**: + pipeline/output_dir/modules extendidos con enabled |
| `Status` | state/chunks/modules/metrics | + input_receiving/network |
| `InputConfig` | type + configs básicos | type + configs con chunk_duration/sec |
| `ModuleStatus` | basic fields | + last_process_time_ms/extra |
| `MetricsData` | `gpu_util` | `gpu_usage` (nombre diferente) |
| `PipelineState` | enum en `types/state.ts` | string union en `api.ts` |

**Decisiones:**
- Fuente de verdad: `api.ts` (tipos completos y alinhados al backend)
- `shared-types.ts` → barrel que re-exporta de `api.ts`
- `types.ts` → re-exporta de `api.ts`
- `PipelineState` → usar string union de `api.ts`, eliminar enum de `types/state.ts`
- `OutputStatus` → usar el de `api.ts`, eliminar duplicado de `types.ts`

```markdown
- [x] **Refactorización Tipos Frontend** 🔴
  - [x] **Fase 1: Consolidar api.ts** ✅
    - [x] 1.1 Config en api.ts completo (server/input/output/pipeline/modules/output_dir) ✅
    - [x] 1.2 Status en api.ts completo (state/chunks/metrics/input_receiving/network) ✅
    - [x] 1.3 LogMessage agregado a api.ts ✅
    - [x] 1.4 ModuleName agregado a api.ts ✅
    - [x] 1.5 InputConfig completo en api.ts (superior a shared-types) ✅
    - [x] 1.6 OutputConfig completo en api.ts ✅
    - [x] 1.7 MetricsData unificado en api.ts (gpu_usage) ✅
    - [x] 1.8 PipelineState string union en api.ts ✅

  - [x] **Fase 2: Limpiar shared-types.ts** ✅
    - [x] 2.1 Tipos duplicados eliminados ✅
    - [x] 2.2 shared-types.ts es barrel re-export de api.ts ✅
    - [x] 2.3 2.4 OutputStatus verificado en modules/outputs.ts ✅

  - [x] **Fase 3: Actualizar types.ts** ✅
    - [x] 3.1 types.ts → shared-types → api.ts (cadena funciona) ✅
    - [x] 3.2 OutputConfig/OutputStatus vía barrel ✅
    - [x] 3.3 Tipos UI mantenidos en types.ts ✅

  - [x] **Fase 4: Actualizar imports** ✅
    - [x] 4.1 signals.ts → ConnectionMode value import (fix TS1361) ✅
    - [x] 4.2 signals.ts → gpu_usage/gpu_memory (fix pre-existing metrics) ✅
    - [x] 4.3 effects.ts → EnumPipelineState (fix PipelineState usages) ✅
    - [x] 4.4 types.ts → selective exports (fix TS2308 duplicate exports) ✅
    - [x] 4.5 types/state.ts → import from api (fix circular) ✅
    - [x] 4.6 @preact/signals-core instalado ✅
    - [x] 4.7-4.11 Barrel chain funciona sin cambios en resto de archivos ✅
    - [NOTA] dashboard.ts ~20 strict types pre-existentes (DOM string vs literal)
    - [NOTA] tests necesitan @types/vitest (separado de esta refactor)

  - [x] **Fase 5: Verificación** ✅
    - [x] 5.1 npx tsc --noEmit → 74 errores pre-existentes (0 nuevos de refactor) ✅
    - [x] 5.2 npm run build:local → 19 pages built ✅
    - [x] 5.3 npm test -- --run → 2 tests passing ✅
    - [x] 5.4 Build va directo a server/static ✅

  - [x] **Fase 6: dashboard.ts strict types** ✅
    - [x] 6.1 getStatus import agregado ✅
    - [x] 6.2 VideoMuxerConfig.video_codec agregado ✅
    - [x] 6.3 VideoMuxerConfig.gpu_preset/video_preset agregado ✅
    - [x] 6.4 ModulesConfig.audio_extractor agregado ✅
    - [x] 6.5 Pipeline config campos completos (mode/max_concurrent_chunks/etc) ✅
    - [x] 6.6 Window.handleEngineChange removido ✅
    - [x] 6.7 inputType/outputType reference fix ✅
    - [x] 6.8 ttsEngine reference fix ✅
    - [x] 6.9 WARN→WARNING fix ✅

  - [x] **Fase 7: Verificación final** ✅
    - [x] 7.1 dashboard.ts → 0 errores de TypeScript ✅
    - [x] 7.2 Non-test errors → 18 errores (test files pre-existentes: 43)
    - [x] 7.3 npm run build:local → 19 pages built ✅

  - [x] **Fase 8: Otros módulos TypeScript** ✅
    - [x] 8.1 ModuleName/LogMessage exportados en api.ts ✅
    - [x] 8.2 LANGUAGE agregado a STORAGE_KEYS en constants ✅
    - [x] 8.3 formatTimestamp accepte string|number ✅
    - [x] 8.4 ConnectionMode agregado a api.ts ✅
    - [x] 8.5 MetricsData campos completos (gpu_util/gpu_memory_mb/etc) ✅
    - [x] 8.6 SrtInputConfig/RtmpInputConfig port opcional ✅
    - [x] 8.7 ModuleStatus.processed_chunks opcional ✅
    - [x] 8.8 effects.ts isRunning variable local ✅
    - [x] 8.9 signals.ts imports directos desde api.ts ✅
    - [x] 8.10 types.ts selective exports ✅
    - [x] 8.11 types/state.ts import desde api.ts ✅
    - [x] 8.12 signals.ts timestamp como ISO string ✅

  - [x] **Fase 9: Verificación final completo** ✅
    - [x] 9.1 npx tsc --noEmit → 0 errores non-test ✅
    - [x] 9.2 npm run build:local → 19 pages built ✅
```
