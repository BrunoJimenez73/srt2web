# SRT2Web - Plan de Refactorizacion Python

## Estado Actual (Mayo 2026)

### Version: 0.6.8

### Fases Completadas

#### Fase 1: Fundamentos

- `core/exceptions.py` - Jerarquia de excepciones personalizadas
- `core/types.py` - Tipos compartidos (enums, dataclasses)
- `core/pipeline_data.py` - Dataclass PipelineData

#### Fase 2: Arquitectura de Modulos

- `core/module_interface.py` - ProcessingModule Protocol + BaseModule ABC
- `core/config_schema.py` - Schema Pydantic centralizado
- `core/config_manager.py` - DEFAULT_CONFIG como unica fuente de verdad

#### Fase 3: Pipeline y Estado

- `core/pipeline_manager.py` - Orquestador del pipeline
- `core/pipeline_state_manager.py` - Gestion de estado (32 tests)
- `core/pipeline_error_handler.py` - Manejo de errores centralizado (33 tests)
- `core/app_context.py` - Fabrica para pipeline, modulos y I/O
- `core/pipeline/` - Modulos de pipeline (`base.py`, `sequential.py`, `parallel.py`, `async_pipeline.py`, `strategies.py`, `factory.py`)

#### Fase 4: Lifecycle y Server

- `server/lifespan.py` - Gestion de ciclo de vida del servidor
- `main.py` - Reducido a ~65 lineas (bootstrap minimo)

#### Fase 5: Testing

- 590+ tests passing
- 6 XFAIL documentados (config values pre-existentes)
- Tests de snapshot para configuracion (24 tests)
- Tests de migracion de config (22 tests)

#### Fase 6: Tooling y CI

- `mypy.ini` eliminado, config unificada en `pyproject.toml`
- MyPy en pre-commit hooks
- CI con matrix OS (ubuntu, windows, macos)
- Ruff configurado para lint + format

#### Fase 7: Documentacion

- `docs/architecture.md` - Diagramas Mermaid de arquitectura
- `docs/deployment.md` - Guia de despliegue con troubleshooting
- `docs/contributing.md` - Guia de contribucion
- `docs/new_module_guide.md` - Guia para agregar nuevos modulos
- `docs/outputs.md` - Documentacion del sistema de salidas
- `docs/cli.md` - Documentacion CLI

## Arquitectura Actual

```
core/
├── __init__.py           # Exporta tipos, excepciones, interfaces
├── exceptions.py         # Jerarquia de excepciones
├── types.py              # Tipos compartidos
├── pipeline_data.py      # Dataclass PipelineData
├── config_schema.py      # Schema Pydantic centralizado
├── config_manager.py     # Gestion de configuracion
├── pipeline_manager.py   # Orquestador del pipeline
├── pipeline_state_manager.py  # Gestion de estado
├── pipeline_error_handler.py  # Manejo de errores
├── app_context.py        # Fabrica de componentes
├── module_interface.py   # ProcessingModule Protocol
├── ffmpeg_pool.py        # Pool de procesos FFmpeg
├── ffmpeg_utils.py       # Utilidades FFmpeg
├── model_cache.py        # Cache de modelos
├── logging_setup.py      # Logging con file rotation
├── watchdog.py           # Watchdog de recursos
├── security.py           # Middlewares de seguridad
└── pipeline/             # Modulos de pipeline
    ├── base.py
    ├── sequential.py
    ├── parallel.py
    ├── async_pipeline.py
    ├── strategies.py
    └── factory.py

modules/
├── audio_extractor.py    # Extraccion de audio
├── transcriber.py        # Transcripcion (Whisper)
├── translator.py         # Traduccion (Argos)
├── subtitle_generator.py # Generacion de subtitulos
├── tts_engine.py         # Sintesis de voz (Piper)
├── audio_mixer.py        # Mezcla de audio (numpy)
├── video_muxer.py        # Muxer de video HLS
├── piper_loader.py       # Loader de Piper (subprocess)
└── inputs/               # Modulos de entrada
    ├── srt_input.py
    ├── rtmp_input.py
    └── file_input.py

server/
├── app.py                # FastAPI app factory
├── lifespan.py           # Startup/shutdown lifecycle
├── api_routes.py         # REST API endpoints
├── ws_routes.py          # WebSocket endpoints
└── security.py           # Middlewares de seguridad
```

## Modulos Pendientes

### Mejoras Incrementales

1. **Tipado Python**: Corregir errores de mypy en `core/` (actualmente ~20 errores)
2. **Modulos grandes**: Reducir `core/unified_pipeline.py` (940 lineas)
3. **Tests de integracion**: Pipeline completo con TTS deshabilitado
4. **Correlation ID**: Tracking de chunks a traves del pipeline
5. **Logs estructurados**: Campos consistentes (module, chunk_index, stage, duration_ms)
6. **Backpressure**: Medicion de latencia y congestión

### Prioridad Baja

- Docstrings Google-style en funciones publicas criticas
- Sustituir `Any` innecesarios por tipos concretos o `Protocol`
- Evitar bloques `except Exception` sin contexto

## Beneficios de la Refactorizacion

1. **Mantenibilidad**: Código mas facil de entender y modificar
2. **Escalabilidad**: Fácil agregar nuevos modulos/inputs/outputs
3. **Testabilidad**: Tests mas simples y cobertura completa
4. **Robustez**: Mejor manejo de errores y recuperación
5. **Performance**: Pipeline optimizado y asincrono

## Commits Principales

| Descripcion            | Archivos Clave                   |
| ---------------------- | -------------------------------- |
| Pipeline data flow fix | `modules/inputs/srt_input.py`    |
| Piper TTS subprocess   | `modules/piper_loader.py`        |
| Audio mixer numpy      | `modules/audio_mixer.py`         |
| Config schema Pydantic | `core/config_schema.py`          |
| Pipeline state manager | `core/pipeline_state_manager.py` |
| Pipeline error handler | `core/pipeline_error_handler.py` |
| App context factory    | `core/app_context.py`            |
| Server lifecycle       | `server/lifespan.py`             |
| MyPy config unificado  | `pyproject.toml`                 |
| CI matrix OS           | `.github/workflows/ci.yml`       |

## Tests

| Categoria            | Count |
| -------------------- | ----- |
| Unit tests           | 590+  |
| XFAIL (documentados) | 6     |
| Config snapshot      | 24    |
| Config migration     | 22    |
| Pipeline state       | 32    |
| Pipeline error       | 33    |
