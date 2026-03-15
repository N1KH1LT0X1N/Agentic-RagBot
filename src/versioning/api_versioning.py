"""
API Versioning System for MediGuard AI.
Provides backward compatibility and smooth API evolution.
"""

import inspect
import logging
import re
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any
from functools import wraps
from starlette.routing import Match

from fastapi import HTTPException, Request, status
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APIVersion(Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"
    LATEST = "latest"


class VersioningStrategy:
    """Base class for versioning strategies."""

    def get_version(self, request: Request) -> str | None:
        """Extract version from request."""
        raise NotImplementedError


class HeaderVersioning(VersioningStrategy):
    """Version extraction from headers."""

    def __init__(self, header_name: str = "API-Version"):
        self.header_name = header_name

    def get_version(self, request: Request) -> str | None:
        """Get version from header."""
        return request.headers.get(self.header_name)


class URLPathVersioning(VersioningStrategy):
    """Version extraction from URL path."""

    def __init__(self, prefix: str = "/api"):
        self.prefix = prefix

    def get_version(self, request: Request) -> str | None:
        """Get version from URL path."""
        path = request.url.path

        # Match /api/v1/... or /v1/...
        patterns = [
            rf"{self.prefix}/(v\d+)/",
            r"^/(v\d+)/"
        ]

        for pattern in patterns:
            match = re.search(pattern, path)
            if match:
                return match.group(1)

        return None


class QueryParameterVersioning(VersioningStrategy):
    """Version extraction from query parameters."""

    def __init__(self, param_name: str = "version"):
        self.param_name = param_name

    def get_version(self, request: Request) -> str | None:
        """Get version from query parameter."""
        return request.query_params.get(self.param_name)


class MediaTypeVersioning(VersioningStrategy):
    """Version extraction from Accept header."""

    def get_version(self, request: Request) -> str | None:
        """Get version from Accept header."""
        accept = request.headers.get("accept", "")

        # Look for application/vnd.mediguard.v1+json
        match = re.search(r"application/vnd\.mediguard\.(v\d+)\+json", accept)
        if match:
            return match.group(1)

        return None


class CompositeVersioning(VersioningStrategy):
    """Try multiple versioning strategies in order."""

    def __init__(self, strategies: list[VersioningStrategy]):
        self.strategies = strategies

    def get_version(self, request: Request) -> str | None:
        """Try each strategy in order."""
        for strategy in self.strategies:
            version = strategy.get_version(request)
            if version:
                return version
        return None


class APIVersionManager:
    """Manages API version routing and compatibility."""

    def __init__(self, default_version: str = "v1"):
        self.default_version = default_version
        self.version_handlers: dict[str, dict[str, Callable]] = {}
        self.deprecated_versions: dict[str, dict[str, Any]] = {}
        self.version_middleware: dict[str, list[Callable]] = {}

    def register_version(
        self,
        version: str,
        handlers: dict[str, Callable],
        deprecated: bool = False,
        sunset_date: datetime | None = None,
        migration_guide: str | None = None
    ):
        """Register a version with its handlers."""
        self.version_handlers[version] = handlers

        if deprecated:
            self.deprecated_versions[version] = {
                "deprecated": True,
                "sunset_date": sunset_date,
                "migration_guide": migration_guide,
                "warning": f"Version {version} is deprecated"
            }

    def add_middleware(self, version: str, middleware: Callable):
        """Add middleware for a specific version."""
        if version not in self.version_middleware:
            self.version_middleware[version] = []
        self.version_middleware[version].append(middleware)

    def get_handler(self, version: str, endpoint: str) -> Callable | None:
        """Get handler for version and endpoint."""
        version_handlers = self.version_handlers.get(version)
        if version_handlers:
            return version_handlers.get(endpoint)
        return None

    def is_deprecated(self, version: str) -> bool:
        """Check if version is deprecated."""
        return version in self.deprecated_versions

    def get_deprecation_info(self, version: str) -> dict[str, Any] | None:
        """Get deprecation information for a version."""
        return self.deprecated_versions.get(version)


class VersionedRoute(APIRoute):
    """Custom route that supports versioning."""

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        *,
        version: str = None,
        versions: dict[str, Callable] = None,
        **kwargs
    ):
        self.version = version
        self.versions = versions or {}
        super().__init__(path, endpoint, **kwargs)

    def match(self, scope: Dict[str, Any]) -> tuple[Match, Dict[str, Any]]:
        """Match route with version consideration."""
        # Get version from request
        request = Request(scope)
        version_manager = scope.get("version_manager")

        if version_manager:
            version = version_manager.get_version(request)

            # Check if we have a versioned handler
            if version and version in self.versions:
                # Store versioned endpoint
                scope["versioned_endpoint"] = self.versions[version]
                scope["matched_version"] = version

        return super().match(scope)


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning."""

    def __init__(
        self,
        app,
        versioning_strategy: VersioningStrategy = None,
        version_manager: APIVersionManager = None
    ):
        super().__init__(app)
        self.versioning_strategy = versioning_strategy or CompositeVersioning([
            HeaderVersioning(),
            URLPathVersioning(),
            QueryParameterVersioning(),
            MediaTypeVersioning()
        ])
        self.version_manager = version_manager or APIVersionManager()

    async def dispatch(self, request: Request, call_next):
        """Handle versioning logic."""
        # Extract version
        version = self.versioning_strategy.get_version(request)

        # Use default if no version specified
        if not version:
            version = self.version_manager.default_version

        # Validate version
        if version not in self.version_manager.version_handlers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Unsupported API version",
                    "version": version,
                    "supported_versions": list(self.version_manager.version_handlers.keys())
                }
            )

        # Add version to request state
        request.state.version = version
        request.state.version_manager = self.version_manager

        # Add deprecation warning if needed
        if self.version_manager.is_deprecated(version):
            deprecation_info = self.version_manager.get_deprecation_info(version)
            logger.warning(f"Deprecated API version {version} being used: {deprecation_info}")

        # Add version headers to response
        response = await call_next(request)
        response.headers["API-Version"] = version
        response.headers["Supported-Versions"] = ",".join(self.version_manager.version_handlers.keys())

        # Add deprecation header if needed
        if self.version_manager.is_deprecated(version):
            deprecation_info = self.version_manager.get_deprecation_info(version)
            response.headers["Deprecation"] = "true"
            if deprecation_info.get("sunset_date"):
                response.headers["Sunset"] = deprecation_info["sunset_date"].isoformat()

        return response


class VersionCompatibilityMixin:
    """Mixin for version compatibility helpers."""

    @staticmethod
    def transform_request_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
        """Transform v1 request format to v2."""
        # Example transformation
        if "patient_data" in data:
            # v1 used patient_data, v2 uses patient_context
            data["patient_context"] = data.pop("patient_data")

        if "biomarker_values" in data:
            # v1 used biomarker_values, v2 uses biomarkers
            data["biomarkers"] = data.pop("biomarker_values")

        return data

    @staticmethod
    def transform_response_v2_to_v1(data: dict[str, Any]) -> dict[str, Any]:
        """Transform v2 response to v1 format."""
        # Example transformation
        if "patient_context" in data:
            data["patient_data"] = data.pop("patient_context")

        if "biomarkers" in data:
            data["biomarker_values"] = data.pop("biomarkers")

        # Remove v2-only fields
        v2_only_fields = ["metadata", "trace_id", "version"]
        for field in v2_only_fields:
            data.pop(field, None)

        return data


class APIVersionRegistry:
    """Registry for managing API versions and their handlers."""

    def __init__(self):
        self.versions: dict[str, dict[str, Any]] = {}
        self.global_middleware: list[Callable] = []

    def version(
        self,
        version: str,
        deprecated: bool = False,
        sunset_date: datetime | None = None,
        migration_guide: str | None = None
    ):
        """Decorator to register a versioned endpoint."""
        def decorator(func):
            # Get the module and function name
            module_name = func.__module__
            func_name = func.__name__
            endpoint_key = f"{module_name}.{func_name}"

            # Initialize version if not exists
            if version not in self.versions:
                self.versions[version] = {
                    "handlers": {},
                    "deprecated": deprecated,
                    "sunset_date": sunset_date,
                    "migration_guide": migration_guide,
                    "middleware": []
                }

            # Register handler
            self.versions[version]["handlers"][endpoint_key] = func

            # Add version info to function
            func._api_version = version
            func._endpoint_key = endpoint_key

            return func

        return decorator

    def add_global_middleware(self, middleware: Callable):
        """Add middleware that applies to all versions."""
        self.global_middleware.append(middleware)

    def add_version_middleware(self, version: str, middleware: Callable):
        """Add middleware for a specific version."""
        if version in self.versions:
            self.versions[version]["middleware"].append(middleware)

    def get_version_info(self, version: str) -> dict[str, Any] | None:
        """Get information about a version."""
        return self.versions.get(version)

    def list_versions(self) -> list[dict[str, Any]]:
        """List all versions with their info."""
        return [
            {
                "version": version,
                **info
            }
            for version, info in self.versions.items()
        ]


# Global version registry
api_registry = APIVersionRegistry()


# Decorator for easy version registration
def api_version(
    version: str,
    deprecated: bool = False,
    sunset_date: datetime | None = None,
    migration_guide: str | None = None
):
    """Decorator to mark a function as a versioned API endpoint."""
    return api_registry.version(
        version=version,
        deprecated=deprecated,
        sunset_date=sunset_date,
        migration_guide=migration_guide
    )


# Version compatibility decorator
def backward_compatible(from_version: str, to_version: str):
    """Decorator to handle backward compatibility."""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Transform request if needed
                if hasattr(args[0], 'state') and args[0].state.version == from_version:
                    # Transform data
                    if 'data' in kwargs:
                        kwargs['data'] = VersionCompatibilityMixin.transform_request_v1_to_v2(kwargs['data'])

                # Call function
                result = await func(*args, **kwargs)

                # Transform response if needed
                if hasattr(args[0], 'state') and args[0].state.version == from_version:
                    result = VersionCompatibilityMixin.transform_response_v2_to_v1(result)

                return result

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Similar logic for sync functions
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


# Version negotiation utilities
def negotiate_version(request: Request, supported_versions: list[str]) -> str:
    """Negotiate the best version based on request."""
    # Try to extract version from various sources
    strategies = [
        HeaderVersioning(),
        URLPathVersioning(),
        QueryParameterVersioning(),
        MediaTypeVersioning()
    ]

    for strategy in strategies:
        version = strategy.get_version(request)
        if version and version in supported_versions:
            return version

    # Return default if no match
    return supported_versions[0]


# Version validation middleware
def validate_version(supported_versions: list[str]):
    """Middleware to validate API version."""
    def middleware(request: Request, call_next):
        version = getattr(request.state, 'version', None)

        if version and version not in supported_versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Unsupported API version",
                    "version": version,
                    "supported_versions": supported_versions
                }
            )

        return call_next(request)

    return middleware


# FastAPI integration
class VersionedAPIRouter:
    """Router that supports versioning out of the box."""

    def __init__(self, prefix: str = "", version: str = None):
        self.prefix = prefix
        self.version = version
        self.routes = []

    def add_route(self, path: str, endpoint: Callable, methods: list[str] = None):
        """Add a versioned route."""
        full_path = f"{self.prefix}{path}"

        # Add version to path if specified
        if self.version:
            full_path = f"/api/{self.version}{full_path}"

        # Store route info
        self.routes.append({
            "path": full_path,
            "endpoint": endpoint,
            "methods": methods or ["GET"],
            "version": self.version
        })

    def include_router(self, app):
        """Include this router in a FastAPI app."""
        for route in self.routes:
            app.add_api_route(
                route["path"],
                route["endpoint"],
                methods=route["methods"]
            )
