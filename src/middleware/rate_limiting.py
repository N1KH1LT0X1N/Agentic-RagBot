"""
API Rate Limiting Middleware for MediGuard AI.
Implements token bucket and sliding window rate limiting algorithms.
"""

import asyncio
import logging
import time
from collections import deque

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.settings import get_settings

logger = logging.getLogger(__name__)


class RateLimitStrategy:
    """Base class for rate limiting strategies."""

    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, dict]:
        """Check if request is allowed.
        
        Returns:
            Tuple of (is_allowed, info_dict)
        """
        raise NotImplementedError


class TokenBucketStrategy(RateLimitStrategy):
    """Token bucket rate limiting algorithm."""

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis = redis_client
        self.memory_buckets: dict[str, dict] = {}

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, dict]:
        """Check if request is allowed using token bucket."""
        now = time.time()

        if self.redis:
            return await self._redis_token_bucket(key, limit, window, now)
        else:
            return self._memory_token_bucket(key, limit, window, now)

    async def _redis_token_bucket(self, key: str, limit: int, window: int, now: float) -> tuple[bool, dict]:
        """Token bucket implementation using Redis."""
        bucket_key = f"rate_limit:bucket:{key}"

        # Get current bucket state
        bucket_data = await self.redis.hgetall(bucket_key)

        if bucket_data:
            tokens = float(bucket_data.get('tokens', limit))
            last_refill = float(bucket_data.get('last_refill', now))
        else:
            tokens = limit
            last_refill = now

        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = time_elapsed * (limit / window)
        tokens = min(limit, tokens + tokens_to_add)

        # Check if request can be processed
        if tokens >= 1:
            tokens -= 1
            await self.redis.hset(bucket_key, mapping={
                'tokens': tokens,
                'last_refill': now
            })
            await self.redis.expire(bucket_key, window * 2)

            return True, {
                'tokens': tokens,
                'limit': limit,
                'window': window,
                'retry_after': 0
            }
        else:
            # Calculate retry after
            retry_after = (1 - tokens) / (limit / window)

            return False, {
                'tokens': tokens,
                'limit': limit,
                'window': window,
                'retry_after': retry_after
            }

    def _memory_token_bucket(self, key: str, limit: int, window: int, now: float) -> tuple[bool, dict]:
        """Token bucket implementation in memory."""
        if key not in self.memory_buckets:
            self.memory_buckets[key] = {
                'tokens': limit,
                'last_refill': now
            }

        bucket = self.memory_buckets[key]

        # Calculate tokens to add
        time_elapsed = now - bucket['last_refill']
        tokens_to_add = time_elapsed * (limit / window)
        bucket['tokens'] = min(limit, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now

        # Check if request can be processed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True, {
                'tokens': bucket['tokens'],
                'limit': limit,
                'window': window,
                'retry_after': 0
            }
        else:
            retry_after = (1 - bucket['tokens']) / (limit / window)
            return False, {
                'tokens': bucket['tokens'],
                'limit': limit,
                'window': window,
                'retry_after': retry_after
            }


class SlidingWindowStrategy(RateLimitStrategy):
    """Sliding window rate limiting algorithm."""

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis = redis_client
        self.memory_windows: dict[str, deque] = {}

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, dict]:
        """Check if request is allowed using sliding window."""
        now = time.time()
        window_start = now - window

        if self.redis:
            return await self._redis_sliding_window(key, limit, window, now, window_start)
        else:
            return self._memory_sliding_window(key, limit, window, now, window_start)

    async def _redis_sliding_window(self, key: str, limit: int, window: int, now: float, window_start: float) -> tuple[bool, dict]:
        """Sliding window implementation using Redis."""
        window_key = f"rate_limit:window:{key}"

        # Remove old entries
        await self.redis.zremrangebyscore(window_key, 0, window_start)

        # Count current requests
        current_count = await self.redis.zcard(window_key)

        if current_count < limit:
            # Add current request
            await self.redis.zadd(window_key, {str(now): now})
            await self.redis.expire(window_key, window)

            return True, {
                'count': current_count + 1,
                'limit': limit,
                'window': window,
                'remaining': limit - current_count - 1,
                'retry_after': 0
            }
        else:
            # Get oldest request time
            oldest = await self.redis.zrange(window_key, 0, 0, withscores=True)
            if oldest:
                retry_after = window - (now - oldest[0][1]) + 1
            else:
                retry_after = window

            return False, {
                'count': current_count,
                'limit': limit,
                'window': window,
                'remaining': 0,
                'retry_after': retry_after
            }

    def _memory_sliding_window(self, key: str, limit: int, window: int, now: float, window_start: float) -> tuple[bool, dict]:
        """Sliding window implementation in memory."""
        if key not in self.memory_windows:
            self.memory_windows[key] = deque()

        request_times = self.memory_windows[key]

        # Remove old requests
        while request_times and request_times[0] < window_start:
            request_times.popleft()

        if len(request_times) < limit:
            request_times.append(now)
            return True, {
                'count': len(request_times),
                'limit': limit,
                'window': window,
                'remaining': limit - len(request_times),
                'retry_after': 0
            }
        else:
            oldest_time = request_times[0]
            retry_after = window - (now - oldest_time) + 1

            return False, {
                'count': len(request_times),
                'limit': limit,
                'window': window,
                'remaining': 0,
                'retry_after': retry_after
            }


