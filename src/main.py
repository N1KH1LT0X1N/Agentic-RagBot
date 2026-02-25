"""
MediGuard AI — Production FastAPI Application

Central app factory with lifespan that initialises all production services
(OpenSearch, Redis, Ollama, Langfuse, RAG pipeline) and gracefully shuts
them down.  The existing ``api/`` package is kept as-is — this new module
becomes the primary production entry-point.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.settings import get_settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("mediguard")

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise production services on startup, tear them down on shutdown."""
    settings = get_settings()
    app.state.start_time = time.time()
    app.state.version = "2.0.0"

    logger.info("=" * 70)
    logger.info("MediGuard AI — starting production server v%s", app.state.version)
    logger.info("=" * 70)

    # --- OpenSearch ---
    try:
        from src.services.opensearch.client import make_opensearch_client
        from src.services.opensearch.index_config import MEDICAL_CHUNKS_MAPPING
        app.state.opensearch_client = make_opensearch_client()
        app.state.opensearch_client.ensure_index(MEDICAL_CHUNKS_MAPPING)
        logger.info("OpenSearch client ready")
    except Exception as exc:
        logger.warning("OpenSearch unavailable: %s", exc)
        app.state.opensearch_client = None

    # --- Embedding service ---
    try:
        from src.services.embeddings.service import make_embedding_service
        app.state.embedding_service = make_embedding_service()
        logger.info("Embedding service ready (provider=%s)", app.state.embedding_service.provider_name)
    except Exception as exc:
        logger.warning("Embedding service unavailable: %s", exc)
        app.state.embedding_service = None

    # --- Redis cache ---
    try:
        from src.services.cache.redis_cache import make_redis_cache
        app.state.cache = make_redis_cache()
        logger.info("Redis cache ready")
    except Exception as exc:
        logger.warning("Redis cache unavailable: %s", exc)
        app.state.cache = None

    # --- Ollama LLM ---
    try:
        from src.services.ollama.client import make_ollama_client
        app.state.ollama_client = make_ollama_client()
        logger.info("Ollama client ready")
    except Exception as exc:
        logger.warning("Ollama client unavailable: %s", exc)
        app.state.ollama_client = None

    # --- Langfuse tracer ---
    try:
        from src.services.langfuse.tracer import make_langfuse_tracer
        app.state.tracer = make_langfuse_tracer()
        logger.info("Langfuse tracer ready")
    except Exception as exc:
        logger.warning("Langfuse tracer unavailable: %s", exc)
        app.state.tracer = None

    # --- Agentic RAG service ---
    try:
        from src.llm_config import get_llm
        from src.services.agents.agentic_rag import AgenticRAGService
        from src.services.agents.context import AgenticContext
        if app.state.opensearch_client and app.state.embedding_service:
            llm = get_llm()
            ctx = AgenticContext(
                llm=llm,
                embedding_service=app.state.embedding_service,
                opensearch_client=app.state.opensearch_client,
                cache=app.state.cache,
                tracer=app.state.tracer,
            )
            app.state.rag_service = AgenticRAGService(ctx)
            logger.info("Agentic RAG service ready")
        else:
            app.state.rag_service = None
            logger.warning("Agentic RAG service skipped — missing backing services (OpenSearch or Embedding)")
    except Exception as exc:
        logger.warning("Agentic RAG service failed: %s", exc)
        app.state.rag_service = None

    # --- Legacy RagBot service (backward-compatible /analyze) ---
    try:
        from src.workflow import create_guild
        guild = create_guild()
        app.state.ragbot_service = guild
        logger.info("RagBot service ready (ClinicalInsightGuild)")
    except Exception as exc:
        logger.warning("RagBot service unavailable: %s", exc)
        app.state.ragbot_service = None

    # --- Extraction service (for natural language input) ---
    try:
        from src.llm_config import get_llm
        from src.services.extraction.service import make_extraction_service
        try:
            llm = get_llm()
        except Exception as e:
            logger.warning("Failed to get LLM for extraction, will use fallback: %s", e)
            llm = None
        # If no LLM available, extraction will use regex fallback
        app.state.extraction_service = make_extraction_service(llm=llm)
        logger.info("Extraction service ready")
    except Exception as exc:
        logger.warning("Extraction service unavailable: %s", exc)
        app.state.extraction_service = None

    logger.info("All services initialised — ready to serve")
    logger.info("=" * 70)

    yield  # ---- server running ----

    logger.info("Shutting down MediGuard AI …")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MediGuard AI",
        description="Production medical biomarker analysis — agentic RAG + multi-agent workflow",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # --- CORS ---
    origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Security & HIPAA Compliance ---
    from src.middlewares import HIPAAAuditMiddleware, SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HIPAAAuditMiddleware)

    # --- Exception handlers ---
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def catch_all(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    # --- Routers ---
    from src.routers import analyze, ask, health, search

    app.include_router(health.router)
    app.include_router(analyze.router)
    app.include_router(ask.router)
    app.include_router(search.router)

    @app.get("/")
    async def root():
        return {
            "name": "MediGuard AI",
            "version": "2.0.0",
            "status": "online",
            "endpoints": {
                "health": "/health",
                "health_ready": "/health/ready",
                "analyze_natural": "/analyze/natural",
                "analyze_structured": "/analyze/structured",
                "ask": "/ask",
                "search": "/search",
                "docs": "/docs",
            },
        }

    return app


# Module-level app for ``uvicorn src.main:app``
app = create_app()
