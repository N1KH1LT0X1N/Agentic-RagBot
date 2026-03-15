"""
Request/Response Validation Middleware for MediGuard AI.
Provides comprehensive validation and sanitization of API data.
"""

import asyncio
import json
import logging
import re
from typing import Any

import bleach
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ValidationRule:
    """Base validation rule."""

    def __init__(self, name: str, message: str = None):
        self.name = name
        self.message = message or f"Validation failed for {name}"

    def validate(self, value: Any) -> bool:
        """Validate the value."""
        raise NotImplementedError


class RequiredRule(ValidationRule):
    """Required field validation."""

    def validate(self, value: Any) -> bool:
        return value is not None and value != ""


class TypeRule(ValidationRule):
    """Type validation."""

    def __init__(self, expected_type: type, **kwargs):
        super().__init__("type")
        self.expected_type = expected_type

    def validate(self, value: Any) -> bool:
        try:
            if self.expected_type == bool and isinstance(value, str):
                return value.lower() in ('true', 'false', '1', '0')
            return isinstance(value, self.expected_type)
        except:
            return False


class RangeRule(ValidationRule):
    """Numeric range validation."""

    def __init__(self, min_val: float = None, max_val: float = None, **kwargs):
        super().__init__("range")
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any) -> bool:
        try:
            num_val = float(value)
            if self.min_val is not None and num_val < self.min_val:
                return False
            if self.max_val is not None and num_val > self.max_val:
                return False
            return True
        except:
            return False


class LengthRule(ValidationRule):
    """String length validation."""

    def __init__(self, min_length: int = None, max_length: int = None, **kwargs):
        super().__init__("length")
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any) -> bool:
        if not isinstance(value, (str, list)):
            return False
        length = len(value)
        if self.min_length is not None and length < self.min_length:
            return False
        if self.max_length is not None and length > self.max_length:
            return False
        return True


class PatternRule(ValidationRule):
    """Regex pattern validation."""

    def __init__(self, pattern: str, **kwargs):
        super().__init__("pattern")
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.pattern.match(value))


class EmailRule(PatternRule):
    """Email validation."""

    def __init__(self, **kwargs):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        super().__init__(pattern, **kwargs)
        self.name = "email"


class PhoneRule(PatternRule):
    """Phone number validation."""

    def __init__(self, **kwargs):
        pattern = r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[\s.-]?([0-9]{3})[\s.-]?([0-9]{4})$'
        super().__init__(pattern, **kwargs)
        self.name = "phone"


class PHIValidationRule(ValidationRule):
    """PHI (Protected Health Information) validation."""

    def __init__(self, allow_phi: bool = False, **kwargs):
        super().__init__("phi")
        self.allow_phi = allow_phi
        # Patterns for common PHI
        self.phi_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            (r'\b\d{10}\b', 'Phone Number'),
            (r'\b\d{3}-\d{3}-\d{4}\b', 'US Phone'),
            (r'\b[A-Z]{2}\d{4}\b', 'Medical Record'),
            (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', 'Date of Birth'),
        ]

    def validate(self, value: Any) -> bool:
        if self.allow_phi:
            return True

        if not isinstance(value, str):
            return True

        for pattern, phi_type in self.phi_patterns:
            if re.search(pattern, value):
                logger.warning(f"Potential PHI detected: {phi_type}")
                return False

        return True


class SanitizationRule:
    """Base sanitization rule."""

    def sanitize(self, value: Any) -> Any:
        """Sanitize the value."""
        raise NotImplementedError


