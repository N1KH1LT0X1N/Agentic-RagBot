# RagBot API - Multi-stage Docker Build

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# STAGE 1: Install RagBot core dependencies
# ============================================================================
FROM base as ragbot-deps

# Copy RagBot requirements
COPY ../requirements.txt /app/ragbot_requirements.txt

# Install RagBot dependencies
RUN pip install --no-cache-dir -r /app/ragbot_requirements.txt

# ============================================================================
# STAGE 2: Install API dependencies
# ============================================================================
FROM ragbot-deps as api-deps

# Copy API requirements
COPY requirements.txt /app/api_requirements.txt

# Install API dependencies
RUN pip install --no-cache-dir -r /app/api_requirements.txt

# ============================================================================
# STAGE 3: Build final image
# ============================================================================
FROM api-deps as final

# Copy entire RagBot source (needed for imports)
COPY ../ /app/ragbot/

# Set Python path to include RagBot
ENV PYTHONPATH=/app/ragbot:$PYTHONPATH

# Copy API application
COPY ./app /app/api/app

# Set working directory to API
WORKDIR /app/api

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
