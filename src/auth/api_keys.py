"""
API Key Authentication System for MediGuard AI.
Provides secure API access with key management and rate limiting.
"""

import hashlib
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from src.settings import get_settings

logger = logging.getLogger(__name__)


class APIKeyStatus(Enum):
    """API key status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class APIKeyScope(Enum):
    """API key scopes."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    ANALYZE = "analyze"
    SEARCH = "search"


@dataclass
class APIKey:
    """API key model."""
    key_id: str
    key_hash: str
    name: str
    description: str
    scopes: list[APIKeyScope]
    status: APIKeyStatus
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    usage_count: int = 0
    rate_limit: dict[str, int] | None = None
    metadata: dict[str, Any] | None = None
    created_by: str | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (without sensitive data)."""
        data = asdict(self)
        data.pop('key_hash', None)
        data['scopes'] = [s.value for s in self.scopes]
        data['status'] = self.status.value
        if data['created_at']:
            data['created_at'] = self.created_at.isoformat()
        if data['expires_at']:
            data['expires_at'] = self.expires_at.isoformat()
        if data['last_used_at']:
            data['last_used_at'] = self.last_used_at.isoformat()
        return data


class APIKeyProvider:
    """Base class for API key providers."""

    async def create_key(self, api_key: APIKey) -> str:
        """Create a new API key."""
        raise NotImplementedError

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID."""
        raise NotImplementedError

    async def get_key_by_hash(self, key_hash: str) -> APIKey | None:
        """Get API key by hash."""
        raise NotImplementedError

    async def update_key(self, api_key: APIKey) -> bool:
        """Update an API key."""
        raise NotImplementedError

    async def delete_key(self, key_id: str) -> bool:
        """Delete an API key."""
        raise NotImplementedError

    async def list_keys(self, created_by: str = None) -> list[APIKey]:
        """List API keys."""
        raise NotImplementedError


