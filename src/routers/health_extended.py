"""
Comprehensive health check endpoints for all services.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.llm_config import get_chat_model
from src.services.cache.redis_cache import make_redis_cache
from src.services.embeddings.service import make_embedding_service
from src.services.langfuse.tracer import make_langfuse_tracer
from src.services.ollama.client import make_ollama_client
from src.services.opensearch.client import make_opensearch_client
from src.workflow import create_guild

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    services: dict[str, dict[str, Any]]


class ServiceHealth(BaseModel):
    """Individual service health model."""
    status: str  # "healthy", "unhealthy", "degraded"
    message: str | None = None
    response_time_ms: float | None = None
    last_check: datetime
    details: dict[str, Any] = {}


class DetailedHealthStatus(BaseModel):
    """Detailed health status with all services."""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    services: dict[str, ServiceHealth]
    system: dict[str, Any]


async def check_opensearch_health() -> ServiceHealth:
    """Check OpenSearch service health."""
    start_time = datetime.utcnow()

    try:
        client = make_opensearch_client()

        # Check cluster health
        health = client._client.cluster.health()
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        if health["status"] == "green":
            status = "healthy"
            message = "Cluster is healthy"
        elif health["status"] == "yellow":
            status = "degraded"
            message = "Cluster has some warnings"
        else:
            status = "unhealthy"
            message = f"Cluster status: {health['status']}"

        return ServiceHealth(
            status=status,
            message=message,
            response_time_ms=response_time,
            last_check=start_time,
            details={
                "cluster_status": health["status"],
                "number_of_nodes": health["number_of_nodes"],
                "active_primary_shards": health["active_primary_shards"],
                "active_shards": health["active_shards"],
                "doc_count": client.doc_count()
            }
        )
    except Exception as e:
        logger.error(f"OpenSearch health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


async def check_redis_health() -> ServiceHealth:
    """Check Redis service health."""
    start_time = datetime.utcnow()

    try:
        cache = make_redis_cache()

        # Test set/get operation
        test_key = "health_check_test"
        test_value = str(datetime.utcnow())
        cache.set(test_key, test_value, ttl=10)
        retrieved = cache.get(test_key)
        cache.delete(test_key)

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        if retrieved == test_value:
            return ServiceHealth(
                status="healthy",
                message="Redis is responding",
                response_time_ms=response_time,
                last_check=start_time,
                details={"test_passed": True}
            )
        else:
            return ServiceHealth(
                status="unhealthy",
                message="Redis data mismatch",
                response_time_ms=response_time,
                last_check=start_time
            )
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


async def check_ollama_health() -> ServiceHealth:
    """Check Ollama service health."""
    start_time = datetime.utcnow()

    try:
        client = make_ollama_client()

        # List available models
        models = client.list_models()
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ServiceHealth(
            status="healthy",
            message=f"Ollama is responding with {len(models)} models",
            response_time_ms=response_time,
            last_check=start_time,
            details={
                "available_models": models[:5],  # Show first 5 models
                "total_models": len(models)
            }
        )
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


async def check_langfuse_health() -> ServiceHealth:
    """Check Langfuse service health."""
    start_time = datetime.utcnow()

    try:
        tracer = make_langfuse_tracer()

        # Test trace creation
        test_trace = tracer.trace(
            name="health_check",
            input={"test": True},
            metadata={"health_check": True}
        )
        test_trace.update(output={"status": "ok"})

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ServiceHealth(
            status="healthy",
            message="Langfuse tracer is working",
            response_time_ms=response_time,
            last_check=start_time,
            details={"trace_created": True}
        )
    except Exception as e:
        logger.error(f"Langfuse health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


async def check_embedding_service_health() -> ServiceHealth:
    """Check embedding service health."""
    start_time = datetime.utcnow()

    try:
        service = make_embedding_service()

        # Test embedding generation
        test_text = "Health check test"
        embedding = service.embed_query(test_text)

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        if embedding and len(embedding) > 0:
            return ServiceHealth(
                status="healthy",
                message=f"Embedding service working (dim={len(embedding)})",
                response_time_ms=response_time,
                last_check=start_time,
                details={
                    "provider": service.provider_name,
                    "embedding_dimension": len(embedding)
                }
            )
        else:
            return ServiceHealth(
                status="unhealthy",
                message="No embedding generated",
                response_time_ms=response_time,
                last_check=start_time
            )
    except Exception as e:
        logger.error(f"Embedding service health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


async def check_llm_health() -> ServiceHealth:
    """Check LLM service health."""
    start_time = datetime.utcnow()

    try:
        llm = get_chat_model()

        # Test simple completion
        response = llm.invoke("Say 'OK'")
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        if response and "OK" in str(response):
            return ServiceHealth(
                status="healthy",
                message="LLM is responding",
                response_time_ms=response_time,
                last_check=start_time,
                details={
                    "model": llm.model_name,
                    "provider": getattr(llm, 'provider', 'unknown')
                }
            )
        else:
            return ServiceHealth(
                status="degraded",
                message="LLM response unexpected",
                response_time_ms=response_time,
                last_check=start_time
            )
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


async def check_workflow_health() -> ServiceHealth:
    """Check workflow service health."""
    start_time = datetime.utcnow()

    try:
        guild = create_guild()

        # Test workflow initialization
        if hasattr(guild, 'workflow') and guild.workflow:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ServiceHealth(
                status="healthy",
                message="Workflow initialized successfully",
                response_time_ms=response_time,
                last_check=start_time,
                details={
                    "agents_count": len(guild.__dict__) - 1,  # Subtract workflow
                    "workflow_compiled": True
                }
            )
        else:
            return ServiceHealth(
                status="unhealthy",
                message="Workflow not initialized",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                last_check=start_time
            )
    except Exception as e:
        logger.error(f"Workflow health check failed: {e}")
        return ServiceHealth(
            status="unhealthy",
            message=str(e),
            response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            last_check=start_time
        )


def get_app_state(request):
    """Get application state for uptime calculation."""
    return request.app.state


@router.get("/", response_model=HealthStatus)
async def health_check(request, app_state=Depends(get_app_state)):
    """Basic health check endpoint."""
    uptime = datetime.utcnow().timestamp() - app_state.start_time

    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=app_state.version,
        uptime_seconds=uptime,
        services={
            "api": {"status": "healthy"}
        }
    )


@router.get("/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check(request, app_state=Depends(get_app_state)):
    """Detailed health check for all services."""
    uptime = datetime.utcnow().timestamp() - app_state.start_time

    # Check all services concurrently
    services = {
        "opensearch": await check_opensearch_health(),
        "redis": await check_redis_health(),
        "ollama": await check_ollama_health(),
        "langfuse": await check_langfuse_health(),
        "embedding_service": await check_embedding_service_health(),
        "llm": await check_llm_health(),
        "workflow": await check_workflow_health()
    }

    # Determine overall status
    unhealthy_count = sum(1 for s in services.values() if s.status == "unhealthy")
    degraded_count = sum(1 for s in services.values() if s.status == "degraded")

    if unhealthy_count > 0:
        overall_status = "unhealthy"
    elif degraded_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # System information
    import os

    import psutil

    system_info = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
        "process_id": os.getpid(),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
    }

    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=app_state.version,
        uptime_seconds=uptime,
        services=services,
        system=system_info
    )


@router.get("/ready")
async def readiness_check(app_state=Depends(get_app_state)):
    """Readiness check for Kubernetes."""
    # Check critical services
    critical_checks = [
        check_opensearch_health(),
        check_redis_health()
    ]

    results = await asyncio.gather(*critical_checks)

    if any(r.status == "unhealthy" for r in results):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

    return {"status": "ready", "timestamp": datetime.utcnow()}


@router.get("/live")
async def liveness_check(app_state=Depends(get_app_state)):
    """Liveness check for Kubernetes."""
    # Basic check - if we can respond, we're alive
    uptime = datetime.utcnow().timestamp() - app_state.start_time

    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "uptime_seconds": uptime
    }


@router.get("/service/{service_name}")
async def service_health_check(service_name: str):
    """Check health of a specific service."""
    service_checks = {
        "opensearch": check_opensearch_health,
        "redis": check_redis_health,
        "ollama": check_ollama_health,
        "langfuse": check_langfuse_health,
        "embedding_service": check_embedding_service_health,
        "llm": check_llm_health,
        "workflow": check_workflow_health
    }

    if service_name not in service_checks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown service: {service_name}"
        )

    health = await service_checks[service_name]()
    return health.dict()
