"""
RagBot FastAPI Main Application
Medical biomarker analysis API
"""

import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app import __version__
from app.routes import health, biomarkers, analyze
from app.services.ragbot import get_ragbot_service


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Initializes RagBot service on startup (loads vector store, models).
    """
    logger.info("=" * 70)
    logger.info("Starting RagBot API Server")
    logger.info("=" * 70)
    
    # Startup: Initialize RagBot service
    try:
        ragbot_service = get_ragbot_service()
        ragbot_service.initialize()
        logger.info("RagBot service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RagBot service: {e}")
        logger.warning("API will start but health checks will fail")
    
    logger.info("API server ready to accept requests")
    logger.info("=" * 70)
    
    yield  # Server runs here
    
    # Shutdown
    logger.info("Shutting down RagBot API Server")


# ============================================================================
# CREATE APPLICATION
# ============================================================================

app = FastAPI(
    title="RagBot API",
    description="Medical biomarker analysis using RAG and multi-agent workflow",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

# CORS configuration — restrict to known origins in production
_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allowed_origins != ["*"],  # credentials only with explicit origins
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors — never leak internal details to the client."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

# Register all route modules
app.include_router(health.router)
app.include_router(biomarkers.router)
app.include_router(analyze.router)


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "RagBot API",
        "version": __version__,
        "description": "Medical biomarker analysis using RAG and multi-agent workflow",
        "status": "online",
        "endpoints": {
            "health": "/api/v1/health",
            "biomarkers": "/api/v1/biomarkers",
            "analyze_natural": "/api/v1/analyze/natural",
            "analyze_structured": "/api/v1/analyze/structured",
            "example": "/api/v1/example",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        }
    }


@app.get("/api/v1")
async def api_v1_info():
    """API v1 information"""
    return {
        "version": "1.0",
        "endpoints": [
            "GET /api/v1/health",
            "GET /api/v1/biomarkers",
            "POST /api/v1/analyze/natural",
            "POST /api/v1/analyze/structured",
            "GET /api/v1/example"
        ]
    }


# ============================================================================
# RUN CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
