"""
MediGuard AI — OpenSearch Retriever

Production retriever with BM25 keyword search, vector KNN, and hybrid RRF fusion.
Requires OpenSearch 2.x cluster with KNN plugin.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.services.retrieval.interface import BaseRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class OpenSearchRetriever(BaseRetriever):
    """
    OpenSearch-based retriever for production deployment.
    
    Supports:
    - BM25 keyword search (traditional full-text)
    - KNN vector search (semantic similarity)
    - Hybrid search with Reciprocal Rank Fusion (RRF)
    - Metadata filtering
    
    Requires:
    - OpenSearch 2.x with k-NN plugin
    - Index with both text fields and vector embeddings
    """
    
    def __init__(
        self,
        client: "OpenSearchClient",  # noqa: F821
        embedding_service=None,
        *,
        default_search_mode: str = "hybrid",  # "bm25", "vector", "hybrid"
    ):
        """
        Initialize OpenSearch retriever.
        
        Args:
            client: OpenSearchClient instance
            embedding_service: Optional embedding service for vector queries
            default_search_mode: Default search mode ("bm25", "vector", "hybrid")
        """
        self._client = client
        self._embedding_service = embedding_service
        self._default_search_mode = default_search_mode
    
    def _to_result(self, hit: Dict[str, Any]) -> RetrievalResult:
        """Convert OpenSearch hit to RetrievalResult."""
        # Extract text content from different field names
        content = (
            hit.get("chunk_text")
            or hit.get("content")
            or hit.get("text")
            or ""
        )
        
        # Normalize score to [0, 1] range
        raw_score = hit.get("_score", 0.0)
        # BM25 scores can be > 1, normalize roughly
        normalized_score = min(1.0, raw_score / 10.0) if raw_score > 1.0 else raw_score
        
        return RetrievalResult(
            doc_id=hit.get("_id", ""),
            content=content,
            score=normalized_score,
            metadata={
                k: v for k, v in hit.items()
                if k not in ("_id", "_score", "chunk_text", "content", "text", "embedding")
            },
        )
    
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve documents using the default search mode.
        
        Args:
            query: Natural language query
            top_k: Maximum number of results
            filters: Optional metadata filters
        
        Returns:
            List of RetrievalResult objects
        """
        if self._default_search_mode == "bm25":
            return self.retrieve_bm25(query, top_k=top_k, filters=filters)
        elif self._default_search_mode == "vector":
            return self._retrieve_vector(query, top_k=top_k, filters=filters)
        else:  # hybrid
            return self.retrieve_hybrid(query, top_k=top_k, filters=filters)
    
    def retrieve_bm25(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        BM25 keyword search.
        
        Args:
            query: Natural language query
            top_k: Maximum number of results
            filters: Optional metadata filters
        
        Returns:
            List of RetrievalResult objects
        """
        try:
            hits = self._client.search_bm25(query, top_k=top_k, filters=filters)
            results = [self._to_result(h) for h in hits]
            logger.debug("OpenSearch BM25 retrieved %d results for: %s...", len(results), query[:50])
            return results
        except Exception as exc:
            logger.error("OpenSearch BM25 search failed: %s", exc)
            return []
    
    def _retrieve_vector(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Vector KNN search.
        
        Args:
            query: Natural language query
            top_k: Maximum number of results
            filters: Optional metadata filters
        
        Returns:
            List of RetrievalResult objects
        """
        if self._embedding_service is None:
            logger.warning("No embedding service for vector search, falling back to BM25")
            return self.retrieve_bm25(query, top_k=top_k, filters=filters)
        
        try:
            # Generate embedding for query
            embedding = self._embedding_service.embed_query(query)
            
            hits = self._client.search_vector(embedding, top_k=top_k, filters=filters)
            results = [self._to_result(h) for h in hits]
            logger.debug("OpenSearch vector retrieved %d results for: %s...", len(results), query[:50])
            return results
        except Exception as exc:
            logger.error("OpenSearch vector search failed: %s", exc)
            return []
    
    def retrieve_hybrid(
        self,
        query: str,
        embedding: Optional[List[float]] = None,
        *,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6,
    ) -> List[RetrievalResult]:
        """
        Hybrid search combining BM25 and vector search with RRF fusion.
        
        Args:
            query: Natural language query
            embedding: Pre-computed embedding (optional)
            top_k: Maximum number of results
            filters: Optional metadata filters
            bm25_weight: Weight for BM25 component (unused, RRF is rank-based)
            vector_weight: Weight for vector component (unused, RRF is rank-based)
        
        Returns:
            List of RetrievalResult objects
        """
        if embedding is None:
            if self._embedding_service is None:
                logger.warning("No embedding service for hybrid search, falling back to BM25")
                return self.retrieve_bm25(query, top_k=top_k, filters=filters)
            embedding = self._embedding_service.embed_query(query)
        
        try:
            hits = self._client.search_hybrid(
                query,
                embedding,
                top_k=top_k,
                filters=filters,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight,
            )
            results = [self._to_result(h) for h in hits]
            logger.debug("OpenSearch hybrid retrieved %d results for: %s...", len(results), query[:50])
            return results
        except Exception as exc:
            logger.error("OpenSearch hybrid search failed: %s", exc)
            return []
    
    def health(self) -> bool:
        """Check if OpenSearch cluster is healthy."""
        return self._client.ping()
    
    def doc_count(self) -> int:
        """Return number of indexed documents."""
        return self._client.doc_count()
    
    @property
    def backend_name(self) -> str:
        return f"OpenSearch ({self._client.index_name})"


# Factory function for quick setup
def make_opensearch_retriever(
    client=None,
    embedding_service=None,
    default_search_mode: str = "hybrid",
) -> OpenSearchRetriever:
    """
    Create an OpenSearch retriever with sensible defaults.
    
    Args:
        client: OpenSearchClient (auto-created if None)
        embedding_service: Embedding service (optional)
        default_search_mode: Default search mode
    
    Returns:
        Configured OpenSearchRetriever
    """
    if client is None:
        from src.services.opensearch.client import make_opensearch_client
        client = make_opensearch_client()
    
    return OpenSearchRetriever(
        client,
        embedding_service=embedding_service,
        default_search_mode=default_search_mode,
    )
