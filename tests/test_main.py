"""Tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from unittest.mock import Mock, patch

from src.main import create_app, lifespan


class TestMainApp:
    """Test main FastAPI application."""

    def test_create_app(self):
        """Test app creation."""
        app = create_app()
        
        assert app is not None
        assert app.title == "MediGuard AI"
        assert app.version == "2.0.0"

    @pytest.mark.asyncio
    @patch('src.main.logger')
    @patch('src.main.get_settings')
    async def test_lifespan_startup(self, mock_settings, mock_logger):
        """Test lifespan context manager startup."""
        from unittest.mock import MagicMock, patch
        
        # Mock all service imports to avoid heavy initialization
        with patch('src.services.opensearch.client.make_opensearch_client'), \
             patch('src.services.embeddings.service.make_embedding_service'), \
             patch('src.services.cache.redis_cache.make_redis_cache'), \
             patch('src.services.ollama.client.make_ollama_client'), \
             patch('src.services.langfuse.tracer.make_langfuse_tracer'), \
             patch('src.services.agents.agentic_rag.AgenticRAGService'), \
             patch('src.workflow.create_guild'), \
             patch('src.services.extraction.service.make_extraction_service'):
            
            app = MagicMock()
            state = MagicMock()
            app.state = state
            
            async with lifespan(app):
                # Check startup actions
                assert hasattr(app.state, 'start_time')
                assert hasattr(app.state, 'version')
                assert app.state.version == "2.0.0"
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch('src.main.logger')
    @patch('src.main.get_settings')
    async def test_lifespan_shutdown(self, mock_settings, mock_logger):
        """Test lifespan context manager shutdown."""
        from unittest.mock import MagicMock, patch
        
        # Mock all service imports to avoid heavy initialization
        with patch('src.services.opensearch.client.make_opensearch_client'), \
             patch('src.services.embeddings.service.make_embedding_service'), \
             patch('src.services.cache.redis_cache.make_redis_cache'), \
             patch('src.services.ollama.client.make_ollama_client'), \
             patch('src.services.langfuse.tracer.make_langfuse_tracer'), \
             patch('src.services.agents.agentic_rag.AgenticRAGService'), \
             patch('src.workflow.create_guild'), \
             patch('src.services.extraction.service.make_extraction_service'):
            
            app = MagicMock()
            state = MagicMock()
            app.state = state
            
            async with lifespan(app):
                pass
            
            # Check shutdown was logged
            mock_logger.info.assert_any_call("Shutting down MediGuard AI …")

    def test_app_includes_routers(self):
        """Test that app includes all routers."""
        app = create_app()
        
        # Check that routes are registered
        routes = [route.path for route in app.routes]
        expected_routes = ["/analyze", "/ask", "/search", "/health"]
        
        for route in expected_routes:
            assert any(route in r for r in routes)

    def test_app_cors_middleware(self):
        """Test CORS middleware is configured."""
        app = create_app()
        
        # Find CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None

    def test_global_exception_handler(self):
        """Test global exception handler."""
        app = create_app()
        client = TestClient(app)
        
        # Trigger a validation error
        response = client.post("/analyze/structured", json={"invalid": "data"})
        
        assert response.status_code == 422
        assert "details" in response.json()

    def test_health_endpoint(self):
        """Test health endpoint."""
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"
