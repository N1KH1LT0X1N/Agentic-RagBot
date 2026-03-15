"""
Advanced caching strategies for MediGuard AI.
Implements multi-level caching with intelligent invalidation.
"""

import asyncio
import hashlib
import json
import logging
import pickle
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import redis.asyncio as redis

from src.settings import get_settings

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear(self, pattern: str | None = None) -> int:
        """Clear cache keys matching pattern."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass


class RedisBackend(CacheBackend):
    """Redis cache backend with advanced features."""

    def __init__(self, redis_url: str, key_prefix: str = "mediguard:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client."""
        if not self._client:
            self._client = redis.from_url(self.redis_url)
        return self._client

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """Get value from Redis."""
        try:
            client = await self._get_client()
            value = await client.get(self._make_key(key))

            if value:
                # Try to deserialize
                try:
                    return pickle.loads(value)
                except (pickle.PickleError, json.JSONDecodeError):
                    return value.decode('utf-8')

            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in Redis."""
        try:
            client = await self._get_client()

            # Serialize value
            if isinstance(value, (str, int, float, bool)):
                serialized = str(value).encode('utf-8')
            else:
                serialized = pickle.dumps(value)

            await client.set(self._make_key(key), serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            client = await self._get_client()
            result = await client.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def clear(self, pattern: str | None = None) -> int:
        """Clear keys matching pattern."""
        try:
            client = await self._get_client()

            if pattern:
                keys = await client.keys(self._make_key(pattern))
                if keys:
                    return await client.delete(*keys)
            else:
                # Clear all with our prefix
                keys = await client.keys(f"{self.key_prefix}*")
                if keys:
                    return await client.delete(*keys)

            return 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            client = await self._get_client()
            return await client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()


class MemoryBackend(CacheBackend):
    """In-memory cache backend for development/testing."""

    def __init__(self, max_size: int = 1000):
        self.cache: dict[str, dict] = {}
        self.max_size = max_size
        self._access_times: dict[str, float] = {}

    async def _evict_if_needed(self):
        """Evict oldest entries if cache is full."""
        if len(self.cache) >= self.max_size:
            # Find least recently used key
            oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self._access_times[oldest_key]

    async def get(self, key: str) -> Any | None:
        """Get value from memory cache."""
        if key in self.cache:
            self._access_times[key] = asyncio.get_event_loop().time()
            entry = self.cache[key]

            # Check if expired
            if entry['expires_at'] and datetime.utcnow() > entry['expires_at']:
                del self.cache[key]
                del self._access_times[key]
                return None

            return entry['value']

        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in memory cache."""
        await self._evict_if_needed()

        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.utcnow()
        }
        self._access_times[key] = asyncio.get_event_loop().time()

        return True

    async def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        if key in self.cache:
            del self.cache[key]
            if key in self._access_times:
                del self._access_times[key]
            return True
        return False

    async def clear(self, pattern: str | None = None) -> int:
        """Clear keys matching pattern."""
        if pattern:
            import fnmatch
            keys_to_delete = [k for k in self.cache.keys() if fnmatch.fnmatch(k, pattern)]
        else:
            keys_to_delete = list(self.cache.keys())

        for key in keys_to_delete:
            await self.delete(key)

        return len(keys_to_delete)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.cache


class CacheManager:
    """Advanced cache manager with multi-level caching."""

    def __init__(self, l1_backend: CacheBackend, l2_backend: CacheBackend | None = None):
        self.l1 = l1_backend  # Fast cache (e.g., memory)
        self.l2 = l2_backend  # Slower cache (e.g., Redis)
        self.stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    async def get(self, key: str) -> Any | None:
        """Get value from cache (L1 -> L2)."""
        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            self.stats['l1_hits'] += 1
            return value

        # Try L2
        if self.l2:
            value = await self.l2.get(key)
            if value is not None:
                self.stats['l2_hits'] += 1
                # Promote to L1
                await self.l1.set(key, value)
                return value

        self.stats['misses'] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None,
                  l1_ttl: int | None = None, l2_ttl: int | None = None) -> bool:
        """Set value in cache (both levels)."""
        self.stats['sets'] += 1

        # Set in L1 with shorter TTL
        l1_success = await self.l1.set(key, value, ttl=l1_ttl or ttl)

        # Set in L2 with longer TTL
        l2_success = True
        if self.l2:
            l2_success = await self.l2.set(key, value, ttl=l2_ttl or ttl)

        return l1_success and l2_success

    async def delete(self, key: str) -> bool:
        """Delete from all cache levels."""
        self.stats['deletes'] += 1

        l1_success = await self.l1.delete(key)
        l2_success = True
        if self.l2:
            l2_success = await self.l2.delete(key)

        return l1_success or l2_success

    async def clear(self, pattern: str | None = None) -> int:
        """Clear from all cache levels."""
        l1_count = await self.l1.clear(pattern)
        l2_count = 0
        if self.l2:
            l2_count = await self.l2.clear(pattern)

        return l1_count + l2_count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['l1_hits'] + self.stats['l2_hits'] + self.stats['misses']

        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': (self.stats['l1_hits'] + self.stats['l2_hits']) / total_requests if total_requests > 0 else 0,
            'l1_hit_rate': self.stats['l1_hits'] / total_requests if total_requests > 0 else 0,
            'l2_hit_rate': self.stats['l2_hits'] / total_requests if total_requests > 0 else 0
        }


