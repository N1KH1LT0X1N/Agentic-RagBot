"""
MediGuard AI — Search Router

Direct hybrid search endpoint (no LLM generation).
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request

from src.schemas.schemas import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def hybrid_search(body: SearchRequest, request: Request):
    """Execute a direct hybrid search against the OpenSearch index."""
    os_client = getattr(request.app.state, "opensearch_client", None)
    embedding_service = getattr(request.app.state, "embedding_service", None)

    if os_client is None:
        raise HTTPException(status_code=503, detail="Search service unavailable")

    t0 = time.time()

    try:
        if body.mode == "bm25":
            results = os_client.search_bm25(query_text=body.query, top_k=body.top_k)
        elif body.mode == "vector":
            if embedding_service is None:
                raise HTTPException(status_code=503, detail="Embedding service unavailable for vector search")
            vec = embedding_service.embed_query(body.query)
            results = os_client.search_vector(query_vector=vec, top_k=body.top_k)
        else:
            # hybrid
            if embedding_service is None:
                logger.warning("Embedding service unavailable — falling back to BM25")
                results = os_client.search_bm25(query_text=body.query, top_k=body.top_k)
            else:
                vec = embedding_service.embed_query(body.query)
                results = os_client.search_hybrid(query_text=body.query, query_vector=vec, top_k=body.top_k)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Search failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Search error: {exc}")

    elapsed = (time.time() - t0) * 1000

    formatted = [
        {
            "id": hit.get("_id", ""),
            "score": hit.get("_score", 0.0),
            "title": hit.get("_source", {}).get("title", ""),
            "section": hit.get("_source", {}).get("section_title", ""),
            "text": hit.get("_source", {}).get("chunk_text", "")[:500],
        }
        for hit in results
    ]

    return SearchResponse(
        query=body.query,
        mode=body.mode,
        total_hits=len(formatted),
        results=formatted,
        processing_time_ms=round(elapsed, 1),
    )
