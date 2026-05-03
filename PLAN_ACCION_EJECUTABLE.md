# ⚙️ PLAN DE ACCIÓN EJECUTABLE

**Versión:** 1.0
**Estado:** Listo para implementar
**Estimado:** 6-12 semanas

---

## 🎯 FASE 1: SETUP INICIAL (Semana 1-2)

### Paso 1.1: Configurar Control de Código

- [ ] **Git configuration**

  ```bash
  git config core.editor vim
  git config user.name "Tu Nombre"
  git config user.email "tu@email.com"
  ```

- [ ] **Pre-commit hooks**

  ```bash
  pip install pre-commit --break-system-packages
  npm install husky lint-staged --save-dev
  ```

  Crear `.pre-commit-config.yaml`:

  ```yaml
  repos:
    - repo: https://github.com/psf/black
      rev: 23.3.0
      hooks:
        - id: black
    - repo: https://github.com/PyCQA/flake8
      rev: 6.0.0
      hooks:
        - id: flake8
    - repo: https://github.com/pre-commit/mirrors-isort
      rev: 5.12.0
      hooks:
        - id: isort
  ```

- [ ] **Configurar .gitignore**

  ```
  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  .venv/
  venv/
  .env
  .env.local

  # Node
  node_modules/
  dist/
  .next/
  out/

  # IDEs
  .vscode/
  .idea/
  *.swp
  *.swo

  # OS
  .DS_Store
  Thumbs.db

  # Logs
  logs/
  *.log
  ```

### Paso 1.2: Configurar Backend (Python)

- [ ] **Crear estructura de proyecto**

  ```bash
  mkdir -p src/{domain,application,infrastructure,presentation}
  mkdir -p tests/{unit,integration}
  touch pyproject.toml README.md Makefile
  ```

- [ ] **Instalar dependencias base**

  ```bash
  # Usar Poetry
  pip install poetry --break-system-packages
  poetry init

  # O con pip
  python -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  ```

- [ ] **Configurar pyproject.toml**

  ```toml
  [tool.poetry]
  name = "miproyecto"
  version = "0.1.0"
  description = "Descripción del proyecto"

  [tool.poetry.dependencies]
  python = "^3.11"
  fastapi = "^0.104.0"
  sqlalchemy = "^2.0.0"
  pydantic = "^2.0.0"
  pydantic-settings = "^2.0.0"
  alembic = "^1.12.0"
  python-dotenv = "^1.0.0"

  [tool.poetry.group.dev.dependencies]
  pytest = "^7.4.0"
  pytest-asyncio = "^0.21.0"
  pytest-cov = "^4.1.0"
  black = "^23.7.0"
  flake8 = "^6.0.0"
  isort = "^5.12.0"
  mypy = "^1.4.0"

  [tool.black]
  line-length = 88
  target-version = ['py311']

  [tool.isort]
  profile = "black"

  [tool.mypy]
  strict = true
  python_version = "3.11"
  disallow_untyped_defs = true
  ```

- [ ] **Crear Makefile**

  ```makefile
  .PHONY: install test lint format type-check clean

  install:
  	poetry install

  test:
  	pytest tests/ -v --cov=src

  lint:
  	flake8 src/ tests/
  	isort --check-only src/ tests/

  format:
  	black src/ tests/
  	isort src/ tests/

  type-check:
  	mypy src/

  clean:
  	find . -type d -name __pycache__ -exec rm -rf {} +
  	find . -type f -name "*.pyc" -delete
  	rm -rf .pytest_cache/ .mypy_cache/
  ```

### Paso 1.3: Configurar Frontend (Astro + TypeScript)

- [ ] **Crear proyecto Astro**

  ```bash
  npm create astro@latest -- --template minimal
  cd proyecto-astro
  npm install
  ```

- [ ] **Instalar integraciones esenciales**

  ```bash
  npx astro add react tailwind
  npm install -D @astrojs/sitemap astro-compress
  ```

