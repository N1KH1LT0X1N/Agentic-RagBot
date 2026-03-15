"""
Prometheus metrics collection for MediGuard AI.
"""

import logging
import time
from functools import wraps

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

# HTTP metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Workflow metrics
workflow_duration = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration in seconds',
    ['workflow_type'],
    buckets=[1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]
)

workflow_total = Counter(
    'workflow_total',
    'Total workflow executions',
    ['workflow_type', 'status']
)

# Agent metrics
agent_execution_duration = Histogram(
    'agent_execution_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

agent_total = Counter(
    'agent_total',
    'Total agent executions',
    ['agent_name', 'status']
)

# Database metrics
opensearch_connections_active = Gauge(
    'opensearch_connections_active',
    'Active OpenSearch connections'
)

redis_connections_active = Gauge(
    'redis_connections_active',
    'Active Redis connections'
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# LLM metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens',
    ['provider', 'model', 'type']  # type: input, output
)

# System metrics
active_users = Gauge(
    'active_users_total',
    'Number of active users'
)

memory_usage_bytes = Gauge(
    'process_resident_memory_bytes',
    'Process resident memory in bytes'
)

cpu_usage = Gauge(
    'process_cpu_seconds_total',
    'Total process CPU time in seconds'
)


def track_http_requests(func):
    """Decorator to track HTTP request metrics."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        start_time = time.time()

        try:
            response = await func(request, *args, **kwargs)
            status = str(response.status_code)
        except Exception as e:
            status = "500"
            logger.error(f"HTTP request error: {e}")
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status
            ).inc()

            http_request_duration.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)

        return response

    return wrapper


def track_workflow(workflow_type: str):
    """Decorator to track workflow execution metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Workflow {workflow_type} error: {e}")
                raise
            finally:
                duration = time.time() - start_time

                workflow_total.labels(
                    workflow_type=workflow_type,
                    status=status
                ).inc()

                workflow_duration.labels(
                    workflow_type=workflow_type
                ).observe(duration)

        return wrapper
    return decorator


def track_agent(agent_name: str):
    """Decorator to track agent execution metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Agent {agent_name} error: {e}")
                raise
            finally:
                duration = time.time() - start_time

                agent_total.labels(
                    agent_name=agent_name,
                    status=status
                ).inc()

                agent_execution_duration.labels(
                    agent_name=agent_name
                ).observe(duration)

        return wrapper
    return decorator


def track_llm_request(provider: str, model: str):
    """Decorator to track LLM request metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Track tokens if available
                if hasattr(result, 'usage'):
                    if hasattr(result.usage, 'prompt_tokens'):
                        llm_tokens_total.labels(
                            provider=provider,
                            model=model,
                            type="input"
                        ).inc(result.usage.prompt_tokens)

                    if hasattr(result.usage, 'completion_tokens'):
                        llm_tokens_total.labels(
                            provider=provider,
                            model=model,
                            type="output"
                        ).inc(result.usage.completion_tokens)

                return result
            except Exception as e:
                logger.error(f"LLM request error: {e}")
                raise
            finally:
                duration = time.time() - start_time

                llm_requests_total.labels(
                    provider=provider,
                    model=model
                ).inc()

                llm_request_duration.labels(
                    provider=provider,
                    model=model
                ).observe(duration)

        return wrapper
    return decorator


def track_cache_operation(cache_type: str):
    """Track cache operations."""
    def record_hit():
        cache_hits_total.labels(cache_type=cache_type).inc()

    def record_miss():
        cache_misses_total.labels(cache_type=cache_type).inc()

    return record_hit, record_miss


def update_system_metrics():
    """Update system-level metrics."""
    import os

    import psutil

    process = psutil.Process(os.getpid())

    # Memory usage
    memory_usage_bytes.set(process.memory_info().rss)

    # CPU usage
    cpu_usage.set(process.cpu_times().user)


def metrics_endpoint():
    """FastAPI endpoint to serve Prometheus metrics."""
    def metrics():
        update_system_metrics()
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return metrics


class MetricsCollector:
    """Central metrics collector for the application."""

    def __init__(self):
        self.start_time = time.time()
        self.request_counts: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}

    def increment_request_count(self, endpoint: str):
        """Increment request count for an endpoint."""
        self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1

    def increment_error_count(self, error_type: str):
        """Increment error count for an error type."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time

    def get_request_rate(self) -> float:
        """Get current request rate per second."""
        uptime = self.get_uptime_seconds()
        if uptime > 0:
            total_requests = sum(self.request_counts.values())
            return total_requests / uptime
        return 0.0

    def get_error_rate(self) -> float:
        """Get current error rate."""
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())

        if total_requests > 0:
            return total_errors / total_requests
        return 0.0


# Global metrics collector instance
metrics_collector = MetricsCollector()
