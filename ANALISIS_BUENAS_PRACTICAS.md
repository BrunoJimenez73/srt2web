# 🎯 ANÁLISIS DETALLADO DE BUENAS PRÁCTICAS

**Proyecto:** [Tu Proyecto]  
**Fecha:** 2026-05-01  
**Versión:** 1.0

---

## 📋 TABLA DE CONTENIDOS
1. [Python Best Practices](#python-best-practices)
2. [TypeScript Best Practices](#typescript-best-practices)
3. [Astro Best Practices](#astro-best-practices)
4. [Arquitectura del Proyecto](#arquitectura-del-proyecto)
5. [UI/UX Design Patterns](#uiux-design-patterns)
6. [Performance & Scalability](#performance--scalability)

---

## 🐍 PYTHON BEST PRACTICES

### 1. Estructura del Proyecto

```
proyecto/
├── src/
│   └── miproyecto/
│       ├── __init__.py
│       ├── domain/              # Lógica de negocio pura
│       │   ├── models.py
│       │   ├── entities.py
│       │   └── value_objects.py
│       ├── application/         # Casos de uso
│       │   ├── services.py
│       │   ├── dto/
│       │   │   ├── request.py
│       │   │   └── response.py
│       │   └── use_cases/
│       ├── infrastructure/      # Detalles técnicos
│       │   ├── database/
│       │   │   ├── models.py
│       │   │   ├── repositories.py
│       │   │   └── migrations/
│       │   ├── external_services/
│       │   └── config.py
│       └── presentation/        # FastAPI/Django
│           ├── api/
│           │   ├── routes/
│           │   ├── schemas.py
│           │   └── dependencies.py
│           └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── conftest.py
│   └── fixtures/
├── pyproject.toml
├── poetry.lock (o requirements.txt)
├── Makefile
└── .env.example
```

### 2. Code Style & Formatting

**✅ DEBE HACER:**

```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 88

[tool.ruff]
select = ["E", "F", "W"]
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**✅ CÓDIGO CORRECTO:**

```python
# ✓ Type hints completos
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from enum import Enum

@dataclass
class User:
    """Representa un usuario en el sistema.
    
    Attributes:
        id: Identificador único del usuario
        email: Email del usuario (debe ser único)
        name: Nombre completo del usuario
        is_active: Indica si el usuario está activo
    """
    id: int
    email: str
    name: str
    is_active: bool = True

# ✓ Docstring Google-style
def calculate_total_price(
    items: List[Dict[str, float]],
    tax_rate: float = 0.0,
    discount_percentage: Optional[float] = None
) -> float:
    """Calcula el precio total de una lista de items.
    
    Args:
        items: Lista de items con estructura {'price': float, 'quantity': int}
        tax_rate: Tasa de impuesto a aplicar (defecto 0)
        discount_percentage: Porcentaje de descuento a aplicar
        
    Returns:
        float: Precio total después de impuestos y descuentos
        
    Raises:
        ValueError: Si tax_rate o discount_percentage están fuera de rango
        TypeError: Si items no es una lista
        
    Example:
        >>> items = [{'price': 100, 'quantity': 2}]
        >>> calculate_total_price(items, tax_rate=0.1)
        220.0
    """
    if not isinstance(items, list):
        raise TypeError("items debe ser una lista")
    
    if not 0 <= tax_rate <= 1:
        raise ValueError("tax_rate debe estar entre 0 y 1")
    
    subtotal = sum(item['price'] * item.get('quantity', 1) for item in items)
    
    if discount_percentage:
        if not 0 <= discount_percentage <= 100:
            raise ValueError("discount_percentage debe estar entre 0 y 100")
        subtotal *= (1 - discount_percentage / 100)
    
    return subtotal * (1 + tax_rate)

# ✓ Context managers
class DatabaseConnection:
    """Gestor de conexión a base de datos."""
    
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self.conn = None
    
    def __enter__(self) -> 'DatabaseConnection':
        """Abre la conexión."""
        self.conn = self._create_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cierra la conexión siempre."""
        if self.conn:
            self.conn.close()
    
    def _create_connection(self):
        """Crea la conexión a la BD."""
        # Implementación
        pass

# Usar:
with DatabaseConnection("postgresql://...") as db:
    db.query("SELECT * FROM users")

# ✓ Async/Await correcto
import asyncio
from typing import Awaitable

async def fetch_user_data(user_id: int) -> Dict[str, any]:
    """Obtiene datos del usuario de forma asincrónica."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/api/users/{user_id}") as resp:
            return await resp.json()

async def process_multiple_users(user_ids: List[int]) -> List[Dict]:
    """Procesa múltiples usuarios en paralelo."""
    tasks: List[Awaitable] = [fetch_user_data(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks)
    return results

# ✓ Validación con Pydantic
from pydantic import BaseModel, EmailStr, validator, field_validator

class UserCreate(BaseModel):
    """Schema para crear un usuario."""
    email: EmailStr
    name: str
    age: int
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Valida que el nombre no esté vacío."""
        if not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()
    
    @field_validator('age')
    @classmethod
    def age_valid(cls, v: int) -> int:
        """Valida que la edad sea válida."""
        if v < 0 or v > 150:
            raise ValueError('La edad debe estar entre 0 y 150')
        return v

# ✓ Excepciones personalizadas
class DomainException(Exception):
    """Excepción base del dominio."""
    pass

class UserNotFoundError(DomainException):
    """Se lanza cuando no se encuentra un usuario."""
    
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(f"Usuario con id {user_id} no encontrado")

class InvalidEmailError(DomainException):
    """Se lanza cuando el email es inválido."""
    pass

# ✓ Logging estruturado
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Usar:
logger.info(
    "Usuario creado",
    extra={
        "user_id": 123,
        "email": "user@example.com",
        "timestamp": datetime.now().isoformat()
    }
)
```

**❌ EVITAR:**

```python
# ✗ Sin type hints
def calculate_price(items):
    total = 0
    for item in items:
        total += item['price']
    return total

# ✗ Docstring incompleto
def process_data(data):
    """Procesa datos."""
    pass

# ✗ Manejo de excepciones genérico
try:
    result = some_operation()
except Exception:
    print("Error")

# ✗ Magic numbers
def discount(price):
    return price * 0.85  # ¿Qué es 0.85?

# ✗ Lógica de negocio en controlador
@app.post("/users")
def create_user(email: str, password: str):
    # Demasiada lógica aquí
    hashed = bcrypt.hash(password)
    user = User(email=email, password=hashed)
    db.add(user)
    db.commit()
    send_email(email)
    return {"status": "ok"}
```

### 3. Database Best Practices

```python
# ✓ CORRECTO: SQLAlchemy con type hints
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from datetime import datetime
from typing import Optional

Base = declarative_base()

class UserModel(Base):
    """Modelo de usuario en BD."""
    __tablename__ = "users"
    
    id: int = Column(Integer, primary_key=True)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    name: str = Column(String(255), nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

# ✓ Repository Pattern
from abc import ABC, abstractmethod

class UserRepository(ABC):
    """Interfaz para repositorio de usuarios."""
    
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene un usuario por ID."""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por email."""
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """Guarda un usuario."""
        pass

class SQLAlchemyUserRepository(UserRepository):
    """Implementación de repositorio con SQLAlchemy."""
    
    def __init__(self, session: Session) -> None:
        self.session = session
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = self.session.query(UserModel).filter(
            UserModel.id == user_id
        ).first()
        return self._map_to_domain(result) if result else None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = self.session.query(UserModel).filter(
            UserModel.email == email
        ).first()
        return self._map_to_domain(result) if result else None
    
    async def save(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            name=user.name
        )
        self.session.add(model)
        self.session.commit()
        user.id = model.id
        return user
    
    @staticmethod
    def _map_to_domain(model: UserModel) -> User:
        """Mapea modelo BD a entidad de dominio."""
        return User(
            id=model.id,
            email=model.email,
            name=model.name
        )

# ✓ Query optimization
def get_users_with_posts(session: Session) -> List[User]:
    """Obtiene usuarios con sus posts (evita N+1)."""
    from sqlalchemy.orm import joinedload
    
    return session.query(UserModel).options(
        joinedload(UserModel.posts)
    ).all()

# ✓ Connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_recycle=3600,  # Reciclar conexiones cada hora
    echo=False
)
```

### 4. FastAPI Best Practices

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from typing import Annotated
import logging

# ✓ App configuration
app = FastAPI(
    title="Mi API",
    version="1.0.0",
    description="API RESTful profesional"
)

# ✓ CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ✓ Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com", "*.example.com"]
)

# ✓ Custom exception handler
class APIException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

@app.exception_handler(APIException)
async def api_exception_handler(request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )

# ✓ Dependency Injection
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """Obtiene el usuario actual del token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    
    user = await user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401)
    return user

# ✓ Endpoint bien estructurado
@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_create: UserCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
) -> UserResponse:
    """Crea un nuevo usuario.
    
    - **email**: Email único del usuario
    - **name**: Nombre completo
    
    Returns:
        UserResponse: Usuario creado
        
    Raises:
        HTTPException: Si el email ya existe (400)
        HTTPException: Si no está autenticado (401)
    """
    # Verificar que el usuario tenga permisos
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    
    # Verificar que el email no exista
    existing = await user_repository.get_by_email(user_create.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="El email ya está registrado"
        )
    
    # Crear usuario
    new_user = User(
        email=user_create.email,
        name=user_create.name
    )
    saved_user = await user_repository.save(new_user)
    
    return UserResponse.model_validate(saved_user)

# ✓ Versionado de API
@app.get("/api/v1/users/{user_id}")
async def get_user_v1(user_id: int):
    """API v1 endpoint."""
    pass

@app.get("/api/v2/users/{user_id}")
async def get_user_v2(user_id: int):
    """API v2 endpoint con cambios."""
    pass
```

### 5. Testing Best Practices

```python
# ✓ pytest configuration (conftest.py)
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def db_session():
    """Proporciona una sesión de BD para tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_user():
    """Proporciona un usuario de test."""
    return User(
        id=1,
        email="test@example.com",
        name="Test User"
    )

# ✓ Unit tests
from unittest.mock import Mock, patch, MagicMock

def test_calculate_total_price():
    """Test para función de cálculo."""
    items = [
        {'price': 100, 'quantity': 2},
        {'price': 50, 'quantity': 1}
    ]
    total = calculate_total_price(items, tax_rate=0.1)
    assert total == 275.0  # (100*2 + 50) * 1.1

def test_calculate_total_price_with_discount():
    """Test con descuento."""
    items = [{'price': 100, 'quantity': 1}]
    total = calculate_total_price(items, discount_percentage=10)
    assert total == 90.0

def test_user_not_found_error():
    """Test de excepción personalizada."""
    with pytest.raises(UserNotFoundError) as exc_info:
        raise UserNotFoundError(999)
    assert exc_info.value.user_id == 999

# ✓ Integration tests
@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test de integración para crear usuario."""
    repository = SQLAlchemyUserRepository(db_session)
    
    user = User(
        email="new@example.com",
        name="New User"
    )
    
    saved_user = await repository.save(user)
    
    assert saved_user.id is not None
    assert saved_user.email == "new@example.com"

# ✓ Mocking
@patch('requests.get')
def test_external_api_call(mock_get):
    """Test con mock de llamada externa."""
    mock_get.return_value.json.return_value = {'id': 1, 'name': 'User'}
    
    result = fetch_external_user(1)
    
    assert result['id'] == 1
    mock_get.assert_called_once()
```

---

## 📘 TYPESCRIPT BEST PRACTICES

### 1. TSConfig Strict

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM"],
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "allowUnusedLabels": false,
    "allowUnreachableCode": false,
    "exactOptionalPropertyTypes": true,
    
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@hooks/*": ["src/hooks/*"],
      "@utils/*": ["src/utils/*"],
      "@types/*": ["src/types/*"]
    }
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

### 2. Type Definitions

```typescript
// ✓ CORRECTO: Tipos bien definidos

// types/index.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export type UserRole = 'admin' | 'user' | 'moderator';

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
}

export interface UserResponse extends User {
  // No incluir password
}

// Utility types
export type UserWithoutPassword = Omit<User, 'password'>;
export type PartialUser = Partial<User>;
export type UserProfile = Pick<User, 'id' | 'name' | 'email'>;

// ✓ Discriminated unions
export type ApiResponse<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; error: string; code: number }
  | { status: 'loading' };

// ✓ Generic types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface Result<T, E = Error> {
  ok: true;
  value: T;
} | {
  ok: false;
  error: E;
}

// ✓ Type guards
export function isUser(obj: unknown): obj is User {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'email' in obj &&
    'name' in obj
  );
}