- [ ] **Crear structure**

  ```bash
  mkdir -p src/{components,layouts,pages,lib,types,assets/{images,styles}}
  touch src/types/index.ts
  ```

- [ ] **Configurar tsconfig.json**

  ```json
  {
    "extends": "astro/tsconfigs/strict",
    "compilerOptions": {
      "baseUrl": ".",
      "paths": {
        "@/*": ["src/*"],
        "@components/*": ["src/components/*"],
        "@layouts/*": ["src/layouts/*"],
        "@utils/*": ["src/lib/*"],
        "@types/*": ["src/types/*"]
      }
    }
  }
  ```

- [ ] **Configurar package.json scripts**

  ```json
  {
    "scripts": {
      "dev": "astro dev",
      "build": "astro build",
      "preview": "astro preview",
      "lint": "eslint src/ --ext .ts,.tsx,.astro",
      "format": "prettier --write src/",
      "type-check": "tsc --noEmit",
      "test": "jest"
    }
  }
  ```

- [ ] **Instalar herramientas de desarrollo**
  ```bash
  npm install -D \
    eslint \
    @typescript-eslint/eslint-plugin \
    @typescript-eslint/parser \
    prettier \
    jest \
    @testing-library/react \
    ts-jest \
    @types/jest
  ```

### Paso 1.4: Configurar Git Workflow

- [ ] **Crear branches**

  ```bash
  git checkout -b develop
  git checkout -b feature/initial-setup
  ```

- [ ] **Crear template para PRs**

  `.github/pull_request_template.md`:

  ```markdown
  ## Description

  Describe your changes here

  ## Type of Change

  - [ ] Bug fix
  - [ ] New feature
  - [ ] Breaking change

  ## How Has This Been Tested?

  ## Checklist

  - [ ] Tests pass locally
  - [ ] Code is formatted (black/prettier)
  - [ ] Type checks pass
  - [ ] No new warnings
  ```

---

## 📝 FASE 2: ESTRUCTURA Y ARQUITECTURA (Semana 3-4)

### Paso 2.1: Backend Base Structure

- [ ] **Crear modelos de dominio**

  `src/domain/entities/user.py`:

  ```python
  from dataclasses import dataclass
  from datetime import datetime
  from typing import Optional

  @dataclass
  class User:
      """Entidad de usuario."""
      id: Optional[int] = None
      email: str
      name: str
      is_active: bool = True
      created_at: datetime = None
      updated_at: datetime = None

      def __post_init__(self):
          if self.created_at is None:
              self.created_at = datetime.utcnow()
          if self.updated_at is None:
              self.updated_at = datetime.utcnow()
  ```

- [ ] **Crear excepciones personalizadas**

  `src/domain/exceptions.py`:

  ```python
  class DomainException(Exception):
      """Excepción base del dominio."""
      pass

  class UserNotFoundError(DomainException):
      """Usuario no encontrado."""
      def __init__(self, user_id: int):
          self.user_id = user_id
          super().__init__(f"Usuario {user_id} no encontrado")

  class EmailAlreadyExistsError(DomainException):
      """El email ya existe."""
      def __init__(self, email: str):
          self.email = email
          super().__init__(f"Email {email} ya registrado")
  ```

- [ ] **Crear interfaces de repositorio**

  `src/domain/repositories/user_repository.py`:

  ```python
  from abc import ABC, abstractmethod
  from typing import Optional, List
  from src.domain.entities.user import User

  class IUserRepository(ABC):
      """Interfaz para repositorio de usuarios."""

      @abstractmethod
      async def get_by_id(self, user_id: int) -> Optional[User]:
          """Obtiene usuario por ID."""
          pass

      @abstractmethod
      async def get_by_email(self, email: str) -> Optional[User]:
          """Obtiene usuario por email."""
          pass

      @abstractmethod
      async def save(self, user: User) -> User:
          """Guarda un usuario."""
          pass

      @abstractmethod
      async def list_all(self, skip: int = 0, limit: int = 10) -> List[User]:
          """Lista todos los usuarios."""
          pass

      @abstractmethod
      async def delete(self, user_id: int) -> None:
          """Elimina un usuario."""
          pass
  ```

