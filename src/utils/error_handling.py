"""
Enhanced error handling and logging system for MediGuard AI.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"


class MediGuardError(Exception):
    """Base exception class for MediGuard AI."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()
        self.traceback_str = traceback.format_exc()

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
            "traceback": self.traceback_str if self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }


class ValidationError(MediGuardError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, value: Any | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details,
            **kwargs
        )


class ProcessingError(MediGuardError):
    """Raised when processing fails."""

    def __init__(self, message: str, step: str | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if step:
            details["step"] = step
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )


class DatabaseError(MediGuardError):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: str | None = None, table: str | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )


class ExternalServiceError(MediGuardError):
    """Raised when external service calls fail."""

    def __init__(self, message: str, service: str | None = None, status_code: int | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )


class RateLimitError(MediGuardError):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, limit: int | None = None, window: int | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )


class StructuredLogger:
    """Enhanced logger with structured output."""

    def __init__(self, name: str, log_file: Path | None = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

        # Custom formatter
        formatter = StructuredFormatter()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

        # Add standard logging methods for compatibility
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.debug = self.logger.debug

    def log_error(self, error: MediGuardError, context: dict[str, Any] | None = None):
        """Log an error with structured format."""
        log_data = {
            "event": "error",
            "error": error.to_dict(),
            "context": context or {}
        }
        self.logger.error(json.dumps(log_data, default=str))

    def log_event(
        self,
        event_name: str,
        level: str = "info",
        message: str | None = None,
        **kwargs
    ):
        """Log a structured event."""
        log_data = {
            "event": event_name,
            "message": message or event_name,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        getattr(self.logger, level)(json.dumps(log_data, default=str))

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
        **kwargs
    ):
        """Log HTTP request."""
        self.log_event(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            **kwargs
        )

    def log_workflow(
        self,
        workflow_name: str,
        status: str,
        duration_ms: float,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        **kwargs
    ):
        """Log workflow execution."""
        self.log_event(
            "workflow_execution",
            workflow=workflow_name,
            status=status,
            duration_ms=duration_ms,
            input_hash=str(hash(str(input_data)))[:8] if input_data else None,
            output_hash=str(hash(str(output_data)))[:8] if output_data else None,
            **kwargs
        )


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record):
        try:
            # Try to parse as JSON first
            data = json.loads(record.getMessage())
            return json.dumps(data, default=str)
        except (json.JSONDecodeError, ValueError):
            # Fallback to standard format
            return super().format(record)


class ErrorTracker:
    """Track and analyze errors for monitoring."""

    def __init__(self):
        self.error_counts: dict[str, int] = {}
        self.error_details: dict[str, MediGuardError] = {}

    def track_error(self, error: MediGuardError):
        """Track an error occurrence."""
        key = f"{error.category.value}:{error.error_code}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.error_details[key] = error

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": dict(self.error_counts),
            "most_common": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def clear(self):
        """Clear tracked errors."""
        self.error_counts.clear()
        self.error_details.clear()


# Global error tracker instance
error_tracker = ErrorTracker()


def handle_errors(
    default_error_code: str | None = None,
    default_category: ErrorCategory = ErrorCategory.SYSTEM,
    default_severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = True
):
    """Decorator for consistent error handling."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MediGuardError:
                # Re-raise our custom errors
                if reraise:
                    raise
                return None
            except Exception as e:
                # Convert to MediGuardError
                error = MediGuardError(
                    message=f"Unexpected error in {func.__name__}: {e!s}",
                    error_code=default_error_code or f"{func.__name__}_ERROR",
                    category=default_category,
                    severity=default_severity,
                    cause=e
                )
                error_tracker.track_error(error)

                # Log the error
                logger = logging.getLogger("mediguard")
                if hasattr(logger, 'log_error'):
                    logger.log_error(error)
                else:
                    logger.error(str(error))

                if reraise:
                    raise error from None
                return None
        return wrapper
    return decorator


def setup_logging(log_level: str = "INFO", log_file: Path | None = None):
    """Setup enhanced logging for the application."""
    # Create logs directory if needed
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Add console handler
    root_logger.addHandler(console_handler)

    # Set structured logger for main module
    return StructuredLogger("mediguard", log_file)


# Context manager for error handling
class ErrorContext:
    """Context manager for error handling and logging."""

    def __init__(
        self,
        operation: str,
        logger: StructuredLogger = None,
        **context
    ):
        self.operation = operation
        self.logger = logger or logging.getLogger("mediguard")
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        if hasattr(self.logger, 'log_event'):
            self.logger.log_event(
                "operation_start",
                operation=self.operation,
                **self.context
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        if exc_type is None:
            # Success
            if hasattr(self.logger, 'log_event'):
                self.logger.log_event(
                    "operation_success",
                    operation=self.operation,
                    duration_ms=duration,
                    **self.context
                )
        else:
            # Error occurred
            if isinstance(exc_val, MediGuardError):
                error = exc_val
            else:
                error = MediGuardError(
                    message=str(exc_val),
                    error_code=f"{self.operation}_ERROR",
                    cause=exc_val
                )

            error_tracker.track_error(error)

            if hasattr(self.logger, 'log_error'):
                self.logger.log_error(error, context=self.context)

        return False  # Don't suppress exceptions
