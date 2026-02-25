"""
Tests for src/exceptions.py — domain exception hierarchy.
"""


from src.exceptions import (
    AnalysisError,
    BiomarkerError,
    CacheError,
    DatabaseError,
    EmbeddingError,
    GuardrailError,
    LLMError,
    MediGuardError,
    ObservabilityError,
    OllamaConnectionError,
    OutOfScopeError,
    PDFParsingError,
    SearchError,
    TelegramError,
)


def test_all_exceptions_inherit_from_root():
    """Every domain exception should inherit from MediGuardError."""
    for exc_cls in [
        DatabaseError, SearchError, EmbeddingError, PDFParsingError,
        LLMError, OllamaConnectionError, BiomarkerError, AnalysisError,
        GuardrailError, OutOfScopeError, CacheError, ObservabilityError,
        TelegramError,
    ]:
        assert issubclass(exc_cls, MediGuardError), f"{exc_cls.__name__} must inherit MediGuardError"


def test_ollama_inherits_llm():
    assert issubclass(OllamaConnectionError, LLMError)


def test_exception_message():
    exc = SearchError("OpenSearch timeout")
    assert str(exc) == "OpenSearch timeout"
    assert isinstance(exc, MediGuardError)
