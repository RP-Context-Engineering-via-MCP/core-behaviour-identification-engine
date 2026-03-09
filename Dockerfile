# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — install heavy dependencies (torch, transformers, etc.)
# Requires BuildKit (default in Docker 23+).  If using older Docker, run:
#   DOCKER_BUILDKIT=1 docker compose -f docker-compose.cbie.yml up --build
# ─────────────────────────────────────────────────────────────────────────────
# syntax=docker/dockerfile:1
FROM python:3.10-slim AS builder

WORKDIR /app

# System packages needed to compile numpy / scipy extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first so Docker can cache pip install layer
COPY requirements.txt .

# Install all Python deps with a persistent BuildKit cache mount.
# The /root/.cache/pip directory is reused across builds — packages are
# NEVER re-downloaded unless requirements.txt changes.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt && \
    # Download spaCy model into same layer to keep it cached together
    PYTHONPATH=/install/lib/python3.10/site-packages \
    python -m spacy download en_core_web_sm --target /install/lib/python3.10/site-packages

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — lean final image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (only what's needed — .dockerignore keeps this tiny)
COPY . .

# Ensure the data/profiles directory exists at runtime
RUN mkdir -p /app/data/profiles

# Port exposed by uvicorn
EXPOSE 6009

# Start FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "6009"]
