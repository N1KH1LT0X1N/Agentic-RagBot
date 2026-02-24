"""
MediGuard AI — Agentic RAG Context

Runtime dependency injection dataclass — passed to every LangGraph node
so nodes can access services without globals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class AgenticContext:
    """Immutable runtime context for agentic RAG nodes."""

    llm: Any                         # LangChain chat model
    embedding_service: Any           # EmbeddingService
    opensearch_client: Any           # OpenSearchClient
    cache: Any                       # RedisCache
    tracer: Any                      # LangfuseTracer
    guild: Optional[Any] = None      # ClinicalInsightGuild (original workflow)
    retriever: Optional[Any] = None  # BaseRetriever (FAISS or OpenSearch)