// ✓ Const assertions
export const USER_ROLES = ['admin', 'user', 'moderator'] as const;
export type UserRoleType = typeof USER_ROLES[number];
```

### 3. Code Patterns

```typescript
// ✓ Validación de tipos
function validateEmail(email: string): email is string {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ✓ Type narrowing
function handleApiResponse(response: ApiResponse<User>): void {
  switch (response.status) {
    case 'success':
      console.log('Usuario:', response.data);
      break;
    case 'error':
      console.error(`Error ${response.code}: ${response.error}`);
      break;
    case 'loading':
      console.log('Cargando...');
      break;
  }
}

// ✓ Async/Await con tipos
async function fetchUser(userId: string): Promise<Result<User>> {
  try {
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) {
      return {
        ok: false,
        error: new Error(`HTTP ${response.status}`)
      };
    }
    const data = await response.json();
    return { ok: true, value: data };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error : new Error('Unknown error')
    };
  }
}

// ✓ Nullish coalescing y optional chaining
const userName = user?.profile?.name ?? 'Anonymous';
const age = user?.age ?? 0;

// ✓ Type-safe event handlers
interface FormEvent extends React.FormEvent<HTMLFormElement> {
  currentTarget: HTMLFormElement & {
    elements: {
      email: HTMLInputElement;
      password: HTMLInputElement;
    };
  };
}