class RedisAPIKeyProvider(APIKeyProvider):
    """Redis-based API key provider."""

    def __init__(self, redis_url: str, key_prefix: str = "api_keys:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client."""
        if not self._client:
            self._client = redis.from_url(self.redis_url)
        return self._client

    def _make_key(self, key_id: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key_id}"

    def _make_hash_key(self, key_hash: str) -> str:
        """Make hash lookup key."""
        return f"{self.key_prefix}hash:{key_hash}"

    async def create_key(self, api_key: APIKey) -> str:
        """Create a new API key and return the actual key."""
        client = await self._get_client()

        # Generate the actual API key
        actual_key = f"mg_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

        # Update the API key with hash
        api_key.key_hash = key_hash

        # Store API key data
        key_data = api_key.to_dict()
        key_data['key_hash'] = key_hash
        key_data['scopes'] = json.dumps([s.value for s in api_key.scopes])

        # Store in Redis
        await client.hset(
            self._make_key(api_key.key_id),
            mapping=key_data
        )

        # Create hash lookup
        await client.set(
            self._make_hash_key(key_hash),
            api_key.key_id,
            ex=86400 * 365  # 1 year expiry
        )

        # Add to user's key list
        if api_key.created_by:
            await client.sadd(
                f"{self.key_prefix}user:{api_key.created_by}",
                api_key.key_id
            )

        logger.info(f"Created API key {api_key.key_id} for {api_key.created_by}")
        return actual_key

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID."""
        client = await self._get_client()

        data = await client.hgetall(self._make_key(key_id))
        if not data:
            return None

        return self._deserialize_key(data)

    async def get_key_by_hash(self, key_hash: str) -> APIKey | None:
        """Get API key by hash."""
        client = await self._get_client()

        # Get key_id from hash
        key_id = await client.get(self._make_hash_key(key_hash))
        if not key_id:
            return None

        return await self.get_key(key_id.decode())

    async def update_key(self, api_key: APIKey) -> bool:
        """Update an API key."""
        client = await self._get_client()

        key_data = api_key.to_dict()
        key_data['key_hash'] = api_key.key_hash
        key_data['scopes'] = json.dumps([s.value for s in api_key.scopes])

        result = await client.hset(
            self._make_key(api_key.key_id),
            mapping=key_data
        )

        return result > 0

    async def delete_key(self, key_id: str) -> bool:
        """Delete an API key."""
        client = await self._get_client()

        # Get key data for cleanup
        api_key = await self.get_key(key_id)
        if not api_key:
            return False

        # Delete main key
        result = await client.delete(self._make_key(key_id))

        # Delete hash lookup
        await client.delete(self._make_hash_key(api_key.key_hash))

        # Remove from user's key list
        if api_key.created_by:
            await client.srem(
                f"{self.key_prefix}user:{api_key.created_by}",
                key_id
            )

        logger.info(f"Deleted API key {key_id}")
        return result > 0

    async def list_keys(self, created_by: str = None) -> list[APIKey]:
        """List API keys."""
        client = await self._get_client()

        if created_by:
            # Get user's keys
            key_ids = await client.smembers(f"{self.key_prefix}user:{created_by}")
        else:
            # Get all keys (scan)
            key_ids = []
            async for key in client.scan_iter(match=f"{self.key_prefix}*"):
                if not key.endswith(b":hash"):
                    key_ids.append(key.split(b":")[-1])

        keys = []
        for key_id in key_ids:
            api_key = await self.get_key(key_id.decode() if isinstance(key_id, bytes) else key_id)
            if api_key:
                keys.append(api_key)

        return keys

    def _deserialize_key(self, data: dict[bytes, Any]) -> APIKey:
        """Deserialize API key from Redis data."""
        # Convert bytes to strings
        data = {k.decode() if isinstance(k, bytes) else k: v for k, v in data.items()}
        data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}

        # Parse scopes
        scopes = json.loads(data.get('scopes', '[]'))
        scopes = [APIKeyScope(s) for s in scopes]

        # Parse dates
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        expires_at = datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
        last_used_at = datetime.fromisoformat(data['last_used_at']) if data.get('last_used_at') else None

        return APIKey(
            key_id=data['key_id'],
            key_hash=data['key_hash'],
            name=data['name'],
            description=data['description'],
            scopes=scopes,
            status=APIKeyStatus(data['status']),
            created_at=created_at,
            expires_at=expires_at,
            last_used_at=last_used_at,
            usage_count=int(data.get('usage_count', 0)),
            rate_limit=json.loads(data.get('rate_limit', '{}')),
            metadata=json.loads(data.get('metadata', '{}')),
            created_by=data.get('created_by')
        )


class APIKeyManager:
    """Manages API key operations."""

    def __init__(self, provider: APIKeyProvider):
        self.provider = provider

    async def create_api_key(
        self,
        name: str,
        description: str,
        scopes: list[APIKeyScope],
        expires_in_days: int | None = None,
        rate_limit: dict[str, int] | None = None,
        created_by: str = None,
        metadata: dict[str, Any] | None = None
    ) -> tuple[str, APIKey]:
        """Create a new API key."""
        key_id = f"key_{secrets.token_urlsafe(8)}"

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            key_id=key_id,
            key_hash="",  # Will be set by provider
            name=name,
            description=description,
            scopes=scopes,
            status=APIKeyStatus.ACTIVE,
            expires_at=expires_at,
            rate_limit=rate_limit,
            metadata=metadata,
            created_by=created_by
        )

        actual_key = await self.provider.create_key(api_key)
        return actual_key, api_key

    async def validate_api_key(self, api_key: str) -> APIKey | None:
        """Validate an API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Get key from provider
        stored_key = await self.provider.get_key_by_hash(key_hash)
        if not stored_key:
            return None

        # Check status
        if stored_key.status != APIKeyStatus.ACTIVE:
            return None

        # Check expiry
        if stored_key.expires_at and datetime.utcnow() > stored_key.expires_at:
            # Mark as expired
            stored_key.status = APIKeyStatus.EXPIRED
            await self.provider.update_key(stored_key)
            return None

        # Update usage stats
        stored_key.last_used_at = datetime.utcnow()
        stored_key.usage_count += 1
        await self.provider.update_key(stored_key)

        return stored_key

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        api_key = await self.provider.get_key(key_id)
        if api_key:
            api_key.status = APIKeyStatus.SUSPENDED
            return await self.provider.update_key(api_key)
        return False

    async def rotate_key(self, key_id: str) -> str | None:
        """Rotate an API key (create new key, invalidate old)."""
        old_key = await self.provider.get_key(key_id)
        if not old_key:
            return None

        # Create new key with same properties
        new_key, _ = await self.create_api_key(
            name=old_key.name,
            description=f"Rotated from {key_id}",
            scopes=old_key.scopes,
            expires_in_days=None if not old_key.expires_at else (old_key.expires_at - datetime.utcnow()).days,
            rate_limit=old_key.rate_limit,
            created_by=old_key.created_by,
            metadata={**(old_key.metadata or {}), "rotated_from": key_id}
        )

        # Revoke old key
        await self.revoke_key(key_id)

        return new_key

    async def get_key_info(self, key_id: str) -> dict[str, Any] | None:
        """Get API key information."""
        api_key = await self.provider.get_key(key_id)
        return api_key.to_dict() if api_key else None

    async def list_user_keys(self, user_id: str) -> list[dict[str, Any]]:
        """List all keys for a user."""
        keys = await self.provider.list_keys(created_by=user_id)
        return [key.to_dict() for key in keys]


# Global API key manager
_api_key_manager: APIKeyManager | None = None


async def get_api_key_manager() -> APIKeyManager:
    """Get or create the global API key manager."""
    global _api_key_manager

    if not _api_key_manager:
        settings = get_settings()

        if settings.REDIS_URL:
            provider = RedisAPIKeyProvider(settings.REDIS_URL)
            logger.info("API keys: Using Redis provider")
        else:
            # Fallback to memory provider for development
            provider = MemoryAPIKeyProvider()
            logger.info("API keys: Using memory provider")

        _api_key_manager = APIKeyManager(provider)

    return _api_key_manager


# Authentication dependencies
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    api_key: str = Depends(api_key_header)
) -> APIKey:
    """Dependency to get and validate API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    manager = await get_api_key_manager()
    validated_key = await manager.validate_api_key(api_key)

    if not validated_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return validated_key


async def get_api_key_with_scope(required_scope: APIKeyScope):
    """Dependency to get API key with required scope."""
    async def dependency(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        if required_scope not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key requires '{required_scope.value}' scope"
            )
        return api_key

    return dependency


# Scope-specific dependencies
require_read_scope = Depends(get_api_key_with_scope(APIKeyScope.READ))
require_write_scope = Depends(get_api_key_with_scope(APIKeyScope.WRITE))
require_admin_scope = Depends(get_api_key_with_scope(APIKeyScope.ADMIN))
require_analyze_scope = Depends(get_api_key_with_scope(APIKeyScope.ANALYZE))
require_search_scope = Depends(get_api_key_with_scope(APIKeyScope.SEARCH))


# Rate limiting integration with API keys
class APIKeyRateLimiter:
    """Rate limiter that uses API key configuration."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        api_key: APIKey,
        endpoint: str,
        window: int = 60
    ) -> tuple[bool, dict[str, Any]]:
        """Check if API key is within rate limits."""
        if not api_key.rate_limit:
            # Default limits
            limits = {
                "requests_per_minute": 100,
                "requests_per_hour": 1000,
                "requests_per_day": 10000
            }
        else:
            limits = api_key.rate_limit

        # Check per-minute limit
        minute_key = f"rate_limit:{api_key.key_id}:{endpoint}:minute"
        minute_count = await self.redis.incr(minute_key)
        await self.redis.expire(minute_key, 60)

        if minute_count > limits.get("requests_per_minute", 100):
            return False, {
                "limit": limits["requests_per_minute"],
                "window": 60,
                "remaining": 0,
                "retry_after": 60
            }

        # Check per-hour limit
        hour_key = f"rate_limit:{api_key.key_id}:{endpoint}:hour"
        hour_count = await self.redis.incr(hour_key)
        await self.redis.expire(hour_key, 3600)

        if hour_count > limits.get("requests_per_hour", 1000):
            return False, {
                "limit": limits["requests_per_hour"],
                "window": 3600,
                "remaining": 0,
                "retry_after": 3600
            }

        return True, {
            "limit": limits["requests_per_minute"],
            "window": 60,
            "remaining": limits["requests_per_minute"] - minute_count,
            "retry_after": 0
        }


