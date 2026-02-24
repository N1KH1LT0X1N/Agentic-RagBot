"""
MediGuard AI — FAISS Retriever

Local vector store retriever for development and HuggingFace Spaces.
Uses FAISS for fast similarity search on medical document embeddings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.retrieval.interface import BaseRetriever, RetrievalResult

logger = logging.getLogger(__name__)

# Guard import — faiss might not be installed in test environments
try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    FAISS = None  # type: ignore[assignment,misc]


class FAISSRetriever(BaseRetriever):
    """
    FAISS-based retriever for local development and HuggingFace deployment.
    
    Supports:
    - Semantic similarity search (default)
    - Maximal Marginal Relevance (MMR) for diversity
    - Score threshold filtering
    
    Does NOT support:
    - BM25 keyword search (vector-only)
    - Metadata filtering (FAISS limitation)
    """
    
    def __init__(
        self,
        vector_store: "FAISS",
        *,
        search_type: str = "similarity",  # "similarity" or "mmr"
        score_threshold: Optional[float] = None,
    ):
        """
        Initialize FAISS retriever.
        
        Args:
            vector_store: Loaded FAISS vector store instance
            search_type: "similarity" for cosine, "mmr" for diversity
            score_threshold: Minimum score (0-1) to include results
        """
        if FAISS is None:
            raise ImportError("langchain-community with FAISS is not installed")
        
        self._store = vector_store
        self._search_type = search_type
        self._score_threshold = score_threshold
        self._doc_count_cache: Optional[int] = None
    
    @classmethod
    def from_local(
        cls,
        vector_store_path: str,
        embedding_model,
        *,
        index_name: str = "medical_knowledge",
        **kwargs,
    ) -> "FAISSRetriever":
        """
        Load FAISS retriever from a local directory.
        
        Args:
            vector_store_path: Directory containing .faiss and .pkl files
            embedding_model: Embedding model (must match creation model)
            index_name: Name of the index (default: medical_knowledge)
            **kwargs: Additional args passed to FAISSRetriever.__init__
        
        Returns:
            Initialized FAISSRetriever
        
        Raises:
            FileNotFoundError: If the index doesn't exist
        """
        if FAISS is None:
            raise ImportError("langchain-community with FAISS is not installed")
        
        store_path = Path(vector_store_path)
        index_path = store_path / f"{index_name}.faiss"
        
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        
        logger.info("Loading FAISS index from %s", store_path)
        
        # SECURITY NOTE: allow_dangerous_deserialization=True uses pickle.
        # Only load from trusted, locally-built sources.
        store = FAISS.load_local(
            str(store_path),
            embedding_model,
            index_name=index_name,
            allow_dangerous_deserialization=True,
        )
        
        return cls(store, **kwargs)
    
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve documents using FAISS similarity search.
        
        Args:
            query: Natural language query
            top_k: Maximum number of results
            filters: Ignored (FAISS doesn't support metadata filtering)
        
        Returns:
            List of RetrievalResult objects
        """
        if filters:
            logger.warning("FAISS does not support metadata filters; ignoring filters=%s", filters)
        
        try:
            if self._search_type == "mmr":
                # MMR provides diversity in results
                docs_with_scores = self._store.max_marginal_relevance_search_with_score(
                    query, k=top_k, fetch_k=top_k * 2
                )
            else:
                # Standard similarity search
                docs_with_scores = self._store.similarity_search_with_score(query, k=top_k)
            
            results = []
            for doc, score in docs_with_scores:
                # FAISS returns L2 distance (lower = better), convert to similarity
                # Assumes normalized embeddings where L2 distance is in [0, 2]
                # Similarity = 1 - (distance / 2), clamped to [0, 1]
                similarity = max(0.0, min(1.0, 1 - score / 2))
                
                # Apply score threshold
                if self._score_threshold and similarity < self._score_threshold:
                    continue
                
                results.append(RetrievalResult(
                    doc_id=str(doc.metadata.get("chunk_id", hash(doc.page_content))),
                    content=doc.page_content,
                    score=similarity,
                    metadata=doc.metadata,
                ))
            
            logger.debug("FAISS retrieved %d results for query: %s...", len(results), query[:50])
            return results
        
        except Exception as exc:
            logger.error("FAISS retrieval failed: %s", exc)
            return []
    
    def health(self) -> bool:
        """Check if FAISS store is loaded."""
        return self._store is not None
    
    def doc_count(self) -> int:
        """Return number of indexed chunks."""
        if self._doc_count_cache is None:
            try:
                self._doc_count_cache = self._store.index.ntotal
            except Exception:
                self._doc_count_cache = 0
        return self._doc_count_cache
    
    @property
    def backend_name(self) -> str:
        return "FAISS (local)"


# Factory function for quick setup
def make_faiss_retriever(
    vector_store_path: str = "data/vector_stores",
    embedding_model=None,
    index_name: str = "medical_knowledge",
) -> FAISSRetriever:
    """
    Create a FAISS retriever with sensible defaults.
    
    Args:
        vector_store_path: Path to vector store directory
        embedding_model: Embedding model (auto-loaded if None)
        index_name: Index name
    
    Returns:
        Configured FAISSRetriever
    """
    if embedding_model is None:
        from src.llm_config import get_embedding_model
        embedding_model = get_embedding_model()
    
    return FAISSRetriever.from_local(
        vector_store_path,
        embedding_model,
        index_name=index_name,
    )