function handleSubmit(event: FormEvent): void {
  const { email, password } = event.currentTarget.elements;
  console.log(email.value, password.value);
}

// ✓ Class con tipos
abstract class BaseRepository<T> {
  protected abstract tableName: string;

  async findById(id: string): Promise<T | null> {
    // implementación
    return null;
  }

  async create(data: Partial<T>): Promise<T> {
    // implementación
    throw new Error('Not implemented');
  }
}

class UserRepository extends BaseRepository<User> {
  protected tableName = 'users';
  
  override async findById(id: string): Promise<User | null> {
    // implementación específica
    return null;
  }
}
```

### 4. React + TypeScript

```typescript
// ✓ Props bien tipadas
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, children, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        className={`btn btn-${variant} btn-${size}`}
        disabled={isLoading}
        {...rest}
      >
        {isLoading ? 'Loading...' : children}
      </button>
    );
  }
);

Button.displayName = 'Button';

// ✓ Hook tipado
function useAsync<T, E = string>(
  asyncFunction: () => Promise<T>,
  immediate = true
): { status: 'idle' | 'pending' | 'success' | 'error'; value?: T; error?: E } {
  const [status, setStatus] = React.useState<'idle' | 'pending' | 'success' | 'error'>('idle');
  const [value, setValue] = React.useState<T | undefined>();
  const [error, setError] = React.useState<E | undefined>();

  const execute = React.useCallback(async () => {
    setStatus('pending');
    setValue(undefined);
    setError(undefined);
    try {
      const response = await asyncFunction();
      setValue(response);
      setStatus('success');
      return response;
    } catch (error) {
      setError(error as E);
      setStatus('error');
    }
  }, [asyncFunction]);

  React.useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate]);

  return { status, value, error };
}

