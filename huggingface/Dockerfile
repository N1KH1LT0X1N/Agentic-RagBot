# ===========================================================================
# MediGuard AI — Hugging Face Spaces Dockerfile
# ===========================================================================
# Optimized single-container deployment for Hugging Face Spaces.
# Uses FAISS vector store + Cloud LLMs (Groq/Gemini) - no external services.
# ===========================================================================

FROM python:3.11-slim

# Non-interactive apt
ENV DEBIAN_FRONTEND=noninteractive

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# HuggingFace Spaces runs on port 7860
ENV GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860

# Default embedding provider (can be overridden by HF Secrets)
# Options: huggingface (local, no key needed), google, jina
ENV EMBEDDING_PROVIDER=huggingface

# Disable HF hub implicit token warning
ENV HF_HUB_DISABLE_IMPLICIT_TOKEN=1

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY huggingface/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the entire project
COPY . .

# Create necessary directories and ensure vector store exists
RUN mkdir -p data/medical_pdfs data/vector_stores data/chat_reports

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 user

# Make app writable by user
RUN chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:7860/ || exit 1

# Launch Gradio app
CMD ["python", "huggingface/app.py"]
