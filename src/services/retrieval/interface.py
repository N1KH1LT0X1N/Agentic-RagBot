"""
MediGuard AI — Retriever Interface

Abstract base class defining the common interface for all retriever backends:
- FAISS (local dev and HuggingFace Spaces)
- OpenSearch (production with BM25 + KNN hybrid)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Unified result format for retrieval operations."""

    doc_id: str
    """Unique identifier for the document chunk."""

    content: str
    """The actual text content of the chunk."""

    score: float
    """Relevance score (higher is better, normalized 0-1 where possible)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary metadata (source_file, page, section, etc.)."""

    def __repr__(self) -> str:
        preview = self.content[:80].replace("\n", " ") + "..." if len(self.content) > 80 else self.content
        return f"RetrievalResult(score={self.score:.3f}, content='{preview}')"


class BaseRetriever(ABC):
    """
    Abstract base class for retrieval backends.
    
    Implementations must provide:
    - retrieve(): Semantic/hybrid search
    - health(): Health check
    - doc_count(): Number of indexed documents
    
    Optionally:
    - retrieve_bm25(): Keyword-only search
    - retrieve_hybrid(): Combined BM25 + vector search
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Natural language query
            top_k: Maximum number of results
            filters: Optional metadata filters (e.g., {"source_file": "guidelines.pdf"})
        
        Returns:
            List of RetrievalResult objects, ordered by relevance (highest first)
        """
        ...

    @abstractmethod
    def health(self) -> bool:
        """
        Check if the retriever is healthy and ready.
        
        Returns:
            True if operational, False otherwise
        """
        ...

    @abstractmethod
    def doc_count(self) -> int:
        """
        Return the number of indexed document chunks.
        
        Returns:
            Total document count, or 0 if unavailable
        """
        ...

    def retrieve_bm25(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """
        BM25 keyword search (optional, falls back to retrieve()).
        
        Args:
            query: Natural language query
            top_k: Maximum results
            filters: Optional filters
        
        Returns:
            List of RetrievalResult objects
        """
        logger.warning("%s does not support BM25, falling back to retrieve()", type(self).__name__)
        return self.retrieve(query, top_k=top_k, filters=filters)

    def retrieve_hybrid(
        self,
        query: str,
        embedding: list[float] | None = None,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6,
    ) -> list[RetrievalResult]:
        """
        Hybrid search combining BM25 and vector search (optional).
        
        Args:
            query: Natural language query
            embedding: Pre-computed embedding (optional)
            top_k: Maximum results
            filters: Optional filters
            bm25_weight: Weight for BM25 component
            vector_weight: Weight for vector component
        
        Returns:
            List of RetrievalResult objects
        """
        logger.warning("%s does not support hybrid search, falling back to retrieve()", type(self).__name__)
        return self.retrieve(query, top_k=top_k, filters=filters)

    @property
    def backend_name(self) -> str:
        """Human-readable backend name for logging."""
        return type(self).__name__