// Uso:
const MyComponent: React.FC = () => {
  const { status, value, error } = useAsync(
    () => fetch('/api/users').then(r => r.json()),
    true
  );

  return (
    <div>
      {status === 'pending' && <p>Cargando...</p>}
      {status === 'success' && <p>Datos: {value}</p>}
      {status === 'error' && <p>Error: {error}</p>}
    </div>
  );
};

// ✓ Context API tipado
interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

function useAuth(): AuthContextType {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de AuthProvider');
  }
  return context;
}

// ✓ Testing tipado
import { render, screen } from '@testing-library/react';

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
  });

  it('calls onClick handler', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    screen.getByRole('button').click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

---

## 🚀 ASTRO BEST PRACTICES

### 1. Astro Config Óptimo

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import sitemap from '@astrojs/sitemap';
import compress from 'astro-compress';

export default defineConfig({
  site: 'https://example.com',
  
  // ✓ Output mode
  output: 'hybrid', // SSR + SSG
  
  // ✓ Integrations
  integrations: [
    react(),
    tailwind({
      applyBaseStyles: false,
    }),
    sitemap(),
    compress(),
  ],

  // ✓ Vite config
  vite: {
    ssr: {
      external: ['sharp']
    }
  },

  // ✓ Performance
  image: {
    service: { entrypoint: 'astro/assets/services/sharp' },
    remotePatterns: [{
      protocol: 'https',
      hostname: '**.example.com'
    }]
  },

  // ✓ Markdown
  markdown: {
    syntaxHighlight: 'shiki',
    shikiConfig: {
      theme: 'github-dark',
      wrap: true,
    },
    rehypePlugins: [],
    remarkPlugins: [],
  },
});
```

### 2. Estructura de Proyecto

```
src/
├── components/          # Componentes Astro/React
│   ├── ui/             # Componentes UI reutilizables
│   │   ├── Button.astro
│   │   ├── Card.astro
│   │   └── Navigation.astro
│   ├── Layout/
│   │   ├── Header.astro
│   │   ├── Footer.astro
│   │   └── Sidebar.astro
│   └── Forms/
│       ├── LoginForm.tsx
│       └── SearchForm.tsx
├── layouts/            # Layouts base
│   ├── BaseLayout.astro
│   ├── BlogLayout.astro
│   └── DocsLayout.astro
├── pages/              # File-based routing
│   ├── index.astro
│   ├── about.astro
│   ├── blog/
│   │   ├── index.astro
│   │   └── [slug].astro
│   └── api/
│       └── users.ts
├── assets/
│   ├── images/
│   ├── styles/
│   │   └── global.css
│   └── fonts/
├── lib/
│   ├── api.ts
│   ├── utils.ts
│   └── constants.ts
└── types/
    └── index.ts
```

### 3. Componentes Astro

```astro
---
// ✓ Tipado de props
interface Props {
  title: string;
  description?: string;
  featured?: boolean;
}

const { title, description, featured = false } = Astro.props;
const id = Astro.url.searchParams.get('id');

// ✓ Lógica de servidor
const posts = await Astro.glob('../pages/blog/*.md');
const recentPosts = posts.slice(0, 3);

// ✓ Propiedades dinámicas
const headings = [
  { level: 2, text: 'Introducción' },
  { level: 3, text: 'Getting Started' },
];
---

<div class="card">
  <h1>{title}</h1>
  {description && <p>{description}</p>}
  {featured && <span class="badge">Featured</span>}
  
  <slot />
</div>

<style>
  .card {
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
  }
  
  .badge {
    background-color: #ffd700;
    padding: 0.25rem 0.5rem;
  }
</style>
```

### 4. Islands Architecture

```astro
---
// pages/index.astro - Principalmente estático
import Counter from '../components/Counter.tsx';
import SearchForm from '../components/SearchForm.tsx';
---

<Layout>
  <h1>Mi Sitio</h1>
  
  <!-- Static HTML -->
  <p>Este contenido es estático y se sirve sin JavaScript</p>
  
  <!-- Interactive Island (React) -->
  <Counter client:load />
  
  <!-- Island que carga en idle -->
  <SearchForm client:idle />
</Layout>
```

```typescript
// components/Counter.tsx - Island interactivo
import { useState } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>Contador: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Incrementar
      </button>
    </div>
  );
}
```

### 5. Performance Optimization

```astro
---
// ✓ Optimizar imágenes
import { Image } from 'astro:assets';
import myImage from '../assets/my-image.png';

