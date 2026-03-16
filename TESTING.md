# Guía de Testing - SRT2Web

## Ejecutar Tests

### Comandos Básicos

```bash
# Todos los tests
python -m pytest tests/ -v

# Solo tests unitarios (más rápidos)
python -m pytest tests/unit/ -v

# Tests específicos
python -m pytest tests/unit/test_api_routes.py -v
python -m pytest tests/unit/test_config_manager.py -v
python -m pytest tests/unit/test_pipeline.py -v

# Con coverage
python -m pytest tests/ --cov=. --cov-report=html

# Excluir tests lentos
python -m pytest tests/ -m "not slow"
```

### Marcadores (Markers)

| Marker | Descripción |
|--------|-------------|
| `@pytest.mark.slow` | Tests que tardan más de 5 segundos |
| `@pytest.mark.integration` | Tests de integración entre componentes |
| `@pytest.mark.e2e` | Tests end-to-end del sistema completo |
| `@pytest.mark.live` | Tests que requieren servidor activo |

### Ejecutar con Marker

```bash
# Solo tests rápidos
python -m pytest -m "not slow" tests/

# Solo tests de integración
python -m pytest -m integration tests/
```

## Estructura de Tests

```
tests/
├── conftest.py                  # Fixtures globales
├── unit/                        # Tests unitarios (aislados)
│   ├── test_api_routes.py       # 53 tests - API REST
│   ├── test_config_manager.py   # 18 tests - Gestión config
│   ├── test_pipeline.py         # 15 tests - Pipeline
│   ├── test_module_base.py      # Tests BaseModule
│   ├── test_ffmpeg_utils.py     # Tests utilidades FFmpeg
│   └── test_ws_routes.py        # Tests WebSockets
├── integration/                 # Tests de integración
│   └── test_server.py          # Tests del servidor
└── e2e/                        # Tests end-to-end
    ├── test_api_e2e.py
    ├── test_dashboard_page.py
    └── test_player_page.py
```

## Fixtures Disponibles

### `tests/conftest.py`

```python
@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Crea un directorio temporal para tests."""
    ...

@pytest.fixture
def config_file(temp_dir: str) -> str:
    """Crea un archivo de configuración temporal."""
    ...

@pytest.fixture
def sample_srt_content() -> str:
    """Contenido SRT de ejemplo para tests."""
    ...

@pytest.fixture
def sample_pipeline_data() -> dict:
    """Datos de PipelineData de ejemplo."""
    ...

@pytest.fixture
def mock_app_context():
    """Contexto de app mockeado."""
    ...

@pytest.fixture
def client(mock_app_context):
    """Cliente FastAPI TestClient."""
    ...
```

## Escribir Tests

### Test de API

```python
from fastapi.testclient import TestClient
from server.app import create_app

def test_endpoint():
    # Arrange
    app = create_app(mock_context)
    client = TestClient(app)
    
    # Act
    response = client.get("/api/status")
    
    # Assert
    assert response.status_code == 200
    assert "state" in response.json()
```

### Test de Módulo

```python
from core.module_base import BaseModule, PipelineData

class DummyModule(BaseModule):
    def start(self):
        self._state = ModuleState.RUNNING
    
    def stop(self):
        self._state = ModuleState.IDLE
    
    def _do_process(self, data: PipelineData) -> PipelineData:
        data.metadata["processed"] = True
        return data

def test_module_process():
    module = DummyModule("test")
    data = PipelineData(chunk_index=0)
    
    result = module.process(data)
    
    assert result.metadata["processed"] is True
```

### Test con Mock

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_func = Mock(return_value="result")
    
    result = mock_func()
    
    mock_func.assert_called_once()
    assert result == "result"
```

## Mejores Prácticas

1. **Nomenclatura**: `test_<metodo>_<escenario>`
2. **AAA**: Arrange, Act, Assert
3. **Un assert por test** cuando sea posible
4. **Fixtures** para código repetido
5. **No testear implementación**, sino comportamiento
6. **Tests deterministas**: sin dependencias de tiempo red

## Coverage

Para generar reporte de coverage:

```bash
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term
```

El reporte se genera en `htmlcov/index.html`.

## Integración MCP (Pytest MCP)

El proyecto incluye integración con Pytest MCP para debugging de fallos:

- Los fallos se registran automáticamente en `data/failures.json`
- Dashboard disponible en `http://localhost:3000`
- 9 principios de debugging disponibles

## Solución de Problemas

### Tests fallan por timeout

```bash
python -m pytest --timeout=300 tests/
```

### Tests lentos

```bash
# Ver qué tests son lentos
python -m pytest --durations=10 tests/
```

### Ver logs detallados

```bash
python -m pytest -v -s tests/
```
