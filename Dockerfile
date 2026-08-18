#
# Dockerfile para SRT2Web — Multi-stage, <500MB, multi-platform
#
# Build:    docker build -t srt2web .
# Run:      docker run -p 9999:9999 -p 9000:9000/udp srt2web
#
# GPU:      docker build --build-arg BASE_IMAGE=nvidia/cuda:12.6.3-runtime-ubuntu24.04 .
#

# -----------------------------------------------------------------------------
# Argumentos de build
# -----------------------------------------------------------------------------
ARG BASE_IMAGE=python:3.12-slim
# CUDA runtime with python3.12 available in default repos (ubuntu 24.04
# noble ships python3.12; jammy did not — apt install python3.12 failed with
# exit 100). 12.6.3 is the oldest CUDA tag with both amd64+arm64 manifests.
ARG CUDA_IMAGE=nvidia/cuda:12.6.3-runtime-ubuntu24.04

# -----------------------------------------------------------------------------
# Etapa 1: Builder — dependencias Python + build frontend
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Node 22 LTS via official tarball: Debian trixie ships node 20, which Astro
# rejects ("Node.js v20.x is not supported by Astro! >=22.12.0 required").
ARG TARGETARCH=amd64
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-${TARGETARCH}.tar.gz" -o /tmp/node.tar.gz \
    && tar -xzf /tmp/node.tar.gz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.gz

COPY config/requirements.txt config/
RUN pip install --no-cache-dir -r config/requirements.txt

COPY frontend/package*.json frontend/
RUN cd frontend && npm ci

COPY frontend/ frontend/
RUN cd frontend && ASTRO_TELEMETRY_DISABLED=1 npx astro build --outDir ../server/static

RUN python -m mkdocs build -f docs/mkdocs.yml --site-dir /app/server/static/docs 2>/dev/null || echo "Docs build skipped (mkdocs not available)"

# -----------------------------------------------------------------------------
# Etapa 2: Runtime — imagen mínima de ejecución
# -----------------------------------------------------------------------------
FROM ${BASE_IMAGE} AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# F117 fix: Astro builds to --outDir ../server/static (relative to frontend/)
COPY --from=builder /app/server/static /app/server/static

COPY . .

EXPOSE 9000/udp
EXPOSE 9999/tcp

VOLUME [ "/app/config", "/app/logs", "/app/output" ]

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9999/health')" || exit 1

ENTRYPOINT [ "python3", "main.py" ]

# -----------------------------------------------------------------------------
# Etapa 3: Runtime con GPU CUDA (alternativa)
# -----------------------------------------------------------------------------
FROM ${CUDA_IMAGE} AS runtime-cuda

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
ENV CUDA_VISIBLE_DEVICES=0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# F117 fix: builder is python:3.12-slim which uses site-packages, not dist-packages
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/server/static /app/server/static

COPY . .
RUN rm -rf /app/tests /app/frontend /app/.github

EXPOSE 9000/udp
EXPOSE 9999/tcp

VOLUME [ "/app/config", "/app/logs", "/app/output" ]

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9999/health')" || exit 1

ENTRYPOINT [ "python3", "main.py" ]