// ✓ Preload recursos críticos
import { preload } from 'astro:elements';
preload('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700');
---

<Image
  src={myImage}
  alt="Descripción importante"
  widths={[200, 400, 800]}
  sizes="(max-width: 640px) 200px, (max-width: 1024px) 400px, 800px"
/>

<!-- ✓ DNS prefetch -->
<link rel="dns-prefetch" href="https://api.example.com" />

<!-- ✓ Preconnect -->
<link rel="preconnect" href="https://cdn.example.com" />

<!-- ✓ Resource hints -->
<link rel="prefetch" href="/api/users" />
```

---

## 🏛️ ARQUITECTURA DEL PROYECTO

### Arquitectura Recomendada: Clean Architecture + DDD

```
proyecto/
├── 📁 Domain (Lógica de negocio pura)
│   ├── entities/
│   │   └── User.ts
│   ├── value-objects/
│   │   └── Email.ts
│   ├── repositories/
│   │   └── IUserRepository.ts
│   └── services/
│       └── UserDomainService.ts
│
├── 📁 Application (Casos de uso)
│   ├── use-cases/
│   │   ├── CreateUser/
│   │   │   ├── CreateUserUseCase.ts
│   │   │   ├── CreateUserInput.ts
│   │   │   └── CreateUserOutput.ts
│   │   └── GetUser/
│   ├── dtos/
│   │   └── UserDTO.ts
│   └── services/
│       └── UserApplicationService.ts
│
├── 📁 Infrastructure (Detalles técnicos)
│   ├── database/
│   │   ├── models/
│   │   │   └── UserModel.ts
│   │   ├── repositories/
│   │   │   └── SqlUserRepository.ts
│   │   └── migrations/
│   ├── api/
│   │   ├── client.ts
│   │   └── endpoints.ts
│   └── config/
│       └── database.ts
│
└── 📁 Presentation (API/UI)
    ├── controllers/
    │   └── UserController.ts
    ├── routes/
    │   └── users.ts
    ├── middleware/
    │   ├── auth.ts
    │   └── error-handling.ts
    └── schemas/
        └── user-schema.ts
