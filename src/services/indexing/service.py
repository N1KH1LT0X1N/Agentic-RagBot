"""
MediGuard AI — Indexing Service

Orchestrates: PDF parse → chunk → embed → index into OpenSearch.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from src.services.indexing.text_chunker import MedicalChunk, MedicalTextChunker

logger = logging.getLogger(__name__)


class IndexingService:
    """Coordinates chunking → embedding → OpenSearch indexing."""

    def __init__(self, chunker, embedding_service, opensearch_client):
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.opensearch_client = opensearch_client

    def index_text(
        self,
        text: str,
        *,
        document_id: str = "",
        title: str = "",
        source_file: str = "",
    ) -> int:
        """Chunk, embed, and index a single document's text. Returns count of indexed chunks."""
        if not document_id:
            document_id = str(uuid.uuid4())

        chunks = self.chunker.chunk_text(
            text,
            document_id=document_id,
            title=title,
            source_file=source_file,
        )
        if not chunks:
            logger.warning("No chunks generated for document '%s'", title)
            return 0

        # Embed all chunks
        texts = [c.text for c in chunks]
        embeddings = self.embedding_service.embed_documents(texts)

        # Prepare OpenSearch documents
        now = datetime.now(timezone.utc).isoformat()
        docs: List[Dict] = []
        for chunk, emb in zip(chunks, embeddings):
            doc = chunk.to_dict()
            doc["_id"] = f"{document_id}_{chunk.chunk_index}"
            doc["embedding"] = emb
            doc["indexed_at"] = now
            docs.append(doc)

        indexed = self.opensearch_client.bulk_index(docs)
        logger.info(
            "Indexed %d chunks for '%s' (document_id=%s)",
            indexed, title, document_id,
        )
        return indexed

    def index_chunks(self, chunks: List[MedicalChunk]) -> int:
        """Embed and index pre-built chunks."""
        if not chunks:
            return 0
        texts = [c.text for c in chunks]
        embeddings = self.embedding_service.embed_documents(texts)
        now = datetime.now(timezone.utc).isoformat()
        docs: List[Dict] = []
        for chunk, emb in zip(chunks, embeddings):
            doc = chunk.to_dict()
            doc["_id"] = f"{chunk.document_id}_{chunk.chunk_index}"
            doc["embedding"] = emb
            doc["indexed_at"] = now
            docs.append(doc)
        return self.opensearch_client.bulk_index(docs)
