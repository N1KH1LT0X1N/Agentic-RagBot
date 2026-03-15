"""
Feature flags system for MediGuard AI.
Allows dynamic enabling/disabling of features without code deployment.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis

from src.settings import get_settings

logger = logging.getLogger(__name__)


class FeatureStatus(Enum):
    """Feature flag status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONDITIONAL = "conditional"


class ConditionOperator(Enum):
    """Operators for conditional flags."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    REGEX = "regex"


@dataclass
class FeatureFlag:
    """Feature flag definition."""
    key: str
    status: FeatureStatus
    description: str
    conditions: dict[str, Any] | None = None
    rollout_percentage: int = 100
    enabled_for: list[str] | None = None
    disabled_for: list[str] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = None
    updated_at: datetime = None
    expires_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class FeatureFlagProvider:
    """Base class for feature flag providers."""

    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a feature flag by key."""
        raise NotImplementedError

    async def set_flag(self, flag: FeatureFlag) -> bool:
        """Set a feature flag."""
        raise NotImplementedError

    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        raise NotImplementedError

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        raise NotImplementedError


class RedisFeatureFlagProvider(FeatureFlagProvider):
    """Redis-based feature flag provider."""

    def __init__(self, redis_url: str, key_prefix: str = "feature_flags:"):
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

    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get feature flag from Redis."""
        try:
            client = await self._get_client()
            data = await client.get(self._make_key(key))

            if data:
                flag_dict = json.loads(data)
                # Convert datetime strings back to datetime objects
                if flag_dict.get('created_at'):
                    flag_dict['created_at'] = datetime.fromisoformat(flag_dict['created_at'])
                if flag_dict.get('updated_at'):
                    flag_dict['updated_at'] = datetime.fromisoformat(flag_dict['updated_at'])
                if flag_dict.get('expires_at'):
                    flag_dict['expires_at'] = datetime.fromisoformat(flag_dict['expires_at'])

                return FeatureFlag(**flag_dict)

            return None
        except Exception as e:
            logger.error(f"Error getting flag {key}: {e}")
            return None

    async def set_flag(self, flag: FeatureFlag) -> bool:
        """Set feature flag in Redis."""
        try:
            client = await self._get_client()

            # Prepare data for JSON serialization
            flag_dict = asdict(flag)
            # Convert datetime objects to ISO strings
            if flag_dict.get('created_at'):
                flag_dict['created_at'] = flag.created_at.isoformat()
            if flag_dict.get('updated_at'):
                flag_dict['updated_at'] = flag.updated_at.isoformat()
            if flag_dict.get('expires_at'):
                flag_dict['expires_at'] = flag.expires_at.isoformat()

            # Convert enum to string
            flag_dict['status'] = flag.status.value

            await client.set(
                self._make_key(flag.key),
                json.dumps(flag_dict),
                ex=86400 * 30  # 30 days TTL
            )

            # Also add to index
            await client.sadd(f"{self.key_prefix}index", flag.key)

            return True
        except Exception as e:
            logger.error(f"Error setting flag {flag.key}: {e}")
            return False

    async def delete_flag(self, key: str) -> bool:
        """Delete feature flag from Redis."""
        try:
            client = await self._get_client()

            # Delete flag
            result = await client.delete(self._make_key(key))

            # Remove from index
            await client.srem(f"{self.key_prefix}index", key)

            return result > 0
        except Exception as e:
            logger.error(f"Error deleting flag {key}: {e}")
            return False

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        try:
            client = await self._get_client()
            keys = await client.smembers(f"{self.key_prefix}index")

            flags = []
            for key in keys:
                flag = await self.get_flag(key)
                if flag:
                    flags.append(flag)

            return flags
        except Exception as e:
            logger.error(f"Error listing flags: {e}")
            return []


class MemoryFeatureFlagProvider(FeatureFlagProvider):
    """In-memory feature flag provider for development/testing."""

    def __init__(self):
        self.flags: dict[str, FeatureFlag] = {}

    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get feature flag from memory."""
        return self.flags.get(key)

    async def set_flag(self, flag: FeatureFlag) -> bool:
        """Set feature flag in memory."""
        self.flags[flag.key] = flag
        return True

    async def delete_flag(self, key: str) -> bool:
        """Delete feature flag from memory."""
        if key in self.flags:
            del self.flags[key]
            return True
        return False

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        return list(self.flags.values())


