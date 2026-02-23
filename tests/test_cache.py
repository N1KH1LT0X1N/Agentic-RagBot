"""
Tests for src/services/cache/redis_cache.py — graceful degradation.
"""

import pytest

from src.services.cache.redis_cache import RedisCache


class TestNullCache:
    """When Redis is disabled, the NullCache should degrade gracefully."""

    def test_null_cache_get_returns_none(self):
        from src.services.cache.redis_cache import _NullCache
        cache = _NullCache()
        assert cache.get("anything") is None

    def test_null_cache_set_noop(self):
        from src.services.cache.redis_cache import _NullCache
        cache = _NullCache()
        # Should not raise
        cache.set("key", "value", ttl=10)

    def test_null_cache_delete_noop(self):
        from src.services.cache.redis_cache import _NullCache
        cache = _NullCache()
        cache.delete("key")
