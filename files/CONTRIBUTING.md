# 🤝 Guía de Contribución

¡Gracias por tu interés en contribuir a nuestro proyecto! Este documento te guiará a través del proceso.

## Código de Conducta

Todos los colaboradores deben adherirse a nuestro [Código de Conducta](./CODE_OF_CONDUCT.md).

Esperamos comportamiento profesional, respetuoso e inclusivo de todos los participantes.

## ¿Cómo Puedo Contribuir?

### Reportar Bugs 🐛

Antes de reportar un bug, verifica si ya ha sido reportado. Si estás seguro de que es nuevo:

1. **Usa un título descriptivo** para el issue
2. **Describe el problema con claridad**
3. **Proporciona pasos específicos** para reproducir
4. **Describe el comportamiento observado**
5. **Explica cuál era el comportamiento esperado**
6. **Incluye screenshots/logs** si es posible
7. **Menciona tu ambiente** (SO, Python version, Node version)

**Ejemplo de issue bien reportado:**

```markdown
**Descripción del bug**
Al intentar crear un usuario con email vacío, la API no devuelve error.

**Pasos para reproducir**

1. Hacer POST a /api/users
2. Enviar payload: {"email": "", "name": "Test"}
3. Recibir 201 en lugar de 400

**Comportamiento esperado**
Devolver 400 Bad Request con detalle: "Email is required"

**Screenshots**
[Adjuntar si aplica]

**Ambiente**

- OS: Ubuntu 22.04
- Python: 3.11.2
- FastAPI: 0.104.0
```

### Sugerir Enhancements 💡

Si tienes una idea para mejorar el proyecto:

1. **Usa un título claro y descriptivo**
2. **Proporciona descripción detallada**
3. **Proporciona ejemplos concretos**
4. **Describe el beneficio esperado**

### Pull Requests 🔄

Las pull requests son bienvenidas. Para mantener calidad:

**Antes de comenzar:**

1. Fork el repositorio
2. Crea rama con nombre descriptivo
3. Configura tu ambiente local
4. Haz pequeños commits lógicos

**Flujo de trabajo:**

```bash
# 1. Actualizar rama principal
git checkout main
git pull origin main

# 2. Crear rama feature
git checkout -b feat/descripcion-feature

# 3. Hacer cambios y tests
# ... código ...

# 4. Ejecutar verificaciones
make lint
make type-check
make test

# 5. Commit
git add .
git commit -m "feat: descripción clara del cambio"

# 6. Push
git push origin feat/descripcion-feature

# 7. Abrir Pull Request en GitHub
```

**Convención de ramas:**

- `feat/nombre-feature` - Nuevas características
- `fix/nombre-bug` - Corrección de bugs
- `docs/descripcion` - Documentación
- `refactor/descripcion` - Refactoring
- `perf/descripcion` - Mejoras de performance
- `test/descripcion` - Tests

## 💻 Desarrollo Local

### Requisitos

- Python 3.11+
- Node.js 18+
- Poetry
- pnpm o npm

### Setup

```bash
# Clonar tu fork
git clone https://github.com/tu-usuario/proyecto.git
cd proyecto

# Instalar dependencias
make install

# Instalar pre-commit hooks
pre-commit install

# Crear rama
git checkout -b feat/tu-feature
```

### Desarrollo

```bash
# Terminal 1: Backend
make dev-backend

# Terminal 2: Frontend
make dev-frontend

# En otra terminal: Tests en watch mode
pytest tests/ -v --tb=short -x -w
```

### Verificaciones antes de Push

```bash
# Formatear código
make format

# Lint
make lint

# Type checking
make type-check

# Tests
make test

# O todo junto (CI local)
make ci
```

## 📋 Checklist para Pull Request

Antes de abrir tu PR, verifica:

- [ ] Mi código sigue las convenciones de estilo del proyecto
- [ ] He ejecutado `make lint` sin errores
- [ ] He ejecutado `make type-check` sin errores
- [ ] He agregado tests para mis cambios
- [ ] Mis tests pasan localmente (`make test`)
- [ ] He actualizado la documentación si aplica
- [ ] Mi commit messag sigue [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] No hay cambios sin relacionados en el PR
- [ ] He revisado mi propio código antes de enviarlo

## ✍️ Estilo de Código

### Python

Usamos **Black** para formatting y **MyPy** para type checking.

```python
# ✅ Bien
def create_user(email: str, name: str) -> User:
    """Crea un nuevo usuario.

    Args:
        email: Email del usuario
        name: Nombre del usuario

    Returns:
        Usuario creado

    Raises:
        ValueError: Si email es inválido
    """
    if not is_valid_email(email):
        raise ValueError("Email inválido")

    user = User(email=email, name=name)
    return user

# ❌ Mal
def createUser(email, name):
    # Crear usuario
    u = User(email, name)
    return u
```

**Reglas:**

- Usar **type hints** siempre
- **Docstrings** Google-style para funciones públicas
- **Line length**: 88 caracteres (Black default)
- **Variable names**: snake_case
- **Class names**: PascalCase
- **Constants**: SCREAMING_SNAKE_CASE

### TypeScript

Usamos **Prettier** para formatting y **ESLint** para linting.

