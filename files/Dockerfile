# ─── Stage 1: Frontend build ─────────────────────────────────────────────────
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --only=production=false

COPY frontend/ .
RUN npm run build


# ─── Stage 2: Python dependencies ────────────────────────────────────────────
FROM python:3.11-slim AS python-deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install poetry==1.7.0
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --without dev --output requirements.txt
RUN pip install --prefix=/install -r requirements.txt


# ─── Stage 3: Final image ─────────────────────────────────────────────────────
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="Mi Proyecto"
LABEL org.opencontainers.image.version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copiar dependencias Python
COPY --from=python-deps /install /usr/local

# Copiar código fuente
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Copiar frontend compilado (para servir estáticos si aplica)
COPY --from=frontend-builder /app/frontend/dist/ static/

# Cambiar a usuario no-root
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["uvicorn", "src.presentation.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