- [ ] **Crear DTOs**

  `src/application/dtos/user_dto.py`:

  ```python
  from pydantic import BaseModel, EmailStr, field_validator

  class UserCreateDTO(BaseModel):
      """DTO para crear usuario."""
      email: EmailStr
      name: str
      password: str

      @field_validator('name')
      @classmethod
      def name_not_empty(cls, v: str) -> str:
          if not v.strip():
              raise ValueError('El nombre no puede estar vacío')
          return v.strip()

  class UserResponseDTO(BaseModel):
      """DTO para respuesta de usuario."""
      id: int
      email: str
      name: str
      is_active: bool

      class Config:
          from_attributes = True
  ```

- [ ] **Crear service layer**

  `src/application/services/user_service.py`:

  ```python
  from typing import Optional, List
  from src.domain.entities.user import User
  from src.domain.repositories.user_repository import IUserRepository
  from src.domain.exceptions import UserNotFoundError, EmailAlreadyExistsError
  from src.application.dtos.user_dto import UserCreateDTO, UserResponseDTO

  class UserApplicationService:
      """Servicio de aplicación para usuarios."""

      def __init__(self, repository: IUserRepository):
          self.repository = repository

      async def create_user(self, user_dto: UserCreateDTO) -> UserResponseDTO:
          """Crea un nuevo usuario."""
          # Validar que email no exista
          existing = await self.repository.get_by_email(user_dto.email)
          if existing:
              raise EmailAlreadyExistsError(user_dto.email)

          # Crear usuario
          user = User(
              email=user_dto.email,
              name=user_dto.name,
          )
          saved_user = await self.repository.save(user)

          return UserResponseDTO.model_validate(saved_user)

      async def get_user(self, user_id: int) -> UserResponseDTO:
          """Obtiene un usuario."""
          user = await self.repository.get_by_id(user_id)
          if not user:
              raise UserNotFoundError(user_id)
          return UserResponseDTO.model_validate(user)
  ```

### Paso 2.2: Database Setup

