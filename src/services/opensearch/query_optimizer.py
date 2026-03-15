"""
Optimized query builder for OpenSearch to improve search performance.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class OptimizedQueryBuilder:
    """Builds optimized OpenSearch queries for better performance."""

    @staticmethod
    def build_bm25_query(
        query_text: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        min_score: float = 0.5,
        boost_recent: bool = True
    ) -> dict[str, Any]:
        """Build optimized BM25 query with performance enhancements."""

        # Use function score for better relevance and performance
        query = {
            "size": top_k,
            "min_score": min_score,
            "query": {
                "function_score": {
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
                                            "abstract^1"
                                        ],
                                        "type": "best_fields",
                                        "fuzziness": "AUTO",
                                        "prefix_length": 2,
                                        "max_expansions": 50
                                    }
                                }
                            ]
                        }
                    },
                    "functions": [],
                    "score_mode": "multiply",
                    "boost_mode": "replace"
                }
            },
            # Optimize for performance
            "_source": ["_id", "chunk_text", "title", "section_title", "abstract", "metadata"],
            "sort": ["_score"],
            "track_total_hits": False  # Disable total hit counting for better performance
        }

        # Add recency boost if enabled
        if boost_recent:
            query["query"]["function_score"]["functions"].append({
                "gauss": {
                    "metadata.publication_date": {
                        "origin": "now",
                        "scale": "365d",
                        "offset": "30d",
                        "decay": 0.5
                    }
                },
                "weight": 1.2
            })

        # Add filters
        if filters:
            query["query"]["function_score"]["query"]["bool"]["filter"] = (
                OptimizedQueryBuilder._build_filters(filters)
            )

        return query

    @staticmethod
    def build_vector_query(
        query_vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        min_score: float = 0.7,
        num_candidates: int = 100  # Larger candidate set for better recall
    ) -> dict[str, Any]:
        """Build optimized vector KNN query."""

        query = {
            "size": top_k,
            "min_score": min_score,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": top_k,
                        "num_candidates": num_candidates
                    }
                }
            },
            "_source": ["_id", "chunk_text", "title", "section_title", "abstract", "metadata"],
            "track_total_hits": False
        }

        # Add filters for KNN (must be in filter context)
        if filters:
            query["query"] = {
                "bool": {
                    "must": [query["query"]],
                    "filter": OptimizedQueryBuilder._build_filters(filters)
                }
            }

        return query

    @staticmethod
    def build_hybrid_query(
        query_text: str,
        query_vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        rrf_window_size: int = 50,
        rrf_rank_constant: int = 60
    ) -> dict[str, Any]:
        """Build optimized hybrid query using RRF (Reciprocal Rank Fusion)."""

        # Build separate queries for BM25 and vector
        bm25_query = OptimizedQueryBuilder.build_bm25_query(
            query_text, top_k=rrf_window_size, filters=filters, min_score=0.1
        )

        vector_query = OptimizedQueryBuilder.build_vector_query(
            query_vector, top_k=rrf_window_size, filters=filters, min_score=0.1
        )

        # Combine using RRF
        query = {
            "size": top_k,
            "query": {
                "rrf": {
                    "queries": [bm25_query["query"], vector_query["query"]],
                    "rank_constant": rrf_rank_constant
                }
            },
            "_source": ["_id", "chunk_text", "title", "section_title", "abstract", "metadata"],
            "track_total_hits": False
        }

        return query

    @staticmethod
    def build_aggregation_query(
        query_text: str,
        agg_field: str,
        *,
        size: int = 10,
        filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build query with aggregations for analytics."""

        query = {
            "size": 0,  # We only want aggregations
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["chunk_text", "title", "abstract"]
                }
            },
            "aggs": {
                "top_values": {
                    "terms": {
                        "field": f"{agg_field}.keyword",
                        "size": size,
                        "min_doc_count": 1
                    }
                }
            }
        }

        if filters:
            query["query"] = {
                "bool": {
                    "must": [query["query"]],
                    "filter": OptimizedQueryBuilder._build_filters(filters)
                }
            }

        return query

    @staticmethod
    def _build_filters(filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Build optimized filter clauses."""
        filter_clauses = []

        for field, value in filters.items():
            if isinstance(value, list):
                # Multiple values - use terms query
                filter_clauses.append({
                    "terms": {f"{field}.keyword": value}
                })
            elif isinstance(value, dict):
                # Range query
                if "gte" in value or "lte" in value or "gt" in value or "lt" in value:
                    range_filter = {"range": {field: {}}}
                    for op, val in value.items():
                        if op in ["gte", "lte", "gt", "lt"]:
                            range_filter["range"][field][op] = val
                    filter_clauses.append(range_filter)
                else:
                    # Nested query
                    filter_clauses.append({
                        "nested": {
                            "path": field,
                            "query": {
                                "bool": {
                                    "must": [
                                        {"term": {f"{field}.{k}.keyword": v}}
                                        for k, v in value.items()
                                    ]
                                }
                            }
                        }
                    })
            else:
                # Single value - use term query
                filter_clauses.append({
                    "term": {f"{field}.keyword": value}
                })

        return filter_clauses

    @staticmethod
    def build_suggestion_query(
        text: str,
        *,
        field: str = "chunk_text",
        size: int = 5
    ) -> dict[str, Any]:
        """Build query for spell-check suggestions."""

        return {
            "suggest": {
                "text": text,
                "simple_phrase": {
                    "phrase": {
                        "field": field,
                        "size": size,
                        "gram_size": 3,
                        "direct_generator": [{
                            "field": field,
                            "suggest_mode": "missing"
                        }],
                        "highlight": {
                            "pre_tag": "<em>",
                            "post_tag": "</em>"
                        }
                    }
                }
            }
        }

    @staticmethod
    def build_more_like_this_query(
        doc_id: str,
        *,
        top_k: int = 10,
        min_term_freq: int = 1,
        max_query_terms: int = 25,
        min_doc_freq: int = 2
    ) -> dict[str, Any]:
        """Build More Like This query."""

        return {
            "size": top_k,
            "query": {
                "more_like_this": {
                    "fields": ["chunk_text", "title", "abstract"],
                    "like": [{"_index": "medical_chunks", "_id": doc_id}],
                    "min_term_freq": min_term_freq,
                    "max_query_terms": max_query_terms,
                    "min_doc_freq": min_doc_freq
                }
            },
            "_source": ["_id", "chunk_text", "title", "section_title", "abstract", "metadata"],
            "track_total_hits": False
        }


class QueryCache:
    """Simple query result cache for frequently executed queries."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache: dict[str, dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, query_hash: str) -> list[dict[str, Any]] | None:
        """Get cached results if not expired."""
        if query_hash in self.cache:
            entry = self.cache[query_hash]
            if datetime.now() - entry["timestamp"] < timedelta(seconds=self.ttl_seconds):
                return entry["results"]
            else:
                del self.cache[query_hash]
        return None

    def set(self, query_hash: str, results: list[dict[str, Any]]) -> None:
        """Cache query results."""
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]

        self.cache[query_hash] = {
            "results": results,
            "timestamp": datetime.now()
        }

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }
