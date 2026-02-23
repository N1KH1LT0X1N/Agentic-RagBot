"""
Tests for src/settings.py — Pydantic Settings hierarchy.
"""

import os
from unittest.mock import patch

import pytest


def test_settings_defaults():
    """Settings should have sensible defaults without env vars."""
    # Clear any cached instance
    from src.settings import get_settings
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.api.port == 8000
    assert "mediguard" in settings.postgres.database_url
    assert "localhost" in settings.opensearch.host
    assert settings.redis.port == 6379
    assert settings.ollama.model == "llama3.1:8b"
    assert settings.embedding.dimension == 1024
    assert settings.chunking.chunk_size == 600


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
