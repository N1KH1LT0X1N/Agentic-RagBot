"""
MediGuard AI — Retriever Factory

Auto-selects the best available retriever backend:
1. OpenSearch (production) if OPENSEARCH_* env vars are set
2. FAISS (local) if vector store exists at data/vector_stores/
3. Raises error if neither is available

Usage:
    from src.services.retrieval import get_retriever
    
    retriever = get_retriever()  # Auto-selects best backend
    results = retriever.retrieve("What are normal glucose levels?")
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from src.services.retrieval.interface import BaseRetriever

logger = logging.getLogger(__name__)

# Detection flags
_OPENSEARCH_AVAILABLE = bool(os.environ.get("OPENSEARCH__HOST") or os.environ.get("OPENSEARCH_HOST"))
_FAISS_PATH = Path(os.environ.get("FAISS_VECTOR_STORE", "data/vector_stores"))


def _detect_backend() -> str:
    """
    Detect the best available retriever backend.
    
    Returns:
        "opensearch" or "faiss"
    
    Raises:
        RuntimeError: If no backend is available
    """
    # Priority 1: OpenSearch (production)
    if _OPENSEARCH_AVAILABLE:
        try:
            from src.services.opensearch.client import make_opensearch_client
            client = make_opensearch_client()
            if client.ping():
                logger.info("Auto-detected backend: OpenSearch (cluster reachable)")
                return "opensearch"
            else:
                logger.warning("OpenSearch configured but not reachable, checking FAISS...")
        except Exception as exc:
            logger.warning("OpenSearch init failed (%s), checking FAISS...", exc)
    
    # Priority 2: FAISS (local/HuggingFace)
    faiss_index = _FAISS_PATH / "medical_knowledge.faiss"
    if faiss_index.exists():
        logger.info("Auto-detected backend: FAISS (index found at %s)", faiss_index)
        return "faiss"
    
    # Check alternative locations
    alt_paths = [
        Path("huggingface/data/vector_stores/medical_knowledge.faiss"),
        Path("vector_stores/medical_knowledge.faiss"),
    ]
    for alt in alt_paths:
        if alt.exists():
            logger.info("Auto-detected backend: FAISS (index found at %s)", alt)
            return "faiss"
    
    # No backend found
    raise RuntimeError(
        "No retriever backend available. Either:\n"
        "  - Set OPENSEARCH__HOST for OpenSearch\n"
        "  - Ensure data/vector_stores/medical_knowledge.faiss exists for FAISS\n"
        "Run: python -m src.pdf_processor to create the FAISS index."
    )


def make_retriever(
    backend: Optional[str] = None,
    *,
    embedding_model=None,
    vector_store_path: Optional[str] = None,
    opensearch_client=None,
    embedding_service=None,
) -> BaseRetriever:
    """
    Create a retriever instance.
    
    Args:
        backend: "faiss", "opensearch", or None for auto-detect
        embedding_model: Embedding model for FAISS
        vector_store_path: Path to FAISS index directory
        opensearch_client: OpenSearch client instance
        embedding_service: Embedding service for OpenSearch vector search
    
    Returns:
        Configured BaseRetriever implementation
    
    Raises:
        RuntimeError: If the requested backend is unavailable
    """
    if backend is None:
        backend = _detect_backend()
    
    backend = backend.lower()
    
    if backend == "faiss":
        from src.services.retrieval.faiss_retriever import FAISSRetriever
        
        if embedding_model is None:
            from src.llm_config import get_embedding_model
            embedding_model = get_embedding_model()
        
        path = vector_store_path or str(_FAISS_PATH)
        
        # Try multiple paths
        paths_to_try = [
            path,
            "huggingface/data/vector_stores",
            "data/vector_stores",
        ]
        
        for p in paths_to_try:
            try:
                return FAISSRetriever.from_local(p, embedding_model)
            except FileNotFoundError:
                continue
        
        raise RuntimeError(f"FAISS index not found in any of: {paths_to_try}")
    
    elif backend == "opensearch":
        from src.services.retrieval.opensearch_retriever import OpenSearchRetriever
        
        if opensearch_client is None:
            from src.services.opensearch.client import make_opensearch_client
            opensearch_client = make_opensearch_client()
        
        return OpenSearchRetriever(
            opensearch_client,
            embedding_service=embedding_service,
        )
    
    else:
        raise ValueError(f"Unknown retriever backend: {backend}")


@lru_cache(maxsize=1)
def get_retriever() -> BaseRetriever:
    """
    Get a cached retriever instance (auto-detected backend).
    
    This is the recommended way to get a retriever in most cases.
    Uses LRU cache to avoid repeated initialization.
    
    Returns:
        Cached BaseRetriever implementation
    """
    return make_retriever()


# Environment hints for deployment
def print_backend_info() -> None:
    """Print information about the detected retriever backend."""
    try:
        backend = _detect_backend()
        retriever = make_retriever(backend)
        print(f"Retriever Backend: {retriever.backend_name}")
        print(f"  Health: {'OK' if retriever.health() else 'DEGRADED'}")
        print(f"  Documents: {retriever.doc_count():,}")
    except Exception as exc:
        print(f"Retriever Backend: NOT AVAILABLE")
        print(f"  Error: {exc}")


if __name__ == "__main__":
    # Quick diagnostic
    logging.basicConfig(level=logging.INFO)
    print_backend_info()
