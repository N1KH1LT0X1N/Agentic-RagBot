"""
MediGuard AI — Unified Retrieval Services

Auto-selects FAISS (local-dev/HuggingFace) or OpenSearch (production).
"""

from src.services.retrieval.factory import get_retriever, make_retriever
from src.services.retrieval.faiss_retriever import FAISSRetriever
from src.services.retrieval.interface import BaseRetriever, RetrievalResult
from src.services.retrieval.opensearch_retriever import OpenSearchRetriever

__all__ = [
    "BaseRetriever",
    "FAISSRetriever",
    "OpenSearchRetriever",
    "RetrievalResult",
    "get_retriever",
    "make_retriever",
]
