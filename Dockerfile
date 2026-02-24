# ===========================================================================
# MediGuard AI — Multi-Stage Dockerfile
# ===========================================================================
# Supports both HuggingFace Spaces deployment and Docker Compose production.
#
# Usage:
#   HuggingFace Spaces: docker build -t mediguard .
#   Production API:     docker build -t mediguard --target production .
# ===========================================================================

# ---------------------------------------------------------------------------
# Base stage — common dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

# Non-interactive apt
ENV DEBIAN_FRONTEND=noninteractive

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./requirements.txt
COPY huggingface/requirements.txt ./huggingface-requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p data/medical_pdfs data/vector_stores data/chat_reports


# ---------------------------------------------------------------------------
# Production stage — FastAPI server with uvicorn
# ---------------------------------------------------------------------------
FROM base AS production

# Production settings
ENV API_PORT=8000 \
    WORKERS=4

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser
ENV HOME=/home/appuser \
    PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]


# ---------------------------------------------------------------------------
# HuggingFace stage — Gradio app (default)
# ---------------------------------------------------------------------------
FROM base AS huggingface

# HuggingFace Spaces runs on port 7860
ENV GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    EMBEDDING_PROVIDER=huggingface

# Install HuggingFace-specific requirements
RUN pip install -r huggingface-requirements.txt

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 user && \
    chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:7860/ || exit 1

# Launch Gradio app
CMD ["python", "huggingface/app.py"]

# Default to HuggingFace stage for HF Spaces (no target specified)
FROM huggingface
