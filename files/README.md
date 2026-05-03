# 📱 Mi Proyecto - Fullstack Moderno

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue)](https://www.typescriptlang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Proyecto fullstack moderno construido con **Python/FastAPI**, **Astro** y **TypeScript**, siguiendo las mejores prácticas de arquitectura limpia, DDD y testing.

## 🚀 Características

- ✅ **Backend robusto** con FastAPI y arquitectura Clean Code
- ✅ **Frontend rápido** con Astro + Islands Architecture
- ✅ **Type-safe** - TypeScript strict mode + Python type hints
- ✅ **Testing completo** - Unit, Integration, E2E (>80% coverage)
- ✅ **Seguridad** - JWT auth, CORS, OWASP compliance
- ✅ **Accesibilidad** - WCAG 2.1 AA compliant
- ✅ **Performance** - Lighthouse 90+, LCP < 2.5s
- ✅ **DevOps ready** - Docker, CI/CD, monitoring

## 📋 Requisitos

- **Python**: 3.11+
- **Node.js**: 18+
- **Poetry**: Para gestión de dependencias Python
- **pnpm/npm**: Para gestión de dependencias JavaScript

## ⚡ Quick Start

### 1. Clonar repositorio

```bash
git clone <tu-repo>
cd mi-proyecto
```

### 2. Instalar dependencias

```bash
# Backend
poetry install

# Frontend
npm install

# Pre-commit hooks
pre-commit install
```

### 3. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus configuraciones
nano .env
```

**Variables requeridas:**

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# CORS
FRONTEND_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

### 4. Ejecutar servidores

```bash
# Terminal 1: Backend (puerto 8000)
make dev-backend

# Terminal 2: Frontend (puerto 3000)
make dev-frontend
```

Visita:

- Backend API: [http://localhost:8000](http://localhost:8000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Frontend: [http://localhost:3000](http://localhost:3000)

## 📁 Estructura del Proyecto

```
proyecto/
├── src/
│   ├── domain/              # Lógica de negocio pura
│   │   ├── entities/
│   │   ├── repositories/
│   │   └── exceptions.py
│   ├── application/         # Casos de uso y servicios
│   │   ├── services/
│   │   ├── dtos/
│   │   └── use_cases/
│   ├── infrastructure/      # Detalles técnicos
│   │   ├── database/
│   │   ├── security/
│   │   └── config.py
│   └── presentation/        # API REST
│       ├── api/
│       ├── middleware/
│       └── main.py
├── frontend/                # Astro + TypeScript
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── lib/
│   │   └── types/
│   └── astro.config.mjs
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── alembic/                 # Database migrations
├── pyproject.toml
├── tsconfig.json
└── Makefile
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
make test

# Tests específicos
make test-backend      # Solo Python
make test-frontend     # Solo TypeScript

# Con cobertura
make test-coverage

# Watch mode
poetry run pytest tests/ -v --tb=short -x
```

## 🔍 Linting y Formatting

```bash
# Verificar código
make lint                   # Lint completo
make lint-python           # Solo Python
make lint-frontend         # Solo TypeScript

# Formatear automáticamente
make format                # Formatear todo
make format-python         # Solo Python
make format-frontend       # Solo TypeScript

# Type checking
make type-check            # TypeScript + Python
```

## 📊 Pre-commit Hooks

Los hooks se ejecutan automáticamente antes de cada commit:

- ✨ Formateo con Black/Prettier
- 🔍 Linting con Flake8/ESLint
- 📘 Type checking con MyPy/TypeScript
- 🔒 Seguridad con Bandit
- 📝 Validación de commits

Ejecutar manualmente:

```bash
make pre-commit
```

## 🔐 Variables de Entorno

Crear archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://example.com

# Logging
LOG_LEVEL=INFO

# Features
DEBUG=False
ENVIRONMENT=development
```

### Frontend (.env)

```env
# API
PUBLIC_API_URL=http://localhost:8000
PUBLIC_API_TIMEOUT=30000

# Features
PUBLIC_ENABLE_ANALYTICS=false
```

## 📦 Dependencias Principales

### Backend

- **FastAPI**: Framework web moderno
- **SQLAlchemy**: ORM para base de datos
- **Pydantic**: Validación de datos
- **PyJWT**: Autenticación JWT
- **Alembic**: Migraciones de BD

### Frontend

- **Astro**: Framework SSR/SSG rápido
- **React**: Para componentes interactivos
- **Tailwind CSS**: Styling utility-first
- **TypeScript**: Type-safety

## 🚀 Deployment

### Docker

```bash
# Build imagen
docker build -t mi-proyecto .

# Ejecutar
docker run -p 8000:8000 --env-file .env.production mi-proyecto
```

### Docker Compose

```bash
docker-compose up -d
```

## 📚 Documentación

- [Guía de Arquitectura](./docs/ARCHITECTURE.md)
- [API Documentation](./docs/API.md)
- [Contributing Guidelines](./CONTRIBUTING.md)
- [Development Guide](./docs/DEVELOPMENT.md)

## 🛠️ Comandos Útiles

```bash
# Ver todos los comandos disponibles
make help

# Database
make db-migrate          # Ejecutar migraciones
make db-migrate-new      # Crear nueva migración
make db-downgrade        # Revertir migración

# Development
make dev-backend         # Iniciar backend
make dev-frontend        # Iniciar frontend

# Production
make build              # Build completo
make security-check     # Escaneo de seguridad

# Cleaning
make clean              # Limpiar archivos temporales
make clean-all          # Limpiar todo incluyendo deps
```

## 🔒 Seguridad

- ✅ JWT authentication
- ✅ CORS configurado
- ✅ SQL injection prevention (ORM)
- ✅ XSS protection
- ✅ CSRF protection
- ✅ Dependency scanning
- ✅ OWASP compliance

Ejecutar escaneo de seguridad:

```bash
make security-check
```

## 📈 Performance

Métricas objetivo:

- 🎯 Lighthouse score: **≥ 90**
- 🎯 LCP: **< 2.5s**
- 🎯 FID: **< 100ms**
- 🎯 CLS: **< 0.1**
- 🎯 API response: **< 200ms (p95)**

## 🤝 Contribuir

Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para guías de desarrollo.

**Flujo de contribución:**

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Convención de Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: descripción de la característica
fix: descripción del bug
docs: cambios en documentación
style: cambios de formato (no logic)
refactor: refactoring de código
perf: mejoras de performance
test: agregar/actualizar tests
chore: cambios en configuración
ci: cambios en CI/CD
```

Ejemplo:

```bash
git commit -m "feat: agregar autenticación JWT"
git commit -m "fix: corregir validación de email"
```

## 🐛 Reportar Bugs

Crear issue con:

- Descripción clara del problema
- Pasos para reproducir
- Comportamiento esperado vs actual
- Environment (OS, Python version, etc)
- Logs/screenshots si es relevante

## 💡 Sugerir Features

Crear issue con label `enhancement`:

- Descripción del feature
- Caso de uso
- Beneficio esperado

## 📄 Licencia

MIT License - ver [LICENSE](./LICENSE) para más detalles.

## 👥 Autores

- **Tu Nombre** - Inicial development

## 📞 Soporte

- 📧 Email: tu@email.com
- 💬 Discussions: GitHub Discussions
- 🐛 Issues: GitHub Issues

## 🙏 Agradecimientos

- [FastAPI](https://fastapi.tiangolo.com/)
- [Astro](https://astro.build/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)

## 📊 Status

| Component | Status           |
| --------- | ---------------- |
| Backend   | ✅ Active        |
| Frontend  | ✅ Active        |
| Tests     | ✅ 80%+ coverage |
| Docs      | ✅ Complete      |

---

**Última actualización:** 2026-05-01
**Versión:** 0.1.0 (Beta)
