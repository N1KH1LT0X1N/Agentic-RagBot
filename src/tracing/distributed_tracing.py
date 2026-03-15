"""
Distributed tracing integration for MediGuard AI.
Uses OpenTelemetry for end-to-end request tracing.
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from opentelemetry import baggage, context, trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind, Status, StatusCode

from src.settings import get_settings

logger = logging.getLogger(__name__)


class DistributedTracer:
    """Manages distributed tracing configuration and operations."""

    def __init__(self):
        self.tracer_provider: TracerProvider | None = None
        self.is_initialized = False
        self.service_name = "mediguard-api"
        self.service_version = "2.0.0"

    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        if self.is_initialized:
            return

        settings = get_settings()

        # Set up tracer provider
        self.tracer_provider = TracerProvider()
        trace.set_tracer_provider(self.tracer_provider)

        # Configure exporters based on environment
        exporters = []

        # Jaeger exporter
        if os.getenv("JAEGER_ENDPOINT"):
            jaeger_exporter = JaegerExporter(
                endpoint=os.getenv("JAEGER_ENDPOINT"),
                collector_endpoint=os.getenv("JAEGER_COLLECTOR_ENDPOINT"),
                agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            )
            exporters.append(jaeger_exporter)
            logger.info("Jaeger tracing enabled")

        # OTLP exporter (for services like Tempo, Honeycomb, etc.)
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            otlp_exporter = OTLPSpanExporter(
                endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
                headers=json.loads(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "{}")),
            )
            exporters.append(otlp_exporter)
            logger.info("OTLP tracing enabled")

        # Add processors for each exporter
        for exporter in exporters:
            processor = BatchSpanProcessor(exporter)
            self.tracer_provider.add_span_processor(processor)

        # Set global propagator
        set_global_textmap({})

        # Instrument libraries
        self._instrument_libraries()

        self.is_initialized = True
        logger.info("Distributed tracing initialized")

    def _instrument_libraries(self):
        """Instrument common libraries for automatic tracing."""
        # FastAPI
        try:
            FastAPIInstrumentor.instrument_app(
                app=None,  # Will be set when app is created
                tracer_provider=self.tracer_provider,
                excluded_urls=[
                    "/health",
                    "/metrics",
                    "/docs",
                    "/redoc",
                    "/openapi.json"
                ]
            )
        except Exception as e:
            logger.warning(f"Failed to instrument FastAPI: {e}")

        # HTTPX
        try:
            HTTPXClientInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument HTTPX: {e}")

        # Redis
        try:
            RedisInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")

        # SQLAlchemy (if used)
        try:
            SQLAlchemyInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument SQLAlchemy: {e}")

    def get_tracer(self, name: str = None):
        """Get a tracer instance."""
        if not self.is_initialized:
            self.initialize()

        return trace.get_tracer(name or self.service_name)

    def shutdown(self):
        """Shutdown the tracer provider."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            self.is_initialized = False
            logger.info("Distributed tracing shutdown")


# Global tracer instance
_distributed_tracer = DistributedTracer()


def get_distributed_tracer() -> DistributedTracer:
    """Get the global distributed tracer instance."""
    return _distributed_tracer


class TraceContext:
    """Helper class for managing trace context."""

    @staticmethod
    def get_current_span() -> trace.Span:
        """Get the current span."""
        return trace.get_current_span()

    @staticmethod
    def get_trace_id() -> str | None:
        """Get the current trace ID."""
        span = trace.get_current_span()
        if span:
            span_context = span.get_span_context()
            if span_context.is_valid:
                return format(span_context.trace_id, "032x")
        return None

    @staticmethod
    def get_span_id() -> str | None:
        """Get the current span ID."""
        span = trace.get_current_span()
        if span:
            span_context = span.get_span_context()
            if span_context.is_valid:
                return format(span_context.span_id, "016x")
        return None

    @staticmethod
    def set_baggage(key: str, value: str):
        """Set baggage item."""
        baggage.set_baggage(key, value)

    @staticmethod
    def get_baggage(key: str) -> str | None:
        """Get baggage item."""
        return baggage.get_baggage(key)

    @staticmethod
    def inject_headers(headers: dict[str, str]):
        """Inject trace context into headers."""
        ctx = context.get_current()
        carrier = {}
        set_global_textmap().inject(carrier, ctx)
        headers.update(carrier)

    @staticmethod
    def extract_from_headers(headers: dict[str, str]):
        """Extract trace context from headers."""
        ctx = set_global_textmap().extract(headers)
        return ctx


