# SRT2Web - Plan de Refactorización Python

## Estado Actual (Abril 2026)

### Fases Completadas ✅

#### Fase 1: Fundamentos
- ✅ `core/exceptions.py` - Jerarquía de excepciones personalizadas
- ✅ `core/types.py` - Tipos compartidos (enums, dataclasses)
- ✅ 45 tests unitarios pasando

#### Fase 2: Arquitectura de Módulos
- ✅ `core/module_interface.py` - ProcessingModule Protocol + BaseModule ABC
- ✅ 23 tests unitarios pasando
- ✅ Actualizado `core/__init__.py` para exportar nuevos módulos

### Fases Pendientes

#### Fase 3: Pipeline Asíncrono
**Objetivo**: Mejorar el pipeline para procesamiento asíncrono completo.

**Archivos existentes**:
- `core/pipeline.py` - Pipeline secuencial (threading)
- `core/async_pipeline.py` - Pipeline asíncrono (threading)

**Mejoras propuestas**:
1. Migrar a asyncio completo (eliminar threading)
2. Usar la nueva interfaz `ProcessingModule`
3. Mejorar manejo de errores con excepciones personalizadas
4. Agregar métricas de rendimiento por módulo

#### Fase 4: Testing Avanzado
**Objetivo**: Mejorar cobertura y calidad de tests.

**Propuestas**:
1. Tests de integración completos
2. Tests de carga/estrés
3. Mock factory para testing
4. CI/CD con GitHub Actions

#### Fase 5: Documentación
**Objetivo**: Documentar arquitectura y API.

**Propuestas**:
1. Docstrings consistentes (Google style)
2. Diagramas de arquitectura
3. Ejemplos de uso
4. Migration guide

## Nueva Arquitectura Propuesta

```
core/
├── __init__.py           # Exporta tipos, excepciones, interfaces
├── exceptions.py         # Excepciones personalizadas
├── types.py              # Tipos compartidos
├── module_interface.py   # ProcessingModule Protocol + BaseModule ABC
├── config_manager.py     # Gestión de configuración
├── pipeline.py           # Pipeline secuencial (legacy)
├── async_pipeline.py     # Pipeline asíncrono (mejorado)
├── model_cache.py        # Cache de modelos
├── ffmpeg_pool.py        # Pool de procesos FFmpeg
└── ...
```

## Beneficios de la Refactorización

1. **Mantenibilidad**: Código más fácil de entender y modificar
2. **Escalabilidad**: Fácil agregar nuevos módulos/inputs/outputs
3. **Testabilidad**: Tests más simples y cobertura completa
4. **Robustez**: Mejor manejo de errores y recuperación
5. **Performance**: Pipeline optimizado y asíncrono

## Migración Gradual

La refactorización se diseña para ser compatible hacia atrás:
- Los módulos existentes pueden migrar gradualmente a la nueva interfaz
- El pipeline legacy sigue funcionando
- Nuevos módulos usan la nueva arquitectura

## Commits Realizados

| Hash | Descripción |
|------|-------------|
| `fc1e4fa` | feat(refactor): Add core foundation modules (exceptions and types) |
| `9e4f195` | refactor(core): Update __init__.py to export new types and exceptions |
| `3a1f487` | feat(refactor): Add module interface architecture (Fase 2) |

## Tests Creados

| Archivo | Tests | Descripción |
|---------|-------|-------------|
| `tests/unit/test_core_foundation.py` | 45 | Tests para excepciones y tipos |
| `tests/unit/test_module_interface.py` | 23 | Tests para interfaz de módulos |
| **Total** | **68** | **Todos pasando** |