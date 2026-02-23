# ===========================================================================
# MediGuard AI — Multi-stage Dockerfile
# ===========================================================================
# Build stages:
#   base        — Python + system deps
#   production  — slim runtime image
# ===========================================================================

# ---------------------------------------------------------------------------
# Stage 1: base
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install ".[all]"

# ---------------------------------------------------------------------------
# Stage 2: production
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from base
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mediguard && \
    useradd -r -g mediguard -d /app -s /sbin/nologin mediguard && \
    chown -R mediguard:mediguard /app

USER mediguard

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
