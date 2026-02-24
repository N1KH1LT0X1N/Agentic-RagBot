"""
MediGuard AI — Retrieve Node

Performs document retrieval using the best available backend:
  1. Generic retriever (FAISS, OpenSearch wrapper, etc.)
  2. OpenSearch hybrid search (BM25 + KNN)
  3. BM25 keyword fallback
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def retrieve_node(state: dict, *, context: Any) -> dict:
    """Retrieve documents using the best available backend.

    Priority:
      1. context.retriever (generic BaseRetriever — works with FAISS & OpenSearch)
      2. context.opensearch_client + context.embedding_service (hybrid search)
      3. BM25 keyword fallback
      4. Empty list
    """
    query = state.get("rewritten_query") or state.get("query", "")
    cache_key = f"retrieve:{query}"

    # 1. Try cache
    if context.cache:
        cached = context.cache.get(cache_key)
        if cached is not None:
            logger.info("Cache HIT for query: %s…", query[:50])
            attempts = state.get("retrieval_attempts", 0) + 1
            return {"retrieved_documents": cached, "retrieval_attempts": attempts}

    documents: list = []

    # 2. Generic retriever (FAISS, OpenSearch wrapper, etc.)
    if getattr(context, "retriever", None) is not None:
        try:
            results = context.retriever.retrieve(query, top_k=8)
            documents = [
                {
                    "content": getattr(r, "content", ""),
                    "metadata": getattr(r, "metadata", {}),
                    "score": getattr(r, "score", 0.0),
                }
                for r in results
            ]
            backend = getattr(context.retriever, "backend_name", "unknown")
            logger.info("Retrieved %d docs via %s", len(documents), backend)
        except Exception as exc:
            logger.warning("Retriever failed (%s), trying OpenSearch fallback…", exc)

    # 3. OpenSearch hybrid fallback
    if not documents and context.opensearch_client and context.embedding_service:
        try:
            embedding = context.embedding_service.embed_query(query)
            raw_hits = context.opensearch_client.search_hybrid(
                query_text=query,
                query_vector=embedding,
                top_k=8,
            )
            documents = [
                {
                    "content": h.get("_source", {}).get("chunk_text", ""),
                    "metadata": {
                        k: v for k, v in h.get("_source", {}).items()
                        if k != "chunk_text"
                    },
                    "score": h.get("_score", 0.0),
                }
                for h in raw_hits
            ]
            logger.info("Retrieved %d docs via OpenSearch hybrid", len(documents))
        except Exception as exc:
            logger.error("OpenSearch retrieval failed: %s", exc)

    # 4. Optional BM25 fallback if still nothing
    if not documents and context.opensearch_client:
        try:
            raw_hits = context.opensearch_client.search_bm25(query_text=query, top_k=8)
            documents = [
                {
                    "content": h.get("_source", {}).get("chunk_text", ""),
                    "metadata": {
                        k: v for k, v in h.get("_source", {}).items()
                        if k != "chunk_text"
                    },
                    "score": h.get("_score", 0.0),
                }
                for h in raw_hits
            ]
            logger.info("Retrieved %d docs via BM25 fallback", len(documents))
        except Exception as exc:
            logger.error("BM25 fallback also failed: %s", exc)

    # 5. Store in cache (5 min TTL)
    if context.cache and documents:
        context.cache.set(cache_key, documents, ttl=300)

    attempts = state.get("retrieval_attempts", 0) + 1
    return {"retrieved_documents": documents, "retrieval_attempts": attempts}
