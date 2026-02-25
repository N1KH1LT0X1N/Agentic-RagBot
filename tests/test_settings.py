"""
Tests for src/settings.py — Pydantic Settings hierarchy.
"""

import os

import pytest


def test_settings_defaults(monkeypatch):
    """Settings should have sensible defaults without env vars."""
    # Clear ALL potential override env vars that might affect settings
    for env_var in list(os.environ.keys()):
        if any(prefix in env_var.upper() for prefix in [
            "OLLAMA__", "CHUNKING__", "EMBEDDING__", "OPENSEARCH__",
            "REDIS__", "API__", "LLM__", "LANGFUSE__", "TELEGRAM__"
        ]):
            monkeypatch.delenv(env_var, raising=False)

    # Clear any cached instance
    from src.settings import get_settings
    get_settings.cache_clear()

    settings = get_settings()
    # Test core settings that should always exist with valid values
    assert settings.api.port >= 1 and settings.api.port <= 65535
    assert "mediguard" in settings.postgres.database_url.lower()
    assert settings.opensearch.host  # Should have a host
    assert settings.redis.port >= 1
    # Accept any llama model variant (covers llama3.1:8b, llama3.2, etc)
    assert "llama" in settings.ollama.model.lower()
    assert settings.embedding.dimension > 0
    # Chunk size should match hardcoded default of 600 when no env vars
    assert settings.chunking.chunk_size == 600, f"Expected 600, got {settings.chunking.chunk_size}"


def test_settings_frozen():
    """Settings should be immutable."""
    from src.settings import get_settings
    get_settings.cache_clear()

    settings = get_settings()
    with pytest.raises(Exception):
        settings.api.port = 9999


def test_settings_singleton():
    """get_settings should return the same cached instance."""
    from src.settings import get_settings
    get_settings.cache_clear()

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