# Memory fallback provider for development
class MemoryAPIKeyProvider(APIKeyProvider):
    """In-memory API key provider for development."""

    def __init__(self):
        self.keys: dict[str, APIKey] = {}
        self.hash_lookup: dict[str, str] = {}
        self.user_keys: dict[str, list[str]] = {}

    async def create_key(self, api_key: APIKey) -> str:
        """Create a new API key."""
        actual_key = f"mg_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

        api_key.key_hash = key_hash
        self.keys[api_key.key_id] = api_key
        self.hash_lookup[key_hash] = api_key.key_id

        if api_key.created_by:
            if api_key.created_by not in self.user_keys:
                self.user_keys[api_key.created_by] = []
            self.user_keys[api_key.created_by].append(api_key.key_id)

        return actual_key

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID."""
        return self.keys.get(key_id)

    async def get_key_by_hash(self, key_hash: str) -> APIKey | None:
        """Get API key by hash."""
        key_id = self.hash_lookup.get(key_hash)
        if key_id:
            return self.keys.get(key_id)
        return None

    async def update_key(self, api_key: APIKey) -> bool:
        """Update an API key."""
        if api_key.key_id in self.keys:
            self.keys[api_key.key_id] = api_key
            return True
        return False

    async def delete_key(self, key_id: str) -> bool:
        """Delete an API key."""
        api_key = self.keys.get(key_id)
        if api_key:
            del self.keys[key_id]
            del self.hash_lookup[api_key.key_hash]

            if api_key.created_by and api_key.created_by in self.user_keys:
                self.user_keys[api_key.created_by].remove(key_id)

            return True
        return False

    async def list_keys(self, created_by: str = None) -> list[APIKey]:
        """List API keys."""
        if created_by:
            key_ids = self.user_keys.get(created_by, [])
            return [self.keys[kid] for kid in key_ids if kid in self.keys]
        return list(self.keys.values())
