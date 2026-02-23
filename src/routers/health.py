"""
MediGuard AI — Health Router

Provides /health and /health/ready with per-service checks.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from src.schemas.schemas import HealthResponse, ServiceHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Shallow liveness probe."""
    app_state = request.app.state
    uptime = time.time() - getattr(app_state, "start_time", time.time())
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=getattr(app_state, "version", "2.0.0"),
        uptime_seconds=round(uptime, 2),
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check(request: Request) -> HealthResponse:
    """Deep readiness probe — checks all backing services."""
    app_state = request.app.state
    uptime = time.time() - getattr(app_state, "start_time", time.time())
    services: list[ServiceHealth] = []
    overall = "healthy"

    # --- OpenSearch ---
    try:
        os_client = getattr(app_state, "opensearch_client", None)
        if os_client is not None:
            t0 = time.time()
            info = os_client.health()
            latency = (time.time() - t0) * 1000
            os_status = info.get("status", "unknown")
            services.append(ServiceHealth(name="opensearch", status="ok" if os_status in ("green", "yellow") else "degraded", latency_ms=round(latency, 1)))
        else:
            services.append(ServiceHealth(name="opensearch", status="unavailable"))
    except Exception as exc:
        services.append(ServiceHealth(name="opensearch", status="unavailable", detail=str(exc)))
        overall = "degraded"

    # --- Redis ---
    try:
        cache = getattr(app_state, "cache", None)
        if cache is not None:
            t0 = time.time()
            cache.set("__health__", "ok", ttl=10)
            latency = (time.time() - t0) * 1000
            services.append(ServiceHealth(name="redis", status="ok", latency_ms=round(latency, 1)))
        else:
            services.append(ServiceHealth(name="redis", status="unavailable"))
    except Exception as exc:
        services.append(ServiceHealth(name="redis", status="unavailable", detail=str(exc)))

    # --- Ollama ---
    try:
        ollama = getattr(app_state, "ollama_client", None)
        if ollama is not None:
            t0 = time.time()
            healthy = ollama.health()
            latency = (time.time() - t0) * 1000
            services.append(ServiceHealth(name="ollama", status="ok" if healthy else "degraded", latency_ms=round(latency, 1)))
        else:
            services.append(ServiceHealth(name="ollama", status="unavailable"))
    except Exception as exc:
        services.append(ServiceHealth(name="ollama", status="unavailable", detail=str(exc)))
        overall = "degraded"

    # --- Langfuse ---
    try:
        tracer = getattr(app_state, "tracer", None)
        if tracer is not None:
            services.append(ServiceHealth(name="langfuse", status="ok"))
        else:
            services.append(ServiceHealth(name="langfuse", status="unavailable"))
    except Exception as exc:
        services.append(ServiceHealth(name="langfuse", status="unavailable", detail=str(exc)))

    if any(s.status == "unavailable" for s in services if s.name in ("opensearch", "ollama")):
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=getattr(app_state, "version", "2.0.0"),
        uptime_seconds=round(uptime, 2),
        services=services,
    )
