# Changelog - SRT2Web!

Todas las versiones notables se documentan en este archivo. El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.6.9] - 2026-05-03

### Agregado
- ✅ Pytest markers configurados (unit, integration, e2e, performance, security, slow, gpu, cpu)
- ✅ Justfile con comandos unificados de calidad (cross-platform)
- ✅ API contract tests (test_api_contract.py - verifica /api/config, /api/status, /api/outputs)
- ✅ WebSocket auth tests simplificados (test_websocket_auth.py)
- ✅ Documentación ADRs: pipeline architecture, Pydantic compatibility
- ✅ GitHub Pages workflow para documentación automática
- ✅ Dockerfile actualizado a Python 3.12

### Corregido
- ❌ Pydantic v1/v2 import compatibility (config_manager.py)
- ❌ getMetricClass() en effects.ts (warning/critical classes)
- ❌ Vulnerabilidades seguridad fixeadas (0 restantes)
- ❌ test_structured_log.py - missing import pytest

### Cambiado
- 🔄 222 unit tests with @pytest.mark.unit
- 🔄 test_api_contract.py - /api/status returns dict (not list)
- 🔄 .pre-commit-config.yaml - mypy and tsc hooks configurados

## [0.6.8] - 2026-05-03

### Agregado
- ✅ Accesibilidad WCAG 2.2 AA completada (aria-labels, roles, keyboard nav, reduced-motion)
- ✅ ESLint flat config (eslint.config.js) con reglas TypeScript y Astro
- ✅ Tests de utilidades frontend (utils.test.ts - 15 tests)
- ✅ Documentación de matriz de compatibilidad (docs/compatibility.md)
- ✅ README.md actualizado con comandos rápidos y matriz de compatibilidad
- ✅ Pytest markers configurados (unit, integration, e2e, performance, security, slow, gpu, cpu)
- ✅ Makefile y justfile con comandos unificados de calidad
- ✅ Correlation ID para logs estructurados (core/structured_log.py)
- ✅ Tests de logs estructurados (test_structured_log.py - 10 tests)
- ✅ Tests API frontend (api.test.ts - 23 tests)
- ✅ Benchmarks reproducibles (tests/benchmark/benchmark_pipeline.py)

### Corregido
- ❌ Pydantic v1/v2 import compatibility (config_manager.py)
- ❌ getMetricClass() en effects.ts (warning/critical classes)
- ❌ startMetricsEffects() aplicaba clase a elemento incorrecto
- ❌ effects.test.ts expectations (critical at 90%+)
- ❌ Vulnerabilidades seguridad en aiohttp, cryptography, onnx, pygments, pytest, requests

### Corregido
- ❌ Tipos `any` eliminados del frontend (Player, ConfigCollector, Types)
- ❌ Interfaz Window extendida con player y saveConfig
- ❌ ModuleStatus con campo `memory_mb` faltante
- ❌ CPU metrics tests pre-existentes fallando (2 tests)

### Cambiado
- 🔄 Frontend type-check: 0 errores TypeScript (`tsc --noEmit`)
- 🔄 Build frontend: exitoso (19 páginas)
- 🔄 TODOs.md actualizado con tareas completadas

## [0.6.7] - 2026-04-27

### Agregado
- ✅ Documentación completa MkDocs (docs/, mkdocs.yml)
- ✅ Diagramas Mermaid (architecture.md)
- ✅ GitHub Actions CI/CD configurado (.github/workflows/)
- ✅ Guía de contribución (docs/contributing.md)

### Corregido
- ❌ Typos en docs/architecture.md
- ❌ Mermaid diagrams renderizando incorrectamente

## [0.6.6] - 2026-04-22

### Agregado
- ✅ Empaquetamiento Electron (desktop/)
- ✅ Scripts de inicio para Mac Silicon (install_Mac.sh, start_Mac.sh)
- ✅ Detección de GPU con nvidia-ml-py (reemplaza GPUtil)

### Cambiado
- 🔄 Requisitos: Python 3.12+ (NO 3.13+ por pydantic v1)
- 🔄 FFmpeg pool de procesos (ffmpeg_pool.py)

## [0.6.5] - 2026-04-14

### Agregado
- ✅ Refactoring para mantenibilidad (main.py reducido 21%)
- ✅ Módulos nuevos: core/cuda_paths.py, core/logging_setup.py
- ✅ Clock utility unificado (frontend/src/lib/utils/clock.ts)

### Corregido
- ❌ File paths incorrectos en tests
- ❌ Import statements faltantes en frontend

## [0.6.4] - 2026-04-12

### Agregado
- ✅ Latencia reducida: ~75s → ~15s
- ✅ Audio mixing con numpy (~100x más rápido)
- ✅ Piper subprocess manager (evita bloqueo event loop)
- ✅ Chunk duration configurable (10s)

### Corregido
- ❌ Audio duplicado (original_volume 0.7 → 0.15)
- ❌ A/V desync (verificación de duración restaurada)
- ❌ FFmpeg atempo reemplazado por length_scale

## [0.6.3] - 2026-04-04

### Agregado
- ✅ Suite de tests completa: 590 tests passing
- ✅ Fix workspace errors (TypeScript module resolution)
- ✅ Frontend types unificados (api.ts como fuente de verdad)

### Corregido
- ❌ Tests fallidos pre-existentes documentados (6 XFAIL)
- ❌ Config paths hardcodeados en tests

## [0.6.2] - 2026-04-02

### Agregado
- ✅ Configuración Pydantic centralizada (core/config_schema.py)
- ✅ Migración automática de configuraciones antiguas
- ✅ Tests de snapshot/contrato para configuración (24 tests)

### Corregido
- ❌ Duplicación de configuración entre módulos
- ❌ Bug en _load() de config_manager.py

## [0.6.1] - 2026-03-30

### Agregado
- ✅ Fix pipeline data flow (PipelineData dataclass syntax)
- ✅ Logging persistente en logs/srt2web.log
- ✅ Scripts de inicio mejorados (Start.bat, Run.bat)

### Corregido
- ❌ SRT Input creaba PipelineData con dicts en vez de dataclass
- ❌ TTS Piper crasheaba por modelo lento (subprocess)
- ❌ cuDNN 9.x incompatible con ONNX Runtime

## [0.6.0] - 2026-03-28

### Agregado
- ✅ Refactoring frontend completo (Tailwind CSS + Astro components)
- ✅ Módulos UI base (Button, Input, Toggle, Badge, Card)
- ✅ Modularización JavaScript (ui.ts, config.ts, events.ts, player.ts)

### Cambiado
- 🔄 Frontend: index.astro de 1272 → 35 líneas
- 🔄 Frontend: player.astro de 358 → 30 líneas

## [0.5.0] - 2026-03-15

### Agregado
- ✅ Seguridad: AuthMiddleware, RateLimiter, SecurityHeaders
- ✅ GPU indicators en dashboard (Whisper, TTS, HLS)
- ✅ Video muxer status en pipeline

### Corregido
- ❌ WebSocket crash (FastAPI Request wrapper)
- ❌ Config model: invalid_model → small
- ❌ Player HLS: ErrorTypes undefined → !data.fatal

---

**Leyenda:**
- ✅ Agregado
- ❌ Corregido  
- 🔄 Cambiado
- ❎ Eliminado