class HTMLSanitizationRule(SanitizationRule):
    """HTML sanitization to prevent XSS."""

    def __init__(self, allowed_tags: list[str] = None, allowed_attributes: list[str] = None):
        self.allowed_tags = allowed_tags or ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
        self.allowed_attributes = allowed_attributes or []

    def sanitize(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        # Remove all HTML tags except allowed ones
        return bleach.clean(
            value,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True
        )


class SQLInjectionSanitizationRule(SanitizationRule):
    """SQL injection prevention."""

    def __init__(self):
        # Common SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]\w+['\"]\s*=\s*['\"]\w+['\"])",
            r"(--|#|\/\*|\*\/)",
            r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT|ONLOAD|ONERROR)\b)",
        ]
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_patterns]

    def sanitize(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        # Flag suspicious content
        for pattern in self.patterns:
            if pattern.search(value):
                logger.warning(f"Potential SQL injection detected: {value[:100]}")
                # Remove or escape dangerous characters
                value = re.sub(r"[;'\"\\]", "", value)

        return value


class ValidationSchema:
    """Validation schema for request/response data."""

    def __init__(self):
        self.rules: dict[str, list[ValidationRule]] = {}
        self.sanitizers: list[SanitizationRule] = []
        self.required_fields: list[str] = []

    def add_field(self, field_name: str, rules: list[ValidationRule] = None, required: bool = False):
        """Add field validation rules."""
        if rules:
            self.rules[field_name] = rules
        if required:
            self.required_fields.append(field_name)

    def add_sanitizer(self, sanitizer: SanitizationRule):
        """Add a sanitization rule."""
        self.sanitizers.append(sanitizer)

    def validate(self, data: dict[str, Any]) -> dict[str, list[str]]:
        """Validate data against schema."""
        errors = {}

        # Check required fields
        for field in self.required_fields:
            if field not in data or data[field] is None:
                errors[field] = errors.get(field, [])
                errors[field].append("Field is required")

        # Validate each field
        for field, rules in self.rules.items():
            if field in data:
                value = data[field]
                for rule in rules:
                    if not rule.validate(value):
                        errors[field] = errors.get(field, [])
                        errors[field].append(rule.message)

        return errors

    def sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize data."""
        sanitized = data.copy()

        # Apply field-specific sanitization
        for field, value in sanitized.items():
            if isinstance(value, str):
                for sanitizer in self.sanitizers:
                    sanitized[field] = sanitizer.sanitize(value)

        return sanitized


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation."""

    def __init__(
        self,
        app,
        schemas: dict[str, ValidationSchema] = None,
        strict_mode: bool = True,
        sanitize_all: bool = True
    ):
        super().__init__(app)
        self.schemas = schemas or {}
        self.strict_mode = strict_mode
        self.sanitize_all = sanitize_all

        # Default sanitizers
        self.default_sanitizers = [
            HTMLSanitizationRule(),
            SQLInjectionSanitizationRule()
        ]

    async def dispatch(self, request: Request, call_next):
        """Validate and sanitize request."""
        # Only validate POST, PUT, PATCH requests
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)

        try:
            # Get request body
            body = await request.body()

            if not body:
                return await call_next(request)

            # Parse JSON
            try:
                data = json.loads(body.decode())
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in request body"
                )

            # Get schema for this endpoint
            schema = self._get_schema_for_request(request)

            if schema:
                # Validate data
                errors = schema.validate(data)

                if errors:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "Validation failed",
                            "details": errors
                        }
                    )

                # Sanitize data
                if self.sanitize_all:
                    data = schema.sanitize(data)
                    # Update request body
                    request._body = json.dumps(data).encode()

            # Add validation metadata
            request.state.validated = True
            request.state.sanitized = self.sanitize_all

            return await call_next(request)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request validation error: {e}")
            if self.strict_mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request validation failed"
                )
            else:
                return await call_next(request)

    def _get_schema_for_request(self, request: Request) -> ValidationSchema | None:
        """Get validation schema for request endpoint."""
        path = request.url.path
        method = request.method.lower()

        # Try to match schema by path and method
        schema_key = f"{method}:{path}"
        return self.schemas.get(schema_key)


class ResponseValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for response validation."""

    def __init__(
        self,
        app,
        schemas: dict[str, ValidationSchema] = None,
        validate_success_only: bool = True
    ):
        super().__init__(app)
        self.schemas = schemas or {}
        self.validate_success_only = validate_success_only

    async def dispatch(self, request: Request, call_next):
        """Validate response."""
        response = await call_next(request)

        # Only validate JSON responses
        if response.headers.get("content-type") != "application/json":
            return response

        # Skip error responses if configured
        if self.validate_success_only and response.status_code >= 400:
            return response

        try:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Parse JSON
            data = json.loads(body.decode())

            # Get schema for this endpoint
            schema = self._get_schema_for_request(request)

            if schema:
                # Validate response data
                errors = schema.validate(data)

                if errors:
                    logger.error(f"Response validation failed: {errors}")
                    # Return error response
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={
                            "error": "Internal server error",
                            "message": "Response validation failed"
                        }
                    )

            # Recreate response with validated body
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json"
            )

        except Exception as e:
            logger.error(f"Response validation error: {e}")
            return response

    def _get_schema_for_request(self, request: Request) -> ValidationSchema | None:
        """Get validation schema for response endpoint."""
        path = request.url.path
        method = request.method.lower()

        schema_key = f"{method}:{path}:response"
        return self.schemas.get(schema_key)


# Predefined schemas for common endpoints
class CommonSchemas:
    """Common validation schemas."""

    @staticmethod
    def biomarker_schema() -> ValidationSchema:
        """Schema for biomarker data."""
        schema = ValidationSchema()

        # Add sanitizers
        schema.add_sanitizer(HTMLSanitizationRule())
        schema.add_sanitizer(SQLInjectionSanitizationRule())
        schema.add_sanitizer(PHIValidationRule(allow_phi=False))

        # Biomarker name rules
        schema.add_field("name", [
            RequiredRule(),
            TypeRule(str),
            LengthRule(min_length=1, max_length=100),
            PatternRule(r"^[a-zA-Z\s]+$")
        ], required=True)

        # Biomarker value rules
        schema.add_field("value", [
            RequiredRule(),
            TypeRule((int, float, str)),
            RangeRule(min_val=0, max_val=10000)
        ], required=True)

        # Unit rules
        schema.add_field("unit", [
            TypeRule(str),
            LengthRule(max_length=20)
        ])

        # Timestamp rules
        schema.add_field("timestamp", [
            TypeRule(str),
            PatternRule(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$")
        ])

        return schema

    @staticmethod
    def patient_info_schema() -> ValidationSchema:
        """Schema for patient information."""
        schema = ValidationSchema()

        # Add PHI-aware sanitizers
        schema.add_sanitizer(HTMLSanitizationRule())
        schema.add_sanitizer(SQLInjectionSanitizationRule())
        schema.add_sanitizer(PHIValidationRule(allow_phi=True))  # Allow PHI in patient context

        # Age validation
        schema.add_field("age", [
            TypeRule(int),
            RangeRule(min_val=0, max_val=150)
        ])

        # Gender validation
        schema.add_field("gender", [
            TypeRule(str),
            PatternRule(r"^(male|female|other)$", re.IGNORECASE)
        ])

        # Symptoms validation
        schema.add_field("symptoms", [
            TypeRule(list),
            LengthRule(max_length=10)
        ])

        # Medical history
        schema.add_field("medical_history", [
            TypeRule(str),
            LengthRule(max_length=1000)
        ])

        return schema

    @staticmethod
    def analysis_request_schema() -> ValidationSchema:
        """Schema for analysis requests."""
        schema = ValidationSchema()

        # Add sanitizers
        schema.add_sanitizer(HTMLSanitizationRule())
        schema.add_sanitizer(SQLInjectionSanitizationRule())
        schema.add_sanitizer(PHIValidationRule(allow_phi=False))

        # Biomarkers array
        schema.add_field("biomarkers", [
            RequiredRule(),
            TypeRule(dict),
            LengthRule(min_length=1, max_length=50)
        ], required=True)

        # Patient context
        schema.add_field("patient_context", [
            TypeRule(dict)
        ])

        # Analysis type
        schema.add_field("analysis_type", [
            TypeRule(str),
            PatternRule(r"^(basic|comprehensive|detailed)$")
        ])

        return schema


# Validation decorator
def validate_request(schema: ValidationSchema):
    """Decorator for request validation."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(request: Request, *args, **kwargs):
                # Check if already validated
                if getattr(request.state, 'validated', False):
                    return await func(request, *args, **kwargs)

                # Get request body
                body = await request.body()
                data = json.loads(body.decode())

                # Validate
                errors = schema.validate(data)
                if errors:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={"validation_errors": errors}
                    )

                # Sanitize
                data = schema.sanitize(data)

                return await func(request, *args, **kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


# Utility functions
def create_validation_config() -> dict[str, ValidationSchema]:
    """Create default validation configuration."""
    return {
        "post:/analyze/structured": CommonSchemas.analysis_request_schema(),
        "post:/analyze/natural": CommonSchemas.analysis_request_schema(),
        "post:/ask": ValidationSchema(),  # Basic schema for questions
        "post:/search": ValidationSchema(),  # Basic schema for search
        "post:/patient/register": CommonSchemas.patient_info_schema(),
        "put:/patient/update": CommonSchemas.patient_info_schema(),
    }


def sanitize_input(text: str, allow_html: bool = False) -> str:
    """Quick sanitization function."""
    if not isinstance(text, str):
        return str(text)

    # Remove potential SQL injection
    text = re.sub(r"[;'\"\\]", "", text)

    # Remove HTML if not allowed
    if not allow_html:
        text = bleach.clean(text, tags=[], strip=True)

    return text.strip()


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    pattern = r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[\s.-]?([0-9]{3})[\s.-]?([0-9]{4})$'
    return bool(re.match(pattern, phone))


def detect_phi(text: str) -> list[str]:
    """Detect potential PHI in text."""
    phi_types = []

    phi_patterns = [
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
        (r'\b\d{10}\b', 'Phone Number'),
        (r'\b[A-Z]{2}\d{4}\b', 'Medical Record'),
        (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', 'Date of Birth'),
    ]

    for pattern, phi_type in phi_patterns:
        if re.search(pattern, text):
            phi_types.append(phi_type)

    return phi_types
