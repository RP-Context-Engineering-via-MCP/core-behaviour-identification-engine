# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — install heavy dependencies (torch, transformers, etc.)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /app

# System packages needed to compile numpy / scipy extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first so Docker can cache pip install layer
COPY requirements.txt .

# Install all Python dependencies into a separate directory for clean copy
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# Also download the spaCy model into the install prefix
RUN python -m spacy download en_core_web_sm

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — lean final image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Ensure the data/profiles directory exists at runtime
RUN mkdir -p /app/data/profiles

# Port exposed by uvicorn
EXPOSE 6009

# Start FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "6009"]
