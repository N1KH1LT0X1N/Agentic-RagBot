"""
MediGuard AI — Retrieve Node

Performs hybrid search (BM25 + vector KNN) and merges results.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def retrieve_node(state: dict, *, context: Any) -> dict:
    """Retrieve documents from OpenSearch via hybrid search."""
    query = state.get("rewritten_query") or state.get("query", "")

    # 1. Try cache first
    cache_key = f"retrieve:{query}"
    if context.cache:
        cached = context.cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for retrieve query")
            return {"retrieved_documents": cached}

    # 2. Embed the query
    try:
        query_embedding = context.embedding_service.embed_query(query)
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        return {"retrieved_documents": [], "errors": [str(exc)]}

    # 3. Hybrid search
    try:
        results = context.opensearch_client.search_hybrid(
            query_text=query,
            query_vector=query_embedding,
            top_k=10,
        )
    except Exception as exc:
        logger.error("OpenSearch hybrid search failed: %s — falling back to BM25", exc)
        try:
            results = context.opensearch_client.search_bm25(
                query_text=query,
                top_k=10,
            )
        except Exception as exc2:
            logger.error("BM25 fallback also failed: %s", exc2)
            return {"retrieved_documents": [], "errors": [str(exc), str(exc2)]}

    documents = [
        {
            "id": hit.get("_id", ""),
            "score": hit.get("_score", 0.0),
            "text": hit.get("_source", {}).get("chunk_text", ""),
            "title": hit.get("_source", {}).get("title", ""),
            "section": hit.get("_source", {}).get("section_title", ""),
            "metadata": hit.get("_source", {}),
        }
        for hit in results
    ]

    # 4. Store in cache (5 min TTL)
    if context.cache:
        context.cache.set(cache_key, documents, ttl=300)

    return {"retrieved_documents": documents}
