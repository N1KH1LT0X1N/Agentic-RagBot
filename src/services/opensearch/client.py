"""
MediGuard AI — OpenSearch Client

Production search-engine wrapper supporting BM25, vector (KNN), and
hybrid search with Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from src.exceptions import IndexNotFoundError, SearchError, SearchQueryError
from src.settings import get_settings

logger = logging.getLogger(__name__)

# Guard import — opensearch-py is optional when running tests locally
try:
    from opensearchpy import OpenSearch, RequestError, NotFoundError as OSNotFoundError
except ImportError:  # pragma: no cover
    OpenSearch = None  # type: ignore[assignment,misc]


class OpenSearchClient:
    """Thin wrapper around *opensearch-py* with medical-domain helpers."""

    def __init__(self, client: "OpenSearch", index_name: str):
        self._client = client
        self.index_name = index_name

    # ── Health ───────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        return self._client.cluster.health()

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    # ── Index management ─────────────────────────────────────────────────

    def ensure_index(self, mapping: Dict[str, Any]) -> None:
        """Create the index if it doesn't already exist."""
        if not self._client.indices.exists(index=self.index_name):
            self._client.indices.create(index=self.index_name, body=mapping)
            logger.info("Created OpenSearch index '%s'", self.index_name)
        else:
            logger.info("OpenSearch index '%s' already exists", self.index_name)

    def delete_index(self) -> None:
        if self._client.indices.exists(index=self.index_name):
            self._client.indices.delete(index=self.index_name)

    def doc_count(self) -> int:
        try:
            resp = self._client.count(index=self.index_name)
            return resp["count"]
        except Exception:
            return 0

    # ── Indexing ─────────────────────────────────────────────────────────

    def index_document(self, doc_id: str, body: Dict[str, Any]) -> None:
        self._client.index(index=self.index_name, id=doc_id, body=body)

    def bulk_index(self, documents: List[Dict[str, Any]]) -> int:
        """Bulk-index a list of dicts, each must have an ``_id`` key."""
        if not documents:
            return 0
        actions: list[Dict[str, Any]] = []
        for doc in documents:
            doc_id = doc.pop("_id", None)
            actions.append({"index": {"_index": self.index_name, "_id": doc_id}})
            actions.append(doc)
        resp = self._client.bulk(body=actions, refresh="wait_for")
        indexed = sum(1 for item in resp.get("items", []) if item.get("index", {}).get("status") in (200, 201))
        logger.info("Bulk-indexed %d / %d documents", indexed, len(documents))
        return indexed

    # ── BM25 search ──────────────────────────────────────────────────────

    def search_bm25(
        self,
        query_text: str,
        *,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": [
                                    "chunk_text^3",
                                    "title^2",
                                    "section_title^1.5",
                                    "abstract^1",
                                ],
                                "type": "best_fields",
                            }
                        }
                    ]
                }
            },
        }
        if filters:
            body["query"]["bool"]["filter"] = self._build_filters(filters)
        return self._execute_search(body)

    # ── Vector (KNN) search ──────────────────────────────────────────────

    def search_vector(
        self,
        query_vector: List[float],
        *,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": top_k,
                    }
                }
            },
        }
        return self._execute_search(body)

    # ── Hybrid search (RRF) ─────────────────────────────────────────────

    def search_hybrid(
        self,
        query_text: str,
        query_vector: List[float],
        *,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion of BM25 + KNN results."""
        bm25_results = self.search_bm25(query_text, top_k=top_k, filters=filters)
        vector_results = self.search_vector(query_vector, top_k=top_k, filters=filters)
        return self._rrf_fuse(bm25_results, vector_results, top_k=top_k)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _execute_search(self, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            resp = self._client.search(index=self.index_name, body=body)
        except Exception as exc:
            raise SearchQueryError(str(exc))
        hits = resp.get("hits", {}).get("hits", [])
        return [
            {
                "_id": h["_id"],
                "_score": h.get("_score", 0.0),
                "_source": h.get("_source", {}),
            }
            for h in hits
        ]

    @staticmethod
    def _build_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        clauses: List[Dict[str, Any]] = []
        for key, value in filters.items():
            if isinstance(value, list):
                clauses.append({"terms": {key: value}})
            else:
                clauses.append({"term": {key: value}})
        return clauses

    @staticmethod
    def _rrf_fuse(
        results_a: List[Dict[str, Any]],
        results_b: List[Dict[str, Any]],
        *,
        k: int = 60,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Simple Reciprocal Rank Fusion."""
        scores: Dict[str, float] = {}
        docs: Dict[str, Dict[str, Any]] = {}
        for rank, doc in enumerate(results_a, 1):
            doc_id = doc["_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            docs[doc_id] = doc
        for rank, doc in enumerate(results_b, 1):
            doc_id = doc["_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            docs[doc_id] = doc
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {**docs[doc_id], "_score": score}
            for doc_id, score in ranked
        ]


# ── Factory ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def make_opensearch_client() -> OpenSearchClient:
    if OpenSearch is None:
        raise SearchError("opensearch-py is not installed")
    settings = get_settings()
    os_settings = settings.opensearch
    client = OpenSearch(
        hosts=[os_settings.host],
        http_auth=(os_settings.username, os_settings.password) if os_settings.username else None,
        verify_certs=os_settings.verify_certs,
        timeout=os_settings.timeout,
    )
    return OpenSearchClient(client, os_settings.index_name)