class FeatureFlagManager:
    """Main feature flag manager."""

    def __init__(self, provider: FeatureFlagProvider):
        self.provider = provider
        self._cache: dict[str, FeatureFlag] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update: dict[str, datetime] = {}

    async def is_enabled(
        self,
        key: str,
        context: dict[str, Any] | None = None,
        user_id: str | None = None
    ) -> bool:
        """Check if a feature is enabled."""
        flag = await self._get_flag_cached(key)

        if not flag:
            # Default to disabled for unknown flags
            logger.warning(f"Unknown feature flag: {key}")
            return False

        # Check if flag has expired
        if flag.expires_at and datetime.utcnow() > flag.expires_at:
            return False

        # Check status
        if flag.status == FeatureStatus.DISABLED:
            return False
        elif flag.status == FeatureStatus.ENABLED:
            # Apply rollout percentage
            if flag.rollout_percentage < 100:
                if user_id:
                    # Consistent hashing based on user_id
                    hash_val = int(hash(user_id) % 100)
                    return hash_val < flag.rollout_percentage
                else:
                    # Random rollout
                    import random
                    return random.randint(1, 100) <= flag.rollout_percentage
            return True
        elif flag.status == FeatureStatus.CONDITIONAL:
            return self._evaluate_conditions(flag, context or {}, user_id)

        return False

    def _evaluate_conditions(
        self,
        flag: FeatureFlag,
        context: dict[str, Any],
        user_id: str | None = None
    ) -> bool:
        """Evaluate conditional flag logic."""
        if not flag.conditions:
            return True

        # Check user-specific conditions
        if user_id:
            if flag.enabled_for and user_id not in flag.enabled_for:
                return False
            if flag.disabled_for and user_id in flag.disabled_for:
                return False

        # Evaluate custom conditions
        for condition in flag.conditions.get("rules", []):
            field = condition.get("field")
            operator = ConditionOperator(condition.get("operator"))
            value = condition.get("value")

            # Get context value
            context_value = self._get_nested_value(context, field)

            if not self._evaluate_operator(context_value, operator, value):
                return False

        return True

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """Get nested value from dict using dot notation."""
        keys = path.split(".")
        current = obj

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _evaluate_operator(
        self,
        actual: Any,
        operator: ConditionOperator,
        expected: Any
    ) -> bool:
        """Evaluate a condition operator."""
        if operator == ConditionOperator.EQUALS:
            return actual == expected
        elif operator == ConditionOperator.NOT_EQUALS:
            return actual != expected
        elif operator == ConditionOperator.GREATER_THAN:
            return actual > expected
        elif operator == ConditionOperator.LESS_THAN:
            return actual < expected
        elif operator == ConditionOperator.IN:
            return actual in expected
        elif operator == ConditionOperator.NOT_IN:
            return actual not in expected
        elif operator == ConditionOperator.CONTAINS:
            return expected in str(actual)
        elif operator == ConditionOperator.REGEX:
            import re
            return bool(re.search(expected, str(actual)))

        return False

    async def _get_flag_cached(self, key: str) -> FeatureFlag | None:
        """Get flag with caching."""
        now = datetime.utcnow()

        # Check cache
        if key in self._cache:
            last_update = self._last_cache_update.get(key, datetime.min)
            if now - last_update < self._cache_ttl:
                return self._cache[key]

        # Fetch from provider
        flag = await self.provider.get_flag(key)

        # Update cache
        if flag:
            self._cache[key] = flag
            self._last_cache_update[key] = now

        return flag

    async def create_flag(self, flag: FeatureFlag) -> bool:
        """Create a new feature flag."""
        # Clear cache
        if flag.key in self._cache:
            del self._cache[flag.key]

        return await self.provider.set_flag(flag)

    async def update_flag(self, flag: FeatureFlag) -> bool:
        """Update an existing feature flag."""
        flag.updated_at = datetime.utcnow()

        # Clear cache
        if flag.key in self._cache:
            del self._cache[flag.key]

        return await self.provider.set_flag(flag)

    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        # Clear cache
        if key in self._cache:
            del self._cache[key]

        return await self.provider.delete_flag(key)

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        return await self.provider.list_flags()

    async def get_flag_info(self, key: str) -> dict[str, Any] | None:
        """Get detailed flag information."""
        flag = await self._get_flag_cached(key)

        if not flag:
            return None

        return {
            "key": flag.key,
            "status": flag.status.value,
            "description": flag.description,
            "rollout_percentage": flag.rollout_percentage,
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat(),
            "expires_at": flag.expires_at.isoformat() if flag.expires_at else None,
            "metadata": flag.metadata
        }


# Global feature flag manager
_flag_manager: FeatureFlagManager | None = None


async def get_feature_flag_manager() -> FeatureFlagManager:
    """Get or create the global feature flag manager."""
    global _flag_manager

    if not _flag_manager:
        settings = get_settings()

        if settings.REDIS_URL:
            provider = RedisFeatureFlagProvider(settings.REDIS_URL)
            logger.info("Feature flags: Using Redis provider")
        else:
            provider = MemoryFeatureFlagProvider()
            logger.info("Feature flags: Using memory provider")

        _flag_manager = FeatureFlagManager(provider)

        # Initialize default flags
        await _initialize_default_flags()

    return _flag_manager