- [ ] **Crear configuración de BD**

  `src/infrastructure/database/config.py`:

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker, declarative_base
  from src.core.config import DATABASE_URL

  engine = create_engine(
      DATABASE_URL,
      echo=False,
      pool_size=20,
      max_overflow=0,
  )

  SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
  Base = declarative_base()

  def get_db_session():
      """Obtiene sesión de BD."""
      session = SessionLocal()
      try:
          yield session
      finally:
          session.close()
  ```

- [ ] **Crear modelos de BD**

  `src/infrastructure/database/models/user_model.py`:

  ```python
  from sqlalchemy import Column, Integer, String, Boolean, DateTime
  from datetime import datetime
  from src.infrastructure.database.config import Base

  class UserModel(Base):
      """Modelo de usuario en BD."""
      __tablename__ = "users"

      id = Column(Integer, primary_key=True)
      email = Column(String(255), unique=True, nullable=False, index=True)
      name = Column(String(255), nullable=False)
      password_hash = Column(String(255), nullable=False)
      is_active = Column(Boolean, default=True)
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  ```

- [ ] **Crear migraciones con Alembic**

  ```bash
  alembic init -t async alembic
  ```

  `alembic/env.py` - Configurar para generar automáticamente

- [ ] **Implementar repositorio**

  `src/infrastructure/database/repositories/user_repository.py`:

  ```python
  from sqlalchemy.orm import Session
  from typing import Optional, List
  from src.domain.entities.user import User
  from src.domain.repositories.user_repository import IUserRepository
  from src.infrastructure.database.models.user_model import UserModel

  class SQLAlchemyUserRepository(IUserRepository):
      """Repositorio SQL para usuarios."""

      def __init__(self, session: Session):
          self.session = session

      async def get_by_id(self, user_id: int) -> Optional[User]:
          result = self.session.query(UserModel).filter(
              UserModel.id == user_id
          ).first()
          return self._map_to_domain(result) if result else None

      async def save(self, user: User) -> User:
          model = UserModel(email=user.email, name=user.name)
          self.session.add(model)
          self.session.commit()
          user.id = model.id
          return user

      @staticmethod
      def _map_to_domain(model: UserModel) -> User:
          return User(
              id=model.id,
              email=model.email,
              name=model.name,
              is_active=model.is_active,
          )
  ```

### Paso 2.3: Frontend Components

- [ ] **Crear Layout base**

  `src/layouts/BaseLayout.astro`:

  ```astro
  ---
  interface Props {
    title: string;
  }

  const { title } = Astro.props;
  ---

  <!DOCTYPE html>
  <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{title} - Mi Proyecto</title>
    </head>
    <body>
      <header>
        <nav><!-- Navigation --></nav>
      </header>
      <main>
        <slot />
      </main>
      <footer><!-- Footer --></footer>
    </body>
  </html>

  <style is:global>
    @import url('assets/styles/global.css');
  </style>
  ```

- [ ] **Crear componentes UI base**

  `src/components/Button.astro`:

  ```astro
  ---
  interface Props {
    variant?: 'primary' | 'secondary';
    size?: 'sm' | 'md' | 'lg';
    type?: 'button' | 'submit' | 'reset';
  }

  const { variant = 'primary', size = 'md', type = 'button' } = Astro.props;
  ---

  <button class={`btn btn-${variant} btn-${size}`} type={type}>
    <slot />
  </button>

  <style>
    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 0.375rem;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s;
    }

    .btn-primary {
      background-color: #0ea5e9;
      color: white;
    }

    .btn-primary:hover {
      background-color: #0284c7;
    }
  </style>
  ```

- [ ] **Crear tipos TypeScript**

  `src/types/index.ts`:

  ```typescript
  export interface User {
    id: number;
    email: string;
    name: string;
    isActive: boolean;
    createdAt: string;
  }

  export interface ApiResponse<T> {
    status: "success" | "error";
    data?: T;
    error?: string;
  }

  export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
  }
  ```

---

## 🧪 FASE 3: TESTING (Semana 5-6)

### Paso 3.1: Backend Testing

- [ ] **Setup pytest**

  ```bash
  pip install pytest pytest-asyncio pytest-cov pytest-mock --break-system-packages
  ```

- [ ] **Crear conftest.py**

  `tests/conftest.py`:

  ```python
  import pytest
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from src.infrastructure.database.config import Base
  from src.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository

  @pytest.fixture(scope="session")
  def test_db():
      """Base de datos de test."""
      engine = create_engine("sqlite:///:memory:")
      Base.metadata.create_all(engine)
      yield engine

  @pytest.fixture
  def db_session(test_db):
      """Sesión de BD para tests."""
      connection = test_db.connect()
      transaction = connection.begin()
      session = sessionmaker(bind=connection)()
      yield session
      transaction.rollback()
      connection.close()

  @pytest.fixture
  def user_repository(db_session):
      """Repositorio de usuarios."""
      return SQLAlchemyUserRepository(db_session)
  ```

- [ ] **Crear tests unitarios**

  `tests/unit/test_user_service.py`:

  ```python
  import pytest
  from src.application.services.user_service import UserApplicationService
  from src.application.dtos.user_dto import UserCreateDTO
  from src.domain.exceptions import UserNotFoundError

  @pytest.mark.asyncio
  async def test_create_user(user_repository):
      """Test crear usuario."""
      service = UserApplicationService(user_repository)

      user_dto = UserCreateDTO(
          email="test@example.com",
          name="Test User",
          password="password123"
      )

      result = await service.create_user(user_dto)

      assert result.email == "test@example.com"
      assert result.name == "Test User"

  @pytest.mark.asyncio
  async def test_user_not_found(user_repository):
      """Test usuario no encontrado."""
      service = UserApplicationService(user_repository)

      with pytest.raises(UserNotFoundError):
          await service.get_user(999)
  ```

- [ ] **Generar reporte de coverage**
  ```bash
  pytest tests/ --cov=src --cov-report=html
  ```

### Paso 3.2: Frontend Testing

- [ ] **Setup Jest**

  ```bash
  npm install -D jest @testing-library/react @testing-library/astro ts-jest
  ```

- [ ] **Crear jest.config.js**

  ```javascript
  export default {
    preset: "ts-jest",
    testEnvironment: "jsdom",
    moduleNameMapper: {
      "^@/(.*)$": "<rootDir>/src/$1",
    },
    setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  };
  ```

- [ ] **Crear tests de componentes**

  `src/components/__tests__/Button.test.tsx`:

  ```typescript
  import { render, screen } from '@testing-library/react';
  import Button from '../Button';

  describe('Button Component', () => {
    it('renders with text', () => {
      render(<Button>Click me</Button>);
      expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
    });

    it('calls onClick when clicked', () => {
      const onClick = jest.fn();
      render(<Button onClick={onClick}>Click</Button>);
      screen.getByRole('button').click();
      expect(onClick).toHaveBeenCalled();
    });
  });
  ```

---

## 🔒 FASE 4: SEGURIDAD (Semana 7)

### Paso 4.1: Backend Security

- [ ] **Implementar autenticación JWT**

  ```bash
  pip install python-jose bcrypt --break-system-packages
  ```

- [ ] **Crear servicios de auth**

  `src/infrastructure/security/auth.py`:

  ```python
  from datetime import datetime, timedelta
  from jose import JWTError, jwt
  from passlib.context import CryptContext
  from typing import Optional

  SECRET_KEY = "your-secret-key-change-in-production"
  ALGORITHM = "HS256"

  pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

  def hash_password(password: str) -> str:
      return pwd_context.hash(password)

  def verify_password(plain: str, hashed: str) -> bool:
      return pwd_context.verify(plain, hashed)

  def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
      to_encode = data.copy()
      if expires_delta:
          expire = datetime.utcnow() + expires_delta
      else:
          expire = datetime.utcnow() + timedelta(hours=1)
      to_encode.update({"exp": expire})
      return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  ```

- [ ] **Configurar CORS y headers**

  `src/presentation/main.py`:

  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware

  app = FastAPI()

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://example.com"],
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "DELETE"],
      allow_headers=["*"],
  )
  ```

