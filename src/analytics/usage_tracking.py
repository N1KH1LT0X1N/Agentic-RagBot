"""
API Analytics and Usage Tracking for MediGuard AI.
Comprehensive analytics for API usage, performance, and user behavior.
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of analytics events."""
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    ERROR = "error"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"


@dataclass
class AnalyticsEvent:
    """Analytics event data."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    user_id: str | None = None
    api_key_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    endpoint: str | None = None
    method: str | None = None
    status_code: int | None = None
    response_time_ms: float | None = None
    request_size_bytes: int | None = None
    response_size_bytes: int | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class UsageMetrics:
    """Usage metrics for a time period."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    unique_users: int = 0
    unique_api_keys: int = 0
    average_response_time: float = 0.0
    total_bandwidth_bytes: int = 0
    top_endpoints: list[dict[str, Any]] = None
    errors_by_type: dict[str, int] = None
    requests_by_hour: dict[str, int] = None

    def __post_init__(self):
        if self.top_endpoints is None:
            self.top_endpoints = []
        if self.errors_by_type is None:
            self.errors_by_type = {}
        if self.requests_by_hour is None:
            self.requests_by_hour = {}


class AnalyticsProvider:
    """Base class for analytics providers."""

    async def store_event(self, event: AnalyticsEvent) -> bool:
        """Store an analytics event."""
        raise NotImplementedError

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] = None
    ) -> UsageMetrics:
        """Get usage metrics for a time period."""
        raise NotImplementedError

    async def get_events(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] = None,
        limit: int = 100
    ) -> list[AnalyticsEvent]:
        """Get analytics events."""
        raise NotImplementedError


class RedisAnalyticsProvider(AnalyticsProvider):
    """Redis-based analytics provider."""

    def __init__(self, redis_url: str, key_prefix: str = "analytics:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client."""
        if not self._client:
            self._client = redis.from_url(self.redis_url)
        return self._client

    def _make_key(self, *parts: str) -> str:
        """Make Redis key."""
        return f"{self.key_prefix}{':'.join(parts)}"

    async def store_event(self, event: AnalyticsEvent) -> bool:
        """Store an analytics event."""
        try:
            client = await self._get_client()

            # Store event data
            event_key = self._make_key("events", event.event_id)
            await client.setex(
                event_key,
                86400 * 30,  # 30 days TTL
                json.dumps(event.to_dict())
            )

            # Update counters
            await self._update_counters(client, event)

            # Add to time-based indices
            await self._add_to_time_indices(client, event)

            return True
        except Exception as e:
            logger.error(f"Failed to store analytics event: {e}")
            return False

    async def _update_counters(self, client: redis.Redis, event: AnalyticsEvent):
        """Update various counters for the event."""
        # Daily counters
        date_key = event.timestamp.strftime("%Y-%m-%d")

        # Total requests
        await client.incr(self._make_key("daily", date_key, "requests"))

        # Endpoint counters
        if event.endpoint:
            await client.incr(self._make_key("daily", date_key, "endpoints", event.endpoint))

        # Status code counters
        if event.status_code:
            await client.incr(self._make_key("daily", date_key, "status", str(event.status_code)))

        # User counters
        if event.user_id:
            await client.sadd(self._make_key("daily", date_key, "users"), event.user_id)

        # API key counters
        if event.api_key_id:
            await client.sadd(self._make_key("daily", date_key, "api_keys"), event.api_key_id)

        # Response time tracking
        if event.response_time_ms:
            await client.lpush(
                self._make_key("daily", date_key, "response_times"),
                event.response_time_ms
            )
            await client.ltrim(self._make_key("daily", date_key, "response_times"), 0, 9999)

    async def _add_to_time_indices(self, client: redis.Redis, event: AnalyticsEvent):
        """Add event to time-based indices."""
        # Hourly index
        hour_key = event.timestamp.strftime("%Y-%m-%d:%H")
        await client.zadd(
            self._make_key("hourly", hour_key),
            {event.event_id: event.timestamp.timestamp()}
        )
        await client.expire(self._make_key("hourly", hour_key), 86400 * 7)  # 7 days

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] = None
    ) -> UsageMetrics:
        """Get usage metrics for a time period."""
        client = await self._get_client()
        metrics = UsageMetrics()

        # Iterate through days in range
        current_date = start_time.date()
        end_date = end_time.date()

        total_response_times = []
        endpoint_counts = defaultdict(int)

        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")

            # Get daily counters
            metrics.total_requests += int(
                await client.get(self._make_key("daily", date_key, "requests")) or 0
            )

            # Get successful requests (2xx status codes)
            for status in range(200, 300):
                count = int(
                    await client.get(self._make_key("daily", date_key, "status", str(status))) or 0
                )
                metrics.successful_requests += count

            # Get unique users
            users = await client.smembers(self._make_key("daily", date_key, "users"))
            metrics.unique_users += len(users)

            # Get unique API keys
            api_keys = await client.smembers(self._make_key("daily", date_key, "api_keys"))
            metrics.unique_api_keys += len(api_keys)

            # Get response times
            times = await client.lrange(self._make_key("daily", date_key, "response_times"), 0, -1)
            total_response_times.extend([float(t) for t in times])

            # Get endpoint counts
            for endpoint in await client.keys(self._make_key("daily", date_key, "endpoints", "*")):
                endpoint_name = endpoint.decode().split(":")[-1]
                count = int(await client.get(endpoint) or 0)
                endpoint_counts[endpoint_name] += count

            current_date += timedelta(days=1)

        # Calculate derived metrics
        metrics.failed_requests = metrics.total_requests - metrics.successful_requests

        if total_response_times:
            metrics.average_response_time = sum(total_response_times) / len(total_response_times)

        # Top endpoints
        metrics.top_endpoints = [
            {"endpoint": ep, "requests": count}
            for ep, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return metrics

    async def get_events(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] = None,
        limit: int = 100
    ) -> list[AnalyticsEvent]:
        """Get analytics events."""
        client = await self._get_client()
        events = []

        # Search through hourly indices
        current_hour = start_time.replace(minute=0, second=0, microsecond=0)

        while current_hour <= end_time and len(events) < limit:
            hour_key = current_hour.strftime("%Y-%m-%d:%H")

            # Get event IDs from sorted set
            event_ids = await client.zrangebyscore(
                self._make_key("hourly", hour_key),
                start_time.timestamp(),
                end_time.timestamp(),
                start=0,
                num=limit - len(events)
            )

            # Get event data
            for event_id in event_ids:
                event_key = self._make_key("events", event_id.decode())
                event_data = await client.get(event_key)

                if event_data:
                    event_dict = json.loads(event_data)
                    event = AnalyticsEvent(
                        event_id=event_dict["event_id"],
                        event_type=EventType(event_dict["event_type"]),
                        timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                        user_id=event_dict.get("user_id"),
                        api_key_id=event_dict.get("api_key_id"),
                        endpoint=event_dict.get("endpoint"),
                        status_code=event_dict.get("status_code"),
                        response_time_ms=event_dict.get("response_time_ms")
                    )

                    # Apply filters
                    if self._matches_filters(event, filters):
                        events.append(event)

            current_hour += timedelta(hours=1)

        return events

    def _matches_filters(self, event: AnalyticsEvent, filters: dict[str, Any]) -> bool:
        """Check if event matches filters."""
        if not filters:
            return True

        if filters.get("user_id") and event.user_id != filters["user_id"]:
            return False

        if filters.get("api_key_id") and event.api_key_id != filters["api_key_id"]:
            return False

        if filters.get("endpoint") and event.endpoint != filters["endpoint"]:
            return False

        if filters.get("status_code") and event.status_code != filters["status_code"]:
            return False

        return True


