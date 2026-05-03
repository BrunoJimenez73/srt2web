# Guia: Como Agregar un Nuevo Modulo al Pipeline

Esta guia explica paso a paso como agregar un nuevo modulo de procesamiento al pipeline de SRT2Web.

## Arquitectura del Pipeline

El pipeline sigue el patron **Chain of Responsibility**. Cada modulo recibe `PipelineData`, procesa los datos y pasa el resultado al siguiente modulo.

```
PipelineData → [Modulo 1] → [Modulo 2] → ... → [Modulo N] → OutputSink
```

## Estructura de Datos Principal

### PipelineData

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PipelineData:
    video_chunk_path: str | None = None
    audio_chunk_path: str | None = None
    subtitle_path: str | None = None
    tts_audio_path: str | None = None
    mixed_audio_path: str | None = None
    output_path: str | None = None
    chunk_index: int = 0
    duration: float = 0.0
    cumulative_duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
```

Cada modulo puede leer y modificar estos campos.

## Paso 1: Crear el Modulo

Crea un nuevo archivo en `modules/` siguiendo la convencion de nombres:

```python
# modules/mi_modulo.py
from __future__ import annotations

import logging
from pathlib import Path

from core.pipeline_data import PipelineData
from core.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class MiModulo:
    """Descripcion breve del modulo y su proposito."""

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._enabled = True
        self._processed_chunks = 0
        self._state = "stopped"

    async def process(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk del pipeline.

        Args:
            data: Datos del chunk actual.

        Returns:
            PipelineData modificado con los resultados del procesamiento.

        Raises:
            ProcessingError: Si ocurre un error durante el procesamiento.
        """
        if not self._enabled:
            return data

        self._state = "running"
        logger.debug(f"[MiModulo] Procesando chunk {data.chunk_index}")

        try:
            # Logica de procesamiento aqui
            result = await self._process_chunk(data)
            self._processed_chunks += 1
            return result

        except Exception as exc:
            logger.error(f"[MiModulo] Error en chunk {data.chunk_index}: {exc}")
            self._state = "error"
            raise ProcessingError(f"MiModulo fallo: {exc}") from exc
        finally:
            self._state = "stopped"

    async def _process_chunk(self, data: PipelineData) -> PipelineData:
        """Implementacion especifica del procesamiento."""
        # Ejemplo: leer archivo, transformar, escribir resultado
        return data

    def get_status(self) -> dict:
        """Retorna el estado actual del modulo para el frontend."""
        return {
            "name": "mi_modulo",
            "enabled": self._enabled,
            "state": self._state,
            "processed_chunks": self._processed_chunks,
            "extra": {
                "device": "cpu",
                "using_gpu": False,
            },
        }

    def reconfigure(self, config: dict) -> None:
        """Reconfigura el modulo en runtime."""
        self._config.update(config)

    async def shutdown(self) -> None:
        """Limpieza de recursos al detener el pipeline."""
        self._enabled = False
        self._state = "stopped"
        logger.info("[MiModulo] Modulo detenido")
```

## Paso 2: Registrar el Modulo en el Pipeline

### Opcion A: Pipeline Secuencial

Edita `core/app_context.py` y agrega tu modulo en la cadena:

```python
from modules.mi_modulo import MiModulo

# En create_pipeline_modules() o similar:
mi_modulo = MiModulo(config.get("mi_modulo", {}))
pipeline.add_module(mi_modulo)
```

### Opcion B: Modulo Condicional

Si el modulo solo debe ejecutarse bajo ciertas condiciones:

```python
if config.get("mi_modulo", {}).get("enabled", False):
    mi_modulo = MiModulo(config["mi_modulo"])
    pipeline.add_module(mi_modulo)
```

## Paso 3: Agregar Configuracion

### Schema Pydantic

Edita `core/config_schema.py` y agrega tu schema:

```python
from pydantic import BaseModel, Field


class MiModuloConfig(BaseModel):
    """Configuracion para MiModulo."""
    enabled: bool = False
    param1: str = "default"
    param2: int = Field(default=10, ge=1, le=100)
```

Agregalo al schema principal:

```python
class ModulesConfig(BaseModel):
    transcriber: TranscriberConfig = Field(default_factory=TranscriberConfig)
    # ... otros modulos ...
    mi_modulo: MiModuloConfig = Field(default_factory=MiModuloConfig)
```

### Config por Defecto

Edita `core/config_manager.py` y agrega los defaults:

```python
DEFAULT_CONFIG = {
    "modules": {
        # ... otros modulos ...
        "mi_modulo": {
            "enabled": False,
            "param1": "default",
            "param2": 10,
        },
    },
}
```

### config.yaml

Agrega la seccion en `config.yaml`:

```yaml
modules:
  mi_modulo:
    enabled: false
    param1: "valor"
    param2: 10
```

## Paso 4: Frontend (Opcional)

### Componente UI

Crea un componente en `frontend/src/components/`:

```astro
---
// MiModuloCard.astro
interface Props {
  module: import('../lib/types').ModuleStatus;
}
const { module } = Astro.props;
---

<div class="process-card">
  <div class="process-header">
    <h3>Mi Modulo</h3>
    <span class={`status ${module.state}`}>{module.state}</span>
  </div>
  <div class="process-content">
    <p>Chunks procesados: {module.processed_chunks}</p>
  </div>
</div>
```

### Integracion en ProcessGrid

Edita `frontend/src/components/ProcessGrid.astro`:

```astro
import MiModuloCard from './MiModuloCard.astro';

<!-- En el grid -->
<MiModuloCard module={modules.mi_modulo} />
```

### Tipos TypeScript

Si tu modulo tiene campos especificos, agregalos en `frontend/src/lib/types/api.ts`:

```typescript
export interface MiModuloConfig {
  enabled: boolean;
  param1: string;
  param2: number;
}
```

## Paso 5: Tests

Crea `tests/unit/test_mi_modulo.py`:

```python
import pytest
import asyncio
from modules.mi_modulo import MiModulo
from core.pipeline_data import PipelineData


class TestMiModulo:
    @pytest.fixture
    def modulo(self):
        return MiModulo({"param1": "test"})

    def test_init_default_config(self):
        m = MiModulo()
        assert m._enabled is True

    async def test_process_returns_data(self, modulo):
        data = PipelineData(chunk_index=0)
        result = await modulo.process(data)
        assert isinstance(result, PipelineData)

    async def test_process_disabled_returns_unchanged(self, modulo):
        modulo._enabled = False
        data = PipelineData(chunk_index=0, metadata={"original": True})
        result = await modulo.process(data)
        assert result.metadata == data.metadata

    def test_get_status(self, modulo):
        status = modulo.get_status()
        assert status["name"] == "mi_modulo"
        assert "enabled" in status
        assert "state" in status

    async def test_reconfigure(self, modulo):
        modulo.reconfigure({"param1": "new_value"})
        assert modulo._config["param1"] == "new_value"

    async def test_shutdown(self, modulo):
        await modulo.shutdown()
        assert modulo._enabled is False
        assert modulo._state == "stopped"
```

## Paso 6: Documentacion

### docs/architecture.md

Agrega tu modulo al diagrama Mermaid y a la tabla de modulos.

### docs/index.md

Agrega una entrada en la tabla de tecnologias y estados.

## Checklist Final

- [ ] Modulo creado en `modules/` con `process()`, `get_status()`, `reconfigure()`, `shutdown()`
- [ ] Modulo registrado en `core/app_context.py`
- [ ] Schema Pydantic en `core/config_schema.py`
- [ ] Defaults en `core/config_manager.py`
- [ ] Configuracion en `config.yaml`
- [ ] Componente frontend (opcional)
- [ ] Tests unitarios (minimo 5 tests)
- [ ] Documentacion actualizada
- [ ] Log con prefijo `[MiModulo]` para consistencia

## Buenas Practicas

1. **Logging**: Usa `logging.getLogger(__name__)` y prefijo `[NombreModulo]`
2. **Excepciones**: Usa `ProcessingError` para errores de procesamiento
3. **Estado**: Siempre actualiza `_state` (stopped/running/error)
4. **Recursos**: Limpia en `shutdown()` (archivos temporales, procesos, conexiones)
5. **Config**: Nunca asumas que una clave existe; usa `.get()` con defaults
6. **Async**: Si hay I/O bloqueante, usa `asyncio.to_thread()` o `aiofiles`
7. **Tests**: Testea cada metodo publico y casos de error

## Ejemplo Real: Audio Extractor

Para referencia, revisa `modules/audio_extractor.py` como ejemplo de modulo completo:

- Extrae audio de chunks de video usando FFmpeg
- Maneja errores gracefully con fallback
- Expone status con metricas de procesamiento
- Tests completos en `tests/unit/test_audio_extractor.py`