### Paso 4.2: Frontend Security

- [ ] **Implementar Content Security Policy**

  `astro.config.mjs`:

  ```javascript
  export default defineConfig({
    vite: {
      ssr: {
        noExternal: ["sharp"],
      },
    },
    middleware: true,
  });
  ```

  `src/middleware.ts`:

  ```typescript
  import { defineMiddleware } from "astro:middleware";

  export const onRequest = defineMiddleware(({ request, response }, next) => {
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set("X-Frame-Options", "DENY");
    response.headers.set("X-XSS-Protection", "1; mode=block");
    return next();
  });
  ```

- [ ] **Configurar HTTPS en desarrollo**
  ```bash
  mkcert -install
  mkcert localhost 127.0.0.1
  ```

### Paso 4.3: Dependency Scanning

- [ ] **Python vulnerabilities**

  ```bash
  pip install safety --break-system-packages
  safety check
  ```

- [ ] **JavaScript vulnerabilities**

  ```bash
  npm audit
  npm install -D snyk
  snyk test
  ```

- [ ] **Automatizar en CI**
  ```yaml
  # .github/workflows/security.yml
  name: Security Checks
  on: [push, pull_request]
  jobs:
    security:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - run: pip install safety
        - run: safety check
        - run: npm audit
  ```

---