class AnalyticsManager:
    """Manages analytics collection and reporting."""

    def __init__(self, provider: AnalyticsProvider):
        self.provider = provider
        self.buffer: list[AnalyticsEvent] = []
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
        self._flush_task: asyncio.Task | None = None

    async def track_event(self, event: AnalyticsEvent):
        """Track an analytics event."""
        self.buffer.append(event)

        if len(self.buffer) >= self.buffer_size:
            await self.flush_buffer()

    async def track_request(
        self,
        request: Request,
        response: Response = None,
        response_time_ms: float = None,
        error: Exception = None
    ):
        """Track an API request."""
        # Extract request info
        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)
        session_id = getattr(request.state, "session_id", None)

        # Create request event
        request_event = AnalyticsEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.API_REQUEST,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            api_key_id=api_key_id,
            session_id=session_id,
            request_id=getattr(request.state, "request_id", None),
            endpoint=request.url.path,
            method=request.method,
            user_agent=request.headers.get("user-agent"),
            ip_address=self._get_client_ip(request),
            request_size_bytes=len(await request.body()) if request.method in ["POST", "PUT"] else 0
        )

        await self.track_event(request_event)

        # Create response event if available
        if response or error:
            response_event = AnalyticsEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.API_RESPONSE if not error else EventType.ERROR,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                api_key_id=api_key_id,
                session_id=session_id,
                request_id=getattr(request.state, "request_id", None),
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code if response else 500,
                response_time_ms=response_time_ms,
                response_size_bytes=len(response.body) if response else 0,
                metadata={"error": str(error)} if error else None
            )

            await self.track_event(response_event)

    async def track_user_action(
        self,
        action: str,
        user_id: str,
        metadata: dict[str, Any] = None
    ):
        """Track a user action."""
        event = AnalyticsEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.USER_ACTION,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            metadata={"action": action, **(metadata or {})}
        )

        await self.track_event(event)

    async def get_dashboard_data(
        self,
        time_range: str = "24h"
    ) -> dict[str, Any]:
        """Get dashboard analytics data."""
        # Parse time range
        now = datetime.utcnow()
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)

        # Get metrics
        metrics = await self.provider.get_metrics(start_time, now)

        # Get recent events
        recent_events = await self.provider.get_events(
            start_time,
            now,
            limit=50
        )

        # Calculate additional metrics
        error_rate = (metrics.failed_requests / metrics.total_requests * 100) if metrics.total_requests > 0 else 0

        return {
            "time_range": time_range,
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "error_rate": round(error_rate, 2),
                "unique_users": metrics.unique_users,
                "unique_api_keys": metrics.unique_api_keys,
                "average_response_time": round(metrics.average_response_time, 2),
                "total_bandwidth_mb": round(metrics.total_bandwidth_bytes / (1024 * 1024), 2)
            },
            "top_endpoints": metrics.top_endpoints,
            "recent_events": [event.to_dict() for event in recent_events[:10]]
        }

    async def get_usage_report(
        self,
        start_date: str,
        end_date: str,
        group_by: str = "day"
    ) -> dict[str, Any]:
        """Generate usage report."""
        start_time = datetime.fromisoformat(start_date)
        end_time = datetime.fromisoformat(end_date)

        metrics = await self.provider.get_metrics(start_time, end_time)

        # Group data by time period
        if group_by == "hour":
            # Get hourly breakdown
            hourly_data = await self._get_hourly_breakdown(start_time, end_time)
        else:
            # Get daily breakdown
            daily_data = await self._get_daily_breakdown(start_time, end_time)
            hourly_data = None

        return {
            "period": {
                "start": start_date,
                "end": end_date,
                "group_by": group_by
            },
            "summary": {
                "total_requests": metrics.total_requests,
                "unique_users": metrics.unique_users,
                "average_response_time": metrics.average_response_time,
                "success_rate": (metrics.successful_requests / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
            },
            "breakdown": hourly_data or daily_data,
            "top_endpoints": metrics.top_endpoints
        }

    async def flush_buffer(self):
        """Flush buffered events to provider."""
        if not self.buffer:
            return

        events_to_flush = self.buffer.copy()
        self.buffer.clear()

        # Store events in parallel
        tasks = [self.provider.store_event(event) for event in events_to_flush]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def start_background_flush(self):
        """Start background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._background_flush_loop())

    async def stop_background_flush(self):
        """Stop background flush task."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

    async def _background_flush_loop(self):
        """Background loop for flushing events."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analytics flush error: {e}")

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def _get_hourly_breakdown(self, start_time: datetime, end_time: datetime) -> list[dict]:
        """Get hourly usage breakdown."""
        # This would be implemented based on provider capabilities
        return []

    async def _get_daily_breakdown(self, start_time: datetime, end_time: datetime) -> list[dict]:
        """Get daily usage breakdown."""
        # This would be implemented based on provider capabilities
        return []


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track API requests."""

    def __init__(self, app, analytics_manager: AnalyticsManager):
        super().__init__(app)
        self.analytics_manager = analytics_manager

    async def dispatch(self, request: Request, call_next):
        """Track request and response."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Track start time
        start_time = time.time()

        # Process request
        response = None
        error = None

        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            # Create error response
            from fastapi import HTTPException
            if isinstance(e, HTTPException):
                response = Response(
                    content=str(e.detail),
                    status_code=e.status_code
                )
            else:
                response = Response(
                    content="Internal Server Error",
                    status_code=500
                )

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Track the request
        await self.analytics_manager.track_request(
            request=request,
            response=response,
            response_time_ms=response_time_ms,
            error=error
        )

        return response


# Global analytics manager
_analytics_manager: AnalyticsManager | None = None


async def get_analytics_manager() -> AnalyticsManager:
    """Get or create the global analytics manager."""
    global _analytics_manager

    if not _analytics_manager:
        from src.settings import get_settings
        settings = get_settings()

        # Create provider
        if settings.REDIS_URL:
            provider = RedisAnalyticsProvider(settings.REDIS_URL)
        else:
            # Fallback to in-memory provider for development
            provider = MemoryAnalyticsProvider()

        _analytics_manager = AnalyticsManager(provider)
        await _analytics_manager.start_background_flush()

    return _analytics_manager


# Memory provider for development
class MemoryAnalyticsProvider(AnalyticsProvider):
    """In-memory analytics provider for development."""

    def __init__(self):
        self.events: list[AnalyticsEvent] = []
        self.max_events = 10000

    async def store_event(self, event: AnalyticsEvent) -> bool:
        """Store event in memory."""
        self.events.append(event)

        # Limit size
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        return True

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] = None
    ) -> UsageMetrics:
        """Get metrics from memory."""
        events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time
            and self._matches_filters(e, filters)
        ]

        metrics = UsageMetrics()
        metrics.total_requests = len(events)
        metrics.successful_requests = len([e for e in events if (e.status_code or 0) < 400])
        metrics.failed_requests = metrics.total_requests - metrics.successful_requests
        metrics.unique_users = len(set(e.user_id for e in events if e.user_id))
        metrics.unique_api_keys = len(set(e.api_key_id for e in events if e.api_key_id))

        # Calculate average response time
        response_times = [e.response_time_ms for e in events if e.response_time_ms]
        if response_times:
            metrics.average_response_time = sum(response_times) / len(response_times)

        return metrics

    async def get_events(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] = None,
        limit: int = 100
    ) -> list[AnalyticsEvent]:
        """Get events from memory."""
        events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time
            and self._matches_filters(e, filters)
        ]

        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]

    def _matches_filters(self, event: AnalyticsEvent, filters: dict[str, Any]) -> bool:
        """Check if event matches filters."""
        if not filters:
            return True

        if filters.get("user_id") and event.user_id != filters["user_id"]:
            return False

        if filters.get("endpoint") and event.endpoint != filters["endpoint"]:
            return False

        return True
