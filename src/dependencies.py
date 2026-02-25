"""
MediGuard AI — FastAPI Dependency Injection

Provides factory functions and ``Depends()`` for services used across routers.
"""

from __future__ import annotations

from src.services.cache.redis_cache import RedisCache, make_redis_cache
from src.services.embeddings.service import EmbeddingService, make_embedding_service
from src.services.langfuse.tracer import LangfuseTracer, make_langfuse_tracer
from src.services.ollama.client import OllamaClient, make_ollama_client
from src.services.opensearch.client import OpenSearchClient, make_opensearch_client


def get_opensearch_client() -> OpenSearchClient:
    return make_opensearch_client()


def get_embedding_service() -> EmbeddingService:
    return make_embedding_service()


def get_redis_cache() -> RedisCache:
    return make_redis_cache()


def get_ollama_client() -> OllamaClient:
    return make_ollama_client()


def get_langfuse_tracer() -> LangfuseTracer:
    return make_langfuse_tracer()
