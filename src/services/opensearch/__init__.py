"""MediGuard AI — OpenSearch service package."""
from src.services.opensearch.client import OpenSearchClient, make_opensearch_client
from src.services.opensearch.index_config import MEDICAL_CHUNKS_MAPPING

__all__ = ["MEDICAL_CHUNKS_MAPPING", "OpenSearchClient", "make_opensearch_client"]