@asynccontextmanager
async def trace_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None
):
    """Context manager for creating spans."""
    tracer = get_distributed_tracer().get_tracer()

    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        yield span


def trace_function(
    name: str = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None
):
    """Decorator for tracing functions."""
    def decorator(func):
        import asyncio
        import functools

        span_name = name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_distributed_tracer().get_tracer()

                with tracer.start_as_current_span(span_name, kind=kind) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, str(value))

                    # Add function arguments as attributes (be careful with sensitive data)
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_distributed_tracer().get_tracer()

                with tracer.start_as_current_span(span_name, kind=kind) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, str(value))

                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise

            return sync_wrapper

    return decorator


class TracingMiddleware:
    """Custom middleware for enhanced tracing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get tracer
        tracer = get_distributed_tracer().get_tracer("asgi")

        # Extract trace context from headers
        headers = dict(scope.get("headers", []))
        ctx = TraceContext.extract_from_headers(headers)

        with tracer.start_as_current_span(
            f"{scope['method']} {scope['path']}",
            kind=SpanKind.SERVER,
            context=ctx
        ) as span:
            # Set standard attributes
            span.set_attribute(SpanAttributes.HTTP_METHOD, scope["method"])
            span.set_attribute(SpanAttributes.HTTP_URL, scope.get("path", ""))
            span.set_attribute(SpanAttributes.HTTP_SCHEME, scope.get("scheme", "http"))
            span.set_attribute(SpanAttributes.HTTP_HOST, scope.get("server", ("", ""))[0])
            span.set_attribute(SpanAttributes.HTTP_USER_AGENT, self._get_header(headers, b"user-agent"))
            span.set_attribute(SpanAttributes.HTTP_CLIENT_IP, self._get_client_ip(scope))

            # Add custom baggage
            TraceContext.set_baggage("service.name", "mediguard-api")
            TraceContext.set_baggage("service.version", "2.0.0")

            # Capture start time
            start_time = time.time()

            # Wrap send to capture response
            async def traced_send(message):
                if message["type"] == "http.response.start":
                    # Set response attributes
                    status = message.get("status", 200)
                    span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status)

                    # Mark error status
                    if status >= 400:
                        span.set_status(Status(StatusCode.ERROR))
                    else:
                        span.set_status(Status(StatusCode.OK))

                elif message["type"] == "http.response.body":
                    # Calculate duration
                    duration = time.time() - start_time
                    span.set_attribute("http.response.duration_ms", duration * 1000)

                await send(message)

            await self.app(scope, receive, traced_send)

    def _get_header(self, headers: dict[bytes, bytes], name: bytes) -> str | None:
        """Get header value by name."""
        for key, value in headers.items():
            if key.lower() == name.lower():
                return value.decode("utf-8")
        return None

    def _get_client_ip(self, scope: dict[str, Any]) -> str | None:
        """Extract client IP from scope."""
        # Check for forwarded headers
        headers = dict(scope.get("headers", []))

        # X-Forwarded-For
        xff = self._get_header(headers, b"x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()

        # X-Real-IP
        xri = self._get_header(headers, b"x-real-ip")
        if xri:
            return xri

        # Client from scope
        client = scope.get("client")
        if client:
            return client[0]

        return None


# Specialized tracing for different components

class DatabaseTracer:
    """Tracing utilities for database operations."""

    @staticmethod
    @trace_function(kind=SpanKind.CLIENT)
    async def trace_query(query: str, params: dict[str, Any] = None):
        """Trace a database query."""
        span = TraceContext.get_current_span()
        span.set_attribute("db.query", query)
        span.set_attribute("db.system", "opensearch")

        if params:
            span.set_attribute("db.params", str(params))

    @staticmethod
    @trace_function(kind=SpanKind.CLIENT)
    async def trace_bulk_operation(operation: str, count: int):
        """Trace a bulk database operation."""
        span = TraceContext.get_current_span()
        span.set_attribute("db.operation", operation)
        span.set_attribute("db.bulk_count", count)


class LLTracer:
    """Tracing utilities for LLM operations."""

    @staticmethod
    @trace_function(kind=SpanKind.CLIENT)
    async def trace_llm_call(
        model: str,
        prompt: str,
        response: str = None,
        tokens: dict[str, int] = None
    ):
        """Trace an LLM API call."""
        span = TraceContext.get_current_span()
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.prompt", prompt[:1000])  # Truncate for privacy
        span.set_attribute("llm.provider", "openai")

        if response:
            span.set_attribute("llm.response", response[:1000])

        if tokens:
            span.set_attribute("llm.tokens.prompt", tokens.get("prompt", 0))
            span.set_attribute("llm.tokens.completion", tokens.get("completion", 0))
            span.set_attribute("llm.tokens.total", tokens.get("total", 0))


class CacheTracer:
    """Tracing utilities for cache operations."""

    @staticmethod
    @trace_function(kind=SpanKind.CLIENT)
    async def trace_cache_operation(operation: str, key: str, hit: bool = None):
        """Trace a cache operation."""
        span = TraceContext.get_current_span()
        span.set_attribute("cache.operation", operation)
        span.set_attribute("cache.key", key)
        span.set_attribute("cache.system", "redis")

        if hit is not None:
            span.set_attribute("cache.hit", hit)


class WorkflowTracer:
    """Tracing utilities for workflow operations."""

    @staticmethod
    @trace_function(kind=SpanKind.INTERNAL)
    async def trace_workflow_step(
        workflow_name: str,
        step_name: str,
        step_duration: float,
        success: bool
    ):
        """Trace a workflow step."""
        span = TraceContext.get_current_span()
        span.set_attribute("workflow.name", workflow_name)
        span.set_attribute("workflow.step", step_name)
        span.set_attribute("workflow.step.duration_ms", step_duration * 1000)
        span.set_attribute("workflow.step.success", success)


# Integration with existing services

async def trace_http_request(
    method: str,
    url: str,
    headers: dict[str, str] = None,
    status_code: int = None,
    duration_ms: float = None
):
    """Trace an HTTP request."""
    with trace_span(
        f"HTTP {method}",
        kind=SpanKind.CLIENT,
        attributes={
            "http.method": method,
            "http.url": url,
            "http.status_code": status_code,
            "http.duration_ms": duration_ms
        }
    ) as span:
        if status_code and status_code >= 400:
            span.set_status(Status(StatusCode.ERROR))


# Metrics integration
class TraceMetrics:
    """Extract metrics from traces."""

    def __init__(self):
        self.request_counts: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}
        self.response_times: dict[str, list[float]] = {}

    def record_span(self, span_data: dict[str, Any]):
        """Record span data for metrics."""
        name = span_data.get("name", "")
        duration = span_data.get("duration_ms", 0)
        status = span_data.get("status", "ok")

        # Count requests
        self.request_counts[name] = self.request_counts.get(name, 0) + 1

        # Count errors
        if status != "ok":
            self.error_counts[name] = self.error_counts.get(name, 0) + 1

        # Track response times
        if name not in self.response_times:
            self.response_times[name] = []
        self.response_times[name].append(duration)

    def get_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics."""
        return {
            "request_counts": self.request_counts,
            "error_counts": self.error_counts,
            "avg_response_times": {
                name: sum(times) / len(times)
                for name, times in self.response_times.items()
                if times
            }
        }


# Initialization function for FastAPI app
def initialize_tracing(app):
    """Initialize tracing for FastAPI application."""
    # Initialize distributed tracer
    tracer = get_distributed_tracer()
    tracer.initialize()

    # Add custom middleware
    app.add_middleware(TracingMiddleware)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    logger.info("Tracing initialized for FastAPI application")