class RateLimiter:
    """Main rate limiter class."""

    def __init__(self, strategy: RateLimitStrategy):
        self.strategy = strategy
        self.rules: dict[str, dict] = {}

    def add_rule(self, path_pattern: str, limit: int, window: int, scope: str = "ip"):
        """Add a rate limiting rule."""
        self.rules[path_pattern] = {
            'limit': limit,
            'window': window,
            'scope': scope
        }

    def get_rule(self, path: str) -> dict | None:
        """Get rate limiting rule for a path."""
        # Exact match first
        if path in self.rules:
            return self.rules[path]

        # Pattern matching
        for pattern, rule in self.rules.items():
            if pattern.endswith('*') and path.startswith(pattern[:-1]):
                return rule

        return None

    async def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """Check if request is allowed."""
        path = request.url.path
        rule = self.get_rule(path)

        if not rule:
            return True, {}

        # Generate key based on scope
        if rule['scope'] == 'ip':
            key = self._get_client_ip(request)
        elif rule['scope'] == 'user':
            key = self._get_user_id(request)
        elif rule['scope'] == 'api_key':
            key = self._get_api_key(request)
        else:
            key = self._get_client_ip(request)

        # Add path to key for per-path limiting
        key = f"{key}:{path}"

        return await self.strategy.is_allowed(key, rule['limit'], rule['window'])

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client IP
        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> str:
        """Get user ID from request."""
        # This would typically come from JWT token or session
        return request.headers.get("X-User-ID", "anonymous")

    def _get_api_key(self, request: Request) -> str:
        """Get API key from request."""
        return request.headers.get("X-API-Key", "none")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, redis_url: str | None = None):
        super().__init__(app)
        self.redis_client = None

        # Initialize Redis if available
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                asyncio.create_task(self._test_redis())
            except Exception as e:
                logger.warning(f"Redis not available for rate limiting: {e}")

        # Initialize strategy and limiter
        strategy = TokenBucketStrategy(self.redis_client)
        self.limiter = RateLimiter(strategy)

        # Add default rules
        self._setup_default_rules()

    async def _test_redis(self):
        """Test Redis connection."""
        try:
            await self.redis_client.ping()
            logger.info("Rate limiting: Redis connected")
        except Exception as e:
            logger.warning(f"Rate limiting: Redis connection failed: {e}")
            self.redis_client = None

    def _setup_default_rules(self):
        """Setup default rate limiting rules."""
        settings = get_settings()

        # API endpoints
        self.limiter.add_rule("/analyze/*", limit=100, window=60, scope="ip")
        self.limiter.add_rule("/ask", limit=50, window=60, scope="ip")
        self.limiter.add_rule("/search", limit=200, window=60, scope="ip")

        # Health endpoints (no limit)
        self.limiter.add_rule("/health*", limit=1000, window=60, scope="ip")

        # Admin endpoints (stricter)
        self.limiter.add_rule("/admin/*", limit=10, window=60, scope="user")

        # Global fallback
        self.limiter.add_rule("*", limit=1000, window=60, scope="ip")

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for certain paths
        if self._should_skip(request):
            return await call_next(request)

        # Check rate limit
        allowed, info = await self.limiter.check_rate_limit(request)

        if not allowed:
            # Log rate limit violation
            logger.warning(
                f"Rate limit exceeded for {self.limiter._get_client_ip(request)} "
                f"on {request.url.path}: {info}"
            )

            # Return rate limit error
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": info.get('limit'),
                    "window": info.get('window'),
                    "retry_after": info.get('retry_after')
                },
                headers={
                    "Retry-After": str(int(info.get('retry_after', 1)))
                }
            )

        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info.get('limit', ''))
        response.headers["X-RateLimit-Remaining"] = str(info.get('remaining', info.get('tokens', '')))
        response.headers["X-RateLimit-Window"] = str(info.get('window', ''))

        return response

    def _should_skip(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/metrics", "/favicon.ico"]
        return any(request.url.path.startswith(path) for path in skip_paths)


# Factory function for easy initialization
def create_rate_limiter(app, redis_url: str | None = None) -> RateLimitMiddleware:
    """Create and configure rate limiter middleware."""
    return RateLimitMiddleware(app, redis_url)
