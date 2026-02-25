"""
MediGuard AI — Production Middlewares

HIPAA-aware audit logging, request timing, and security headers.
Designed for medical applications requiring compliance patterns.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("mediguard.audit")

# ---------------------------------------------------------------------------
# HIPAA Audit Logger
# ---------------------------------------------------------------------------

# Sensitive fields that should NEVER be logged
SENSITIVE_FIELDS = {
    "biomarkers", "patient_context", "patient_id", "age", "gender", "bmi",
    "ssn", "mrn", "name", "address", "phone", "email", "dob", "date_of_birth",
}

# Endpoints that require audit logging
AUDITABLE_ENDPOINTS = {
    "/analyze/natural",
    "/analyze/structured",
    "/ask",
    "/ask/stream",
    "/search",
}


def _hash_sensitive(value: str) -> str:
    """Create a one-way hash of sensitive data for audit trail without logging PHI."""
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def _redact_body(body_dict: dict) -> dict:
    """Redact sensitive fields from request body for logging."""
    redacted = {}
    for key, value in body_dict.items():
        if key.lower() in SENSITIVE_FIELDS:
            if isinstance(value, dict):
                redacted[key] = f"[REDACTED: {len(value)} fields]"
            elif isinstance(value, str):
                redacted[key] = f"[REDACTED: {len(value)} chars]"
            else:
                redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted


class HIPAAAuditMiddleware(BaseHTTPMiddleware):
    """
    HIPAA-compliant audit logging middleware.
    
    Features:
    - Generates unique request IDs for traceability
    - Logs request metadata WITHOUT PHI/biomarker values
    - Creates audit trail for all medical analysis requests
    - Tracks request timing and response status
    - Hashes sensitive identifiers for correlation
    
    Audit logs are structured JSON for easy SIEM integration.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Extract metadata safely
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")[:100]

        # Check if this endpoint needs audit logging
        needs_audit = any(path.startswith(ep) for ep in AUDITABLE_ENDPOINTS)

        # Pre-request audit entry
        audit_entry: dict[str, Any] = {
            "event": "request_start",
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "method": method,
            "path": path,
            "client_ip_hash": _hash_sensitive(client_ip),
            "user_agent_hash": _hash_sensitive(user_agent),
        }

        # Try to read request body for POST requests (without logging PHI)
        if needs_audit and method == "POST":
            try:
                body = await request.body()
                # Store body for re-reading by route handlers
                request._body = body
                if body:
                    body_dict = json.loads(body)
                    redacted = _redact_body(body_dict)
                    audit_entry["request_fields"] = list(redacted.keys())
                    # Log presence of biomarkers without values
                    if "biomarkers" in body_dict:
                        audit_entry["biomarker_count"] = len(body_dict["biomarkers"]) if isinstance(body_dict["biomarkers"], dict) else 1
            except Exception as exc:
                logger.debug("Failed to audit POST body: %s", exc)

        if needs_audit:
            logger.info("AUDIT_REQUEST: %s", json.dumps(audit_entry))

        # Process request
        response: Response = await call_next(request)

        # Post-request audit
        elapsed_ms = (time.time() - start_time) * 1000

        completion_entry = {
            "event": "request_complete",
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "elapsed_ms": round(elapsed_ms, 2),
        }

        if needs_audit:
            logger.info("AUDIT_COMPLETE: %s", json.dumps(completion_entry))

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers for HIPAA compliance.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        # Medical data should never be cached
        if any(ep in request.url.path for ep in AUDITABLE_ENDPOINTS):
            response.headers["Cache-Control"] = "no-store, private"

        return response
