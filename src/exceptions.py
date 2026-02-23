"""
MediGuard AI — Domain Exception Hierarchy

Production-grade exception classes for the medical RAG system.
Each service layer raises its own exception type so callers can handle
failures precisely without leaking implementation details.
"""

from typing import Any, Dict, Optional


# ── Base ──────────────────────────────────────────────────────────────────────

class MediGuardError(Exception):
    """Root exception for the entire MediGuard AI application."""

    def __init__(self, message: str = "", *, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


# ── Configuration / startup ──────────────────────────────────────────────────

class ConfigurationError(MediGuardError):
    """Raised when a required setting is missing or invalid."""


class ServiceInitError(MediGuardError):
    """Raised when a service fails to initialise during app startup."""


# ── Database ─────────────────────────────────────────────────────────────────

class DatabaseError(MediGuardError):
    """Base class for all database-related errors."""


class ConnectionError(DatabaseError):
    """Could not connect to PostgreSQL."""


class RecordNotFoundError(DatabaseError):
    """Expected record does not exist."""


# ── Search engine ────────────────────────────────────────────────────────────

class SearchError(MediGuardError):
    """Base class for search-engine (OpenSearch) errors."""


class IndexNotFoundError(SearchError):
    """The requested OpenSearch index does not exist."""


class SearchQueryError(SearchError):
    """The search query was malformed or returned an error."""


# ── Embeddings ───────────────────────────────────────────────────────────────

class EmbeddingError(MediGuardError):
    """Failed to generate embeddings."""


class EmbeddingProviderError(EmbeddingError):
    """The upstream embedding provider returned an error."""


# ── PDF / document parsing ───────────────────────────────────────────────────

class PDFParsingError(MediGuardError):
    """Base class for PDF-processing errors."""


class PDFExtractionError(PDFParsingError):
    """Could not extract text from a PDF document."""


class PDFValidationError(PDFParsingError):
    """Uploaded PDF failed validation (size, format, etc.)."""


# ── LLM / Ollama ─────────────────────────────────────────────────────────────

class LLMError(MediGuardError):
    """Base class for LLM-related errors."""


class OllamaConnectionError(LLMError):
    """Could not reach the Ollama server."""


class OllamaModelNotFoundError(LLMError):
    """The requested Ollama model is not pulled/available."""


class LLMResponseError(LLMError):
    """The LLM returned an unparseable or empty response."""


# ── Biomarker domain ─────────────────────────────────────────────────────────

class BiomarkerError(MediGuardError):
    """Base class for biomarker-related errors."""


class BiomarkerValidationError(BiomarkerError):
    """A biomarker value is physiologically implausible."""


class BiomarkerNotFoundError(BiomarkerError):
    """The biomarker name is unknown to the system."""


# ── Medical analysis / workflow ──────────────────────────────────────────────

class AnalysisError(MediGuardError):
    """The clinical-analysis workflow encountered an error."""


class GuardrailError(MediGuardError):
    """A safety guardrail was triggered (input or output)."""


class OutOfScopeError(GuardrailError):
    """The user query falls outside the medical domain."""


# ── Cache ────────────────────────────────────────────────────────────────────

class CacheError(MediGuardError):
    """Base class for cache (Redis) errors."""


class CacheConnectionError(CacheError):
    """Could not connect to Redis."""


# ── Observability ────────────────────────────────────────────────────────────

class ObservabilityError(MediGuardError):
    """Langfuse or metrics reporting failed (non-fatal)."""


# ── Telegram bot ─────────────────────────────────────────────────────────────

class TelegramError(MediGuardError):
    """Error from the Telegram bot integration."""
