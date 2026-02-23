"""
MediGuard AI — Embedding Service

Supports Jina AI, Google, HuggingFace, and Ollama embeddings with
automatic fallback chain: Jina → Google → HuggingFace.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from src.exceptions import EmbeddingError, EmbeddingProviderError
from src.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Unified embedding interface — delegates to the configured provider."""

    def __init__(self, model, provider_name: str, dimension: int):
        self._model = model
        self.provider_name = provider_name
        self.dimension = dimension

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        try:
            return self._model.embed_query(text)
        except Exception as exc:
            raise EmbeddingProviderError(f"{self.provider_name} embed_query failed: {exc}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch-embed a list of texts."""
        try:
            return self._model.embed_documents(texts)
        except Exception as exc:
            raise EmbeddingProviderError(f"{self.provider_name} embed_documents failed: {exc}")


def _make_google_embeddings():
    settings = get_settings()
    api_key = settings.embedding.google_api_key or settings.llm.google_api_key
    if not api_key:
        raise EmbeddingError("GOOGLE_API_KEY not set for Google embeddings")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key,
    )
    return EmbeddingService(model, "google", 768)


def _make_huggingface_embeddings():
    settings = get_settings()
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings

    model = HuggingFaceEmbeddings(model_name=settings.embedding.huggingface_model)
    return EmbeddingService(model, "huggingface", 384)


def _make_ollama_embeddings():
    settings = get_settings()
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError:
        from langchain_community.embeddings import OllamaEmbeddings

    model = OllamaEmbeddings(
        model=settings.ollama.embedding_model,
        base_url=settings.ollama.host,
    )
    return EmbeddingService(model, "ollama", 768)


def _make_jina_embeddings():
    settings = get_settings()
    api_key = settings.embedding.jina_api_key
    if not api_key:
        raise EmbeddingError("JINA_API_KEY not set for Jina embeddings")
    # Jina v3 via httpx (lightweight, no extra SDK)
    import httpx

    class _JinaModel:
        """Minimal Jina AI embedding adapter."""

        def __init__(self, api_key: str, model: str):
            self._api_key = api_key
            self._model = model
            self._url = "https://api.jina.ai/v1/embeddings"

        def _call(self, texts: list[str], task: str = "retrieval.passage") -> list[list[float]]:
            headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
            payload = {"model": self._model, "input": texts, "task": task}
            resp = httpx.post(self._url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]

        def embed_query(self, text: str) -> list[float]:
            return self._call([text], task="retrieval.query")[0]

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self._call(texts, task="retrieval.passage")

    model = _JinaModel(api_key, settings.embedding.jina_model)
    return EmbeddingService(model, "jina", settings.embedding.dimension)


# ── Fallback chain factory ───────────────────────────────────────────────────

_PROVIDERS = {
    "jina": _make_jina_embeddings,
    "google": _make_google_embeddings,
    "huggingface": _make_huggingface_embeddings,
    "ollama": _make_ollama_embeddings,
}

FALLBACK_ORDER = ["jina", "google", "huggingface"]


@lru_cache(maxsize=1)
def make_embedding_service() -> EmbeddingService:
    """Create an embedding service with automatic fallback."""
    settings = get_settings()
    preferred = settings.embedding.provider

    # Try preferred first, then fallbacks
    order = [preferred] + [p for p in FALLBACK_ORDER if p != preferred]
    for provider in order:
        factory = _PROVIDERS.get(provider)
        if factory is None:
            continue
        try:
            svc = factory()
            logger.info("Embedding provider: %s (dim=%d)", svc.provider_name, svc.dimension)
            return svc
        except Exception as exc:
            logger.warning("Embedding provider '%s' failed: %s — trying next", provider, exc)

    raise EmbeddingError("All embedding providers failed. Check your API keys and configuration.")
