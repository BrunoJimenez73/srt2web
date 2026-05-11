# Guía de Contribución - SRT2Web

## Bienvenido a SRT2Web

Gracias por tu interés en contribuir a SRT2Web. Este documento te guiará a través del proceso de configuración, desarrollo y envío de contribuciones.

## Tabla de Contenidos

1. [Configuración del Entorno](#configuración-del-entorno)
2. [Flujo de Trabajo](#flujo-de-trabajo)
3. [Estándares de Código](#estándares-de-código)
4. [Tests](#tests)
5. [Documentación](#documentación)
6. [Envío de Cambios](#envío-de-cambios)

---

## Configuración del Entorno

### Requisitos Previos

- Python 3.12+
- Node.js 18+
- Git
- FFmpeg
- NVIDIA CUDA (opcional, para GPU)

### Clonar el Repositorio

```bash
git clone https://github.com/BrunoJimenez73/srt2web.git
cd srt2web
```

### Instalar Dependencias Python

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r config/requirements.txt

# Instalar pre-commit hooks
pre-commit install
```

### Instalar Dependencias Frontend

```bash
cd frontend
npm install
```

### Verificar Instalación

```bash
# Tests Python
python -m pytest tests/unit/ -v --tb=short

# TypeScript frontend
cd frontend && npx tsc --noEmit

# Frontend tests (Vitest)
cd frontend && npm test

# Mypy strict
mypy --strict core/ modules/ server/
```

## Flujo de Trabajo

### 1. Crear Rama de Características

```bash
# Desde main
git checkout main
git pull origin main

# Crear nueva rama
git checkout -b feat/nombre-descriptivo
# o
git checkout -b fix/descripcion-del-bug
```

### 2. Desarrollo

```bash
# Trabaja en tu código
# Haz commits pequeños y frecuentes

git add archivo_modificado.py
git commit -m "feat: descripción clara del cambio"
```

### 3. Ejecutar Tests Locales

```bash
# Todos los tests (740 tests)
python -m pytest tests/ -v

# Solo tests unitarios
python -m pytest tests/unit/ -v

# Archivo específico
python -m pytest tests/unit/test_audio_mixer.py -v

# Con coverage
python -m pytest tests/ --cov=. --cov-report=html

# Frontend tests
cd frontend && npm test
```

### 4. Linting y Type Checking

```bash
# Python (ruff + mypy)
ruff check .
mypy --strict .

# Frontend (TypeScript)
cd frontend && npx tsc --noEmit

# Pre-commit hooks
pre-commit run --all-files
```

### 5. Actualizar Documentación

```bash
# Generar MkDocs localmente
cd docs && mkdocs serve

# Verificar en http://localhost:8000
```

---

## Estándares de Código

### Python

#### Style Guide

- **Línea máxima**: 120 caracteres
- **Indentación**: 4 espacios
- **Imports**: Ordenados con ruff (isort)
- **Type hints**: Obligatorios en funciones públicas

```python
# ✅ Correcto
def process_chunk(chunk: ChunkData, config: dict) -> PipelineResult:
    """Procesa un chunk de video y retorna el resultado."""
    ...

# ❌ Incorrecto
def process_chunk(chunk, config):
    ...
```

#### Docstrings

```python
def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """Transcribe audio a texto usando Whisper.

    Args:
        audio_path: Ruta al archivo de audio.
        language: Código de idioma ISO 639-1.

    Returns:
        Texto transcrito.

    Raises:
        AudioExtractionError: Si el audio no puede ser extraído.
        TranscriptionError: Si Whisper falla.
    """
```

#### Naming Conventions

| Tipo       | Convention  | Ejemplo               |
| ---------- | ----------- | --------------------- |
| Variables  | snake_case  | `chunk_duration`      |
| Funciones  | snake_case  | `get_audio_path()`    |
| Clases     | PascalCase  | `AudioExtractor`      |
| Constantes | UPPER_SNAKE | `MAX_CHUNK_SIZE`      |
| Módulos    | snake_case  | `audio_mixer.py`      |
| Tests      | `test_*.py` | `test_audio_mixer.py` |

### TypeScript

```typescript
// ✅ Correcto
interface ModuleStatus {
  name: string;
  enabled: boolean;
  state: ModuleState;
  extra?: Record<string, unknown>;
}

export function getStatus(): Promise<ModuleStatus> {
  // ...
}

// ❌ Incorrecto
function getStatus() {
  // ...
}
```

### Frontend: Signals & Effects

El frontend usa **Preact Signals** para estado reactivo. Cuando añadas nuevo estado UI:

```typescript
// src/lib/store/signals.ts - Definir signal
import { signal, computed } from "@preact/signals-core";

export const myNewState = signal<MyType>(initialValue);
export const myComputed = computed(() => myNewState.value.derived);
```

```typescript
// src/lib/store/effects.ts - Efecto DOM
function setupMyEffect(): EffectCleanup {
  return effect(() => {
    const value = myNewState.value;
    const el = document.getElementById("my-element");
    if (el) el.textContent = value;
  });
}
```

### Git Commits

Formato: `<type>(<scope>): <description>`

| Type       | Descripción                    |
| ---------- | ------------------------------ |
| `feat`     | Nueva funcionalidad            |
| `fix`      | Corrección de bug              |
| `docs`     | Cambios en documentación       |
| `style`    | Formateo, estilos (sin lógica) |
| `refactor` | Refactorización de código      |
| `perf`     | Mejoras de rendimiento         |
| `test`     | Tests nuevos o modificados     |
| `chore`    | Tareas de mantenimiento        |

```bash
# Ejemplos
git commit -m "feat(audio): add numpy-based mixing"
git commit -m "fix(pipeline): correct chunk buffer handling"
git commit -m "docs(readme): update installation steps"
git commit -m "feat(outputs): add WebRTC output support"
git commit -m "test(signals): add unit tests for store signals"
```

---

## Tests

### Estructura de Tests

```
tests/
├── unit/              # Tests unitarios (740 tests)
│   ├── test_*.py      # Tests por módulo
│   └── pytest.ini     # Config pytest
└── integration/       # Tests de integración (futuro)
```

### Ejecutar Tests

```bash
# Todos los tests unitarios
python -m pytest tests/unit/ -v

# Tests específicos
python -m pytest tests/unit/test_audio_mixer.py -v
python -m pytest tests/unit/test_multioutput_api.py -v

# Con verbose y coverage
python -m pytest tests/ --cov=. --cov-report=term-missing

# Solo tests nuevos
python -m pytest tests/unit/test_workspace_fixes.py -v
```

### Escribir Tests

```python
# tests/unit/test_audio_mixer.py
import pytest
from modules.audio_mixer import AudioMixer

class TestAudioMixerNumpy:
    """Tests para implementación numpy del mixer."""

    def test_mix_audio_with_ducking(self, temp_dir, mock_audio_files):
        """Verifica que el ducking funciona correctamente."""
        mixer = AudioMixer(
            original_volume=0.15,
            tts_volume=1.0
        )
        result = mixer.mix(
            original="original.wav",
            tts="tts.wav",
            output_dir=temp_dir
        )
        assert result.endswith(".wav")
        assert os.path.exists(result)
```

### Tests Frontend

```bash
cd frontend

# Ejecutar tests Vitest (signals + effects)
npm test

# TypeScript check
npx tsc --noEmit

# Build
npm run build:local
```

Los tests frontend usan **Vitest + jsdom** para testear:

- **Signals**: `signals.test.ts` - Tests de señales reactivas
- **Effects**: `effects.test.ts` - Tests de efectos DOM (requiren jsdom)

---

## Documentación

### Docstrings

Todos los módulos deben tener docstrings:

```python
"""Módulo de transcripción de audio.

Utiliza OpenAI Whisper para convertir audio a texto.
Soporta múltiples idiomas y modelos de diferentes tamaños.

Ejemplo:
    >>> transcriber = Transcriber(model="base", device="cuda")
    >>> text = transcriber.transcribe("audio.wav")
"""

class Transcriber:
    ...
```

### Docstrings en Funciones

```python
def get_status() -> dict:
    """Obtiene el estado actual del módulo.

    Returns:
        Dictionary con:
        - name: Nombre del módulo
        - enabled: Si está habilitado
        - state: Estado actual (idle/running/error)
        - extra: Metadatos adicionales (GPU, memoria, etc.)
    """
```

### MkDocs

La documentación se genera con MkDocs Material:

```bash
# Servidor local
cd docs && mkdocs serve

# Build
mkdocs build

# Deploy a GitHub Pages
mkdocs gh-deploy --force
```

Archivos de docs:

- `docs/index.md` - Página principal
- `docs/architecture.md` - Arquitectura del sistema
- `docs/deployment.md` - Guía de despliegue
- `docs/contributing.md` - Esta guía
- `docs/outputs.md` - Sistema multi-output
- `docs/cli.md` - Herramienta CLI

---

## Áreas de Contribución

### Añadir un Nuevo Input

1. Crear clase en `modules/inputs/nuevo_input.py`
2. Heredar de `InputSource` y `BaseModule`
3. Registrar en `modules/inputs/__init__.py`
4. Añadir a `VALID_INPUT_TYPES` en `core/config_schema.py`
5. Crear UI en `frontend/src/components/InputCard.astro`
6. Tests en `tests/unit/test_nuevo_input.py`

### Añadir un Nuevo Output

1. Crear clase en `modules/outputs/nuevo_output.py`
2. Heredar de `OutputSink` y `BaseModule`
3. Registrar en `modules/outputs/__init__.py`
4. Añadir a `VALID_OUTPUT_TYPES` en `core/config_schema.py`
5. Crear UI en `frontend/src/components/OutputConfigForm.astro`
6. Tests en `tests/unit/test_nuevo_output.py`

### Añadir un Nuevo Módulo de Pipeline

1. Crear clase heredando de `BaseModule`
2. Implementar: `initialize()`, `process()`, `get_status()`, `shutdown()`
3. Añadir a `core/pipeline.py` en el flujo
4. Crear card UI en `frontend/src/components/`
5. Tests unitarios

---

## Envío de Cambios

### 1. Sync con Main

```bash
git fetch origin
git rebase origin/main
```

### 2. Push de Rama

```bash
git push origin feat/nombre-de-rama
```

### 3. Crear Pull Request

1. Ve a GitHub → Pull requests → New pull request
2. Selecciona tu rama → main
3. Completa la plantilla:
   - **Título**: Descripción clara
   - **Descripción**: Qué, Por qué, Cómo
   - **Link a issues**: Si aplica

### Template de PR

```markdown
## Descripción

[Breve descripción del cambio]

## Tipo de Cambio

- [ ] Bug fix
- [ ] Nueva funcionalidad
- [ ] Breaking change
- [ ] Documentación

## Testing

- [ ] Tests añadidos
- [ ] Tests pasando
- [ ] Verificado manualmente

## Checklist

- [ ] Código sigue style guide
- [ ] Type hints completos
- [ ] Docstrings actualizados
- [ ] Docs actualizadas
- [ ] Commits semánticos
```

### Revisión de Código

El PR será revisado por maintainers. Sé receptivo a feedback:

- Responde a comentarios
- Haz cambios solicitados
- Re-solicita revisión cuando esté listo

---

## Recursos Adicionales

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Preact Signals](https://preactjs.com/guide/v10/signals/)
- [MkDocs User Guide](https://www.mkdocs.org/user-guide/)
- [Testing with pytest](https://docs.pytest.org/)
- [Astro Documentation](https://docs.astro.build/)

## Preguntas

Si tienes dudas, abre un issue o contacta a los maintainers.