```typescript
// ✅ Bien
interface UserInput {
  email: string;
  name: string;
}

const createUser = (input: UserInput): Promise<User> => {
  // Validar
  validateEmail(input.email);

  return api.post('/users', input);
};

// ❌ Mal
const createUser = (input) => {
  return api.post('/users', input);
};
```

**Reglas:**

- Usar **type annotations** siempre (TypeScript strict)
- **JSDoc** para funciones públicas
- **Line length**: 88 caracteres
- **Variable names**: camelCase
- **Type names**: PascalCase
- **Enum names**: SCREAMING_SNAKE_CASE

## 📝 Mensajes de Commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/).

**Formato:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: Nueva característica
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Cambios de formato (sin lógica)
- `refactor`: Refactoring de código
- `perf`: Mejoras de performance
- `test`: Agregar/actualizar tests
- `chore`: Cambios de configuración
- `ci`: Cambios en CI/CD

**Ejemplos:**

```bash
# Característica simple
git commit -m "feat: agregar autenticación JWT"

# Con scope
git commit -m "feat(auth): agregar login con Google"

# Con cuerpo
git commit -m "fix(api): corregir validación de email

La validación no rechazaba algunos emails válidos.
Se mejoró la expresión regular según RFC 5322."

# Breaking change
git commit -m "refactor!: cambiar estructura de API

BREAKING CHANGE: El endpoint /users ahora requiere
autenticación Bearer token."
```

## 🧪 Testing

Todos los cambios deben incluir tests.

### Backend (Python/Pytest)

```python
# tests/unit/test_user_service.py
import pytest
from src.application.services.user_service import UserApplicationService
from src.domain.exceptions import InvalidEmailError

@pytest.mark.asyncio
async def test_create_user_success(user_repository):
    """Test creación exitosa de usuario."""
    service = UserApplicationService(user_repository)

    result = await service.create_user(
        email="test@example.com",
        name="Test User"
    )

    assert result.email == "test@example.com"
    assert result.name == "Test User"

@pytest.mark.asyncio
async def test_create_user_invalid_email(user_repository):
    """Test creación con email inválido."""
    service = UserApplicationService(user_repository)

    with pytest.raises(InvalidEmailError):
        await service.create_user(
            email="invalid-email",
            name="Test User"
        )
```

### Frontend (TypeScript/Jest)

```typescript
// src/components/__tests__/Button.test.tsx
import { render, screen } from '@testing-library/react';
import Button from '../Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('calls onClick handler', () => {
    const onClick = jest.fn();
    render(<Button onClick={onClick}>Click</Button>);
    screen.getByRole('button').click();
    expect(onClick).toHaveBeenCalled();
  });
});
```

**Requisitos:**

- Mínimo 80% de cobertura
- Tests deben ser independientes
- Usar descriptores claros
- Mockear dependencias externas

## 🔍 Review Process

1. **Verificaciones automáticas**

   - Linting
   - Type checking
   - Tests
   - Build

2. **Revisión de código**

   - Un o más maintainers revisarán
   - Pueden solicitar cambios
   - Discusión constructiva

3. **Aprobación**

   - Mínimo 1 aprobación
   - Todos los comentarios resueltos
   - Checks pasando

4. **Merge**
   - Squash or rebase merge
   - Rama eliminada automáticamente

## 📚 Documentación

Los cambios en API o features deben incluir documentación:

- **Code comments**: Para lógica compleja
- **Docstrings**: Para funciones públicas
- **README**: Para instrucciones de setup
- **API docs**: Para nuevos endpoints
- **CHANGELOG**: Para cambios principales

## 🎓 Convenciones del Proyecto

### Estructura de carpetas

```
src/
├── domain/         # Lógica de negocio
├── application/    # Casos de uso
├── infrastructure/ # Detalles técnicos
└── presentation/   # API
```

### Nombres de archivos

- **Python**: snake_case.py
- **TypeScript**: kebab-case.tsx / camelCase.ts
- **Config**: lowercase.config.js
- **Tests**: test\__.py o _.test.tsx

### Imports

```python
# Python: Agrupar por categoría
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.orm import Session

from src.domain.entities import User
from src.infrastructure.database import get_db
```

```typescript
// TypeScript: Agrupar y ordenar alfabéticamente
import { FC, useState } from 'react';
import type { ReactNode } from 'react';

import { cn } from '@/utils/cn';
import type { ButtonProps } from '@/types/ui';
```

## 🚨 Problemas Comunes

### Tests fallan localmente pero pasan en CI

- Asegúrate de estar en la rama correcta
- Ejecuta `make clean && make install`
- Comprueba Python/Node versions

### Merge conflicts

```bash
# Actualizar tu rama
git fetch origin
git rebase origin/main

# Resolver conflictos en editor
git add .
git rebase --continue
git push origin feat/tu-feature -f
```

### Cambios rechazados por pre-commit

```bash
# Ejecutar hooks manualmente
make pre-commit

# Revisar cambios
git diff

# Si quieres saltarte (no recomendado)
git commit --no-verify
```

## 📞 Preguntas?

- 💬 Abre una discussion en GitHub
- 📧 Contáctanos en tu@email.com
- 🐦 Twitter: @tu-handle

## 🎯 Contribuidores

¡Gracias a todos los que contribuyen!

[Lista de contribuidores aquí]

---

**Última actualización:** 2026-05-01

¡Esperamos tu contribución! 🚀
