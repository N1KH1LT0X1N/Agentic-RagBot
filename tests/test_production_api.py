"""
Tests for the production FastAPI app (src/main.py) — endpoint smoke tests.

These tests use FastAPI's TestClient with mocked backing services
so they run without Docker infrastructure.
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked services."""
    # We need to prevent the lifespan from actually connecting to services
    with patch("src.main.lifespan") as mock_lifespan:
        # Use a no-op lifespan
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _noop_lifespan(app):
            import time
            app.state.start_time = time.time()
            app.state.version = "2.0.0-test"
            app.state.opensearch_client = None
            app.state.embedding_service = None
            app.state.cache = None
            app.state.ollama_client = None
            app.state.tracer = None
            app.state.rag_service = None
            app.state.ragbot_service = None
            yield

        mock_lifespan.side_effect = _noop_lifespan

        from src.main import create_app
        app = create_app()
        app.router.lifespan_context = _noop_lifespan
        with TestClient(app) as tc:
            yield tc


def test_root(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "MediGuard AI"
    assert "endpoints" in data


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_ask_no_service(client: TestClient):
    """Without RAG service, /ask should return 503."""
    resp = client.post("/ask", json={"question": "What is diabetes?"})
    assert resp.status_code == 503


def test_search_no_service(client: TestClient):
    """Without OpenSearch, /search should return 503."""
    resp = client.post("/search", json={"query": "diabetes", "top_k": 5})
    assert resp.status_code == 503


def test_analyze_no_service(client: TestClient):
    """Without RagBot, /analyze/structured should return 503."""
    resp = client.post(
        "/analyze/structured",
        json={"biomarkers": {"Glucose": 185.0}},
    )
    assert resp.status_code == 503


def test_validation_error(client: TestClient):
    """Invalid request should return 422."""
    resp = client.post("/ask", json={"question": "ab"})  # too short
    assert resp.status_code == 422