```

### Dependency Injection

```typescript
// ✓ Container de DI
class DIContainer {
  private services = new Map<string, any>();

  register<T>(name: string, factory: () => T): void {
    this.services.set(name, factory);
  }

  resolve<T>(name: string): T {
    const factory = this.services.get(name);
    if (!factory) {
      throw new Error(`Service ${name} not registered`);
    }
    return factory();
  }
}

// Uso:
const container = new DIContainer();

container.register('userRepository', () => new SqlUserRepository(db));
container.register('userService', () => 
  new UserApplicationService(container.resolve('userRepository'))
);

const userService = container.resolve('userService');
```

---

## 🎨 UI/UX DESIGN PATTERNS

### Design System con Tailwind

```tailwind.config.js
module.exports = {
  content: ['./src/**/*.{astro,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#0ea5e9',
          900: '#0c4a6e',
        },
        secondary: {
          50: '#f8fafc',
          500: '#64748b',
          900: '#1e293b',
        },
      },
      spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
        xl: '2rem',
      },
      borderRadius: {
        xs: '0.25rem',
        sm: '0.375rem',
        md: '0.5rem',
        lg: '0.75rem',
      },
      typography: {
        DEFAULT: {
          css: {
            color: '#1e293b',
          }
        }
      }
    },
  },
};
```

### Component Library Pattern

```typescript
// Button component variations
type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

const buttonVariants = {
  primary: 'bg-blue-500 text-white hover:bg-blue-600',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
  outline: 'border-2 border-blue-500 text-blue-500 hover:bg-blue-50',
  ghost: 'text-blue-500 hover:bg-blue-50',
};

const buttonSizes = {
  sm: 'px-3 py-1 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};
```

---

## ⚡ PERFORMANCE & SCALABILITY

### Frontend Performance Checklist

```javascript
// ✓ Code splitting
import { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HeavyComponent />
    </Suspense>
  );
}

// ✓ Image optimization
<img 
  srcSet="image-200w.jpg 200w, image-400w.jpg 400w"
  sizes="(max-width: 600px) 200px, 400px"
  src="image-400w.jpg"
  alt="Description"
  loading="lazy"
/>

// ✓ Web Vitals monitoring
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function onPerfEntry(metric) {
  if (metric.value < thresholds[metric.name]) {
    console.log(metric);
  }
}

getCLS(onPerfEntry);
getFID(onPerfEntry);
getFCP(onPerfEntry);
getLCP(onPerfEntry);
getTTFB(onPerfEntry);
```

### Backend Performance Checklist

```python
# ✓ Query optimization
from sqlalchemy import select
from sqlalchemy.orm import joinedload

# ✗ Evitar N+1 queries
users = db.query(User).all()
for user in users:
    print(user.posts)  # N queries adicionales!

# ✓ Usar eager loading
users = db.query(User).options(joinedload(User.posts)).all()

# ✓ Pagination
@app.get("/users")
async def list_users(skip: int = 0, limit: int = 10):
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    return {"users": users, "total": total}

# ✓ Caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_settings(user_id: int) -> Dict:
    return query_settings_from_db(user_id)

# ✓ Async operations
import asyncio

async def process_multiple_items(items: List[int]):
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)
```

---

## 📊 RESUMEN DE MÉTRICAS ESPERADAS

| Métrica | Target | Tool |
|---------|--------|------|
| TypeScript strict | 100% | `tsconfig.json` |
| Test coverage | >= 80% | Jest/pytest |
| Lighthouse | >= 90 | Lighthouse CLI |
| LCP (Core Web Vitals) | < 2.5s | PageSpeed Insights |
| Type errors | 0 | mypy/tsc |
| Linting errors | 0 | ESLint/Flake8 |
| Security vulnerabilities | 0 | npm audit |
| Code duplication | < 3% | SonarQube |

---

**Última actualización:** 2026-05-01
