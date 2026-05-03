#
# Dockerfile para SRT2Web
# Multi-stage build para reducir tamaño de imagen final
#

# -----------------------------------------------------------------------------
# Etapa 1: Builder - Instalación de dependencias y build frontend
# -----------------------------------------------------------------------------
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    python3.12-venv \
    nodejs \
    npm \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip3.12 install --no-cache-dir -r requirements.txt

# Instalar dependencias del frontend y build
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci

COPY frontend/ frontend/
RUN cd frontend && npm run build:local

# -----------------------------------------------------------------------------
# Etapa 2: Runtime - Imagen final para ejecución
# -----------------------------------------------------------------------------
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

WORKDIR /app

# Instalar dependencias mínimas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias de Python
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar build del frontend
COPY --from=builder /app/frontend/dist /app/server/static

# Copiar código fuente
COPY . .

# Exponer puertos
EXPOSE 9000/udp  # SRT
EXPOSE 9999/tcp  # Web UI / API / HLS

# Volúmenes para configuración y logs
VOLUME [ "/app/config", "/app/logs", "/app/output" ]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9999/health || exit 1

# Comando de inicio
ENTRYPOINT [ "python3", "main.py" ]