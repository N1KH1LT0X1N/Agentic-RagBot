"""
MediGuard AI — Unified Retrieval Services

Auto-selects FAISS (local-dev/HuggingFace) or OpenSearch (production).
"""

from src.services.retrieval.interface import BaseRetriever, RetrievalResult
from src.services.retrieval.faiss_retriever import FAISSRetriever
from src.services.retrieval.opensearch_retriever import OpenSearchRetriever
from src.services.retrieval.factory import make_retriever, get_retriever

__all__ = [
    "BaseRetriever",
    "RetrievalResult",
    "FAISSRetriever",
    "OpenSearchRetriever",
    "make_retriever",
    "get_retriever",
]