class CacheDecorator:
    """Decorator for caching function results."""

    def __init__(
        self,
        cache_manager: CacheManager,
        ttl: int = 300,
        key_prefix: str = "",
        key_builder: Callable | None = None,
        condition: Callable | None = None
    ):
        self.cache = cache_manager
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.key_builder = key_builder or self._default_key_builder
        self.condition = condition or (lambda: True)

    def _default_key_builder(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Default key builder using function name and arguments."""
        # Create a deterministic key from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
        return f"{self.key_prefix}{func_name}:{key_hash}"

    def __call__(self, func):
        """Decorator implementation."""
        if asyncio.iscoroutinefunction(func):
            return self._async_decorator(func)
        else:
            return self._sync_decorator(func)

    def _async_decorator(self, func):
        """Decorator for async functions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if caching should be applied
            if not self.condition(*args, **kwargs):
                return await func(*args, **kwargs)

            # Build cache key
            cache_key = self.key_builder(func.__name__, args, kwargs)

            # Try to get from cache
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await self.cache.set(cache_key, result, ttl=self.ttl)

            return result

        return wrapper

    def _sync_decorator(self, func):
        """Decorator for sync functions."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if caching should be applied
            if not self.condition(*args, **kwargs):
                return func(*args, **kwargs)

            # Build cache key
            cache_key = self.key_builder(func.__name__, args, kwargs)

            # Try to get from cache (sync)
            loop = asyncio.get_event_loop()
            cached_result = loop.run_until_complete(self.cache.get(cache_key))
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            loop.run_until_complete(self.cache.set(cache_key, result, ttl=self.ttl))

            return result

        return wrapper


# Global cache manager instance
_cache_manager: CacheManager | None = None


async def get_cache_manager() -> CacheManager:
    """Get or create the global cache manager."""
    global _cache_manager

    if not _cache_manager:
        settings = get_settings()

        # L1 cache (memory)
        l1 = MemoryBackend(max_size=1000)

        # L2 cache (Redis) if available
        l2 = None
        if settings.REDIS_URL:
            try:
                l2 = RedisBackend(settings.REDIS_URL)
                logger.info("Cache: Redis backend enabled")
            except Exception as e:
                logger.warning(f"Cache: Redis backend failed, using memory only: {e}")

        _cache_manager = CacheManager(l1, l2)
        logger.info("Cache manager initialized")

    return _cache_manager


# Decorator factory
def cached(
    ttl: int = 300,
    key_prefix: str = "",
    key_builder: Callable | None = None,
    condition: Callable | None = None
):
    """Factory function for cache decorator."""
    async def decorator(func):
        cache_manager = await get_cache_manager()
        cache_decorator = CacheDecorator(
            cache_manager, ttl=ttl, key_prefix=key_prefix,
            key_builder=key_builder, condition=condition
        )
        return cache_decorator(func)

    return decorator


# Cache invalidation utilities
class CacheInvalidator:
    """Utilities for cache invalidation."""

    @staticmethod
    async def invalidate_by_pattern(pattern: str):
        """Invalidate cache entries matching pattern."""
        cache = await get_cache_manager()
        count = await cache.clear(pattern)
        logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
        return count

    @staticmethod
    async def invalidate_user_cache(user_id: str):
        """Invalidate all cache entries for a user."""
        patterns = [
            f"user:{user_id}:*",
            f"*:user:{user_id}:*",
            f"analysis:*:user:{user_id}",
            f"search:*:user:{user_id}"
        ]

        total = 0
        for pattern in patterns:
            total += await CacheInvalidator.invalidate_by_pattern(pattern)

        return total

    @staticmethod
    async def invalidate_biomarker_cache(biomarker_type: str):
        """Invalidate cache entries for a biomarker type."""
        pattern = f"*biomarker:{biomarker_type}:*"
        return await CacheInvalidator.invalidate_by_pattern(pattern)