async def _initialize_default_flags():
    """Initialize default feature flags."""
    default_flags = [
        FeatureFlag(
            key="advanced_analytics",
            status=FeatureStatus.ENABLED,
            description="Enable advanced analytics dashboard",
            rollout_percentage=100
        ),
        FeatureFlag(
            key="beta_features",
            status=FeatureStatus.CONDITIONAL,
            description="Enable beta features for specific users",
            enabled_for=["admin@mediguard.com", "beta-tester@mediguard.com"],
            conditions={
                "rules": [
                    {
                        "field": "user.role",
                        "operator": "in",
                        "value": ["admin", "beta_tester"]
                    }
                ]
            }
        ),
        FeatureFlag(
            key="new_ui_components",
            status=FeatureStatus.ENABLED,
            description="Enable new UI components",
            rollout_percentage=50  # Gradual rollout
        ),
        FeatureFlag(
            key="experimental_llm",
            status=FeatureStatus.DISABLED,
            description="Enable experimental LLM model",
            metadata={
                "model_name": "gpt-4-turbo",
                "experimental": True
            }
        ),
        FeatureFlag(
            key="enhanced_caching",
            status=FeatureStatus.ENABLED,
            description="Enable enhanced caching strategies",
            rollout_percentage=100
        ),
        FeatureFlag(
            key="real_time_collaboration",
            status=FeatureStatus.CONDITIONAL,
            description="Enable real-time collaboration features",
            conditions={
                "rules": [
                    {
                        "field": "subscription.plan",
                        "operator": "eq",
                        "value": "enterprise"
                    }
                ]
            }
        )
    ]

    manager = await get_feature_flag_manager()

    for flag in default_flags:
        existing = await manager.provider.get_flag(flag.key)
        if not existing:
            await manager.create_flag(flag)
            logger.info(f"Created default feature flag: {flag.key}")


# Decorator for feature flags
def feature_flag(
    key: str,
    fallback_return: Any = None,
    fallback_callable: callable | None = None
):
    """Decorator to conditionally enable features."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            return _async_feature_flag_decorator(key, func, fallback_return, fallback_callable)
        else:
            return _sync_feature_flag_decorator(key, func, fallback_return, fallback_callable)

    return decorator


def _async_feature_flag_decorator(key: str, func, fallback_return: Any, fallback_callable: callable | None):
    """Async feature flag decorator."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        manager = await get_feature_flag_manager()

        # Extract context from kwargs if available
        context = kwargs.get("feature_context", {})
        user_id = kwargs.get("user_id") or getattr(kwargs.get("request"), "user_id", None)

        if await manager.is_enabled(key, context, user_id):
            return await func(*args, **kwargs)
        else:
            if fallback_callable:
                return await fallback_callable(*args, **kwargs)
            return fallback_return

    return wrapper


def _sync_feature_flag_decorator(key: str, func, fallback_return: Any, fallback_callable: callable | None):
    """Sync feature flag decorator."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create event loop for async call
        loop = asyncio.get_event_loop()

        async def check_flag():
            manager = await get_feature_flag_manager()
            context = kwargs.get("feature_context", {})
            user_id = kwargs.get("user_id")
            return await manager.is_enabled(key, context, user_id)

        is_enabled = loop.run_until_complete(check_flag())

        if is_enabled:
            return func(*args, **kwargs)
        else:
            if fallback_callable:
                return fallback_callable(*args, **kwargs)
            return fallback_return

    return wrapper


# Utility functions
async def is_feature_enabled(
    key: str,
    context: dict[str, Any] | None = None,
    user_id: str | None = None
) -> bool:
    """Check if a feature is enabled."""
    manager = await get_feature_flag_manager()
    return await manager.is_enabled(key, context, user_id)


async def enable_feature(key: str, user_id: str | None = None) -> bool:
    """Enable a feature flag."""
    manager = await get_feature_flag_manager()
    flag = await manager.get_flag_cached(key)

    if flag:
        flag.status = FeatureStatus.ENABLED
        flag.rollout_percentage = 100
        return await manager.update_flag(flag)

    return False


async def disable_feature(key: str) -> bool:
    """Disable a feature flag."""
    manager = await get_feature_flag_manager()
    flag = await manager.get_flag_cached(key)

    if flag:
        flag.status = FeatureStatus.DISABLED
        return await manager.update_flag(flag)

    return False


async def set_feature_rollout(key: str, percentage: int) -> bool:
    """Set feature rollout percentage."""
    manager = await get_feature_flag_manager()
    flag = await manager.get_flag_cached(key)

    if flag:
        flag.rollout_percentage = max(0, min(100, percentage))
        flag.status = FeatureStatus.ENABLED
        return await manager.update_flag(flag)

    return False