## 📊 FASE 5: MONITORING Y DEPLOYMENT (Semana 8-9)

### Paso 5.1: CI/CD Setup

- [ ] **Crear GitHub Actions workflow**

  `.github/workflows/ci.yml`:

  ```yaml
  name: CI/CD Pipeline
  on: [push, pull_request]

  jobs:
    test-backend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-python@v4
          with:
            python-version: "3.11"
        - run: pip install poetry
        - run: poetry install
        - run: poetry run pytest tests/ --cov=src
        - run: poetry run black --check src/
        - run: poetry run mypy src/

    test-frontend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-node@v3
          with:
            node-version: "18"
        - run: npm install
        - run: npm run type-check
        - run: npm run lint
        - run: npm test
        - run: npm run build

    deploy:
      needs: [test-backend, test-frontend]
      if: github.ref == 'refs/heads/main'
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - name: Deploy to production
          run: echo "Deploying..."
  ```

### Paso 5.2: Logging y Monitoring

- [ ] **Configurar logging estruturado**

  `src/core/logging.py`:

  ```python
  import logging
  import json
  from pythonjsonlogger import jsonlogger

  def setup_logging():
      """Configura logging estruturado."""
      logger = logging.getLogger()
      logHandler = logging.StreamHandler()
      formatter = jsonlogger.JsonFormatter()
      logHandler.setFormatter(formatter)
      logger.addHandler(logHandler)
      logger.setLevel(logging.INFO)
      return logger

  logger = setup_logging()
  ```

- [ ] **Implementar health checks**

  `src/presentation/api/health.py`:

  ```python
  from fastapi import APIRouter, Depends
  from sqlalchemy.orm import Session

  router = APIRouter()

  @router.get("/health")
  async def health_check(db: Session = Depends(get_db)):
      """Health check endpoint."""
      try:
          await db.execute("SELECT 1")
          return {"status": "healthy"}
      except Exception:
          return {"status": "unhealthy"}, 500
  ```

### Paso 5.3: Containerización

- [ ] **Crear Dockerfile**

  `Dockerfile`:

  ```dockerfile
  # Backend
  FROM python:3.11-slim

  WORKDIR /app

  COPY pyproject.toml poetry.lock ./
  RUN pip install poetry && poetry install --no-dev

  COPY src/ src/
  COPY .env.production .env

  EXPOSE 8000
  CMD ["poetry", "run", "uvicorn", "src.presentation.main:app", "--host", "0.0.0.0"]
  ```

- [ ] **Crear docker-compose.yml**

  `docker-compose.yml`:

  ```yaml
  version: "3.8"
  services:
    backend:
      build: .
      ports:
        - "8000:8000"
      environment:
        DATABASE_URL: postgresql://user:pass@db:5432/mydb
      depends_on:
        - db

    db:
      image: postgres:15
      environment:
        POSTGRES_USER: user
        POSTGRES_PASSWORD: pass
        POSTGRES_DB: mydb
      volumes:
        - postgres_data:/var/lib/postgresql/data

  volumes:
    postgres_data:
  ```

---

## 📚 FASE 6: DOCUMENTACIÓN (Semana 10)

- [ ] **README.md completo**
- [ ] **API Documentation (OpenAPI/Swagger)**
- [ ] **Architecture Decision Records**
- [ ] **Deployment Guide**
- [ ] **Troubleshooting Guide**

---

## ✅ CHECKLIST FINAL

- [ ] Todos los tests pasando (>80% coverage)
- [ ] Code formateo con Black/Prettier
- [ ] Type checks pasando (mypy/tsc)
- [ ] Linting 0 errores
- [ ] Security audit passed
- [ ] Performance targets met
- [ ] Documentación completa
- [ ] CI/CD en verde
- [ ] Deployment procedure tested
- [ ] Rollback procedure documented

---

**Siguiente paso:** Seleccionar FASE 1 y comenzar implementación
