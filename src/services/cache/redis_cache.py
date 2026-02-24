"""
MediGuard AI — Redis Cache

Exact-match caching with SHA-256 keys for RAG and analysis responses.
Gracefully degrades when Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any, Optional

from src.settings import get_settings

logger = logging.getLogger(__name__)

try:
    import redis as _redis
except ImportError:  # pragma: no cover
    _redis = None  # type: ignore[assignment]


class RedisCache:
    """Thin Redis wrapper with SHA-256 key generation and JSON ser/de."""

    def __init__(self, client: Any, default_ttl: int = 21600):
        self._client = client
        self._default_ttl = default_ttl
        self._enabled = client is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def ping(self) -> bool:
        if not self._enabled:
            return False
        try:
            return self._client.ping()
        except Exception:
            return False

    @staticmethod
    def _make_key(*parts: str) -> str:
        raw = "|".join(parts)
        return f"mediguard:{hashlib.sha256(raw.encode()).hexdigest()}"

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value by key."""
        if not self._enabled:
            return None
        cache_key = self._make_key(key)
        try:
            value = self._client.get(cache_key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:
            logger.warning("Cache GET failed: %s", exc)
            return None

    def set(self, key: str, value: Any, *, ttl: Optional[int] = None) -> bool:
        """Set a cached value with optional TTL."""
        if not self._enabled:
            return False
        cache_key = self._make_key(key)
        try:
            self._client.setex(cache_key, ttl or self._default_ttl, json.dumps(value, default=str))
            return True
        except Exception as exc:
            logger.warning("Cache SET failed: %s", exc)
            return False

    def delete(self, key: str) -> bool:
        """Delete a cached value by key."""
        if not self._enabled:
            return False
        cache_key = self._make_key(key)
        try:
            self._client.delete(cache_key)
            return True
        except Exception as exc:
            logger.warning("Cache DELETE failed: %s", exc)
            return False

    def flush(self) -> bool:
        if not self._enabled:
            return False
        try:
            self._client.flushdb()
            return True
        except Exception:
            return False


class _NullCache(RedisCache):
    """No-op cache returned when Redis is disabled or unavailable."""

    def __init__(self):
        super().__init__(client=None)


@lru_cache(maxsize=1)
def make_redis_cache() -> RedisCache:
    """Factory — returns a live cache or a silent null-cache."""
    settings = get_settings()
    if not settings.redis.enabled or _redis is None:
        logger.info("Redis caching disabled")
        return _NullCache()
    try:
        client = _redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        client.ping()
        logger.info("Redis connected (%s:%d)", settings.redis.host, settings.redis.port)
        return RedisCache(client, settings.redis.ttl_seconds)
    except Exception as exc:
        logger.warning("Redis unavailable (%s), running without cache", exc)
        return _NullCache()
