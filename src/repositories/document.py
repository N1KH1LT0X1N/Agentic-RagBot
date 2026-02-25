"""
MediGuard AI — Document repository.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.analysis import MedicalDocument


class DocumentRepository:
    """CRUD for ingested medical documents."""

    def __init__(self, db: Session):
        self.db = db

    def upsert(self, doc: MedicalDocument) -> MedicalDocument:
        existing = (
            self.db.query(MedicalDocument)
            .filter(MedicalDocument.content_hash == doc.content_hash)
            .first()
        )
        if existing:
            existing.parse_status = doc.parse_status
            existing.chunk_count = doc.chunk_count
            existing.indexed_at = doc.indexed_at
            self.db.flush()
            return existing
        self.db.add(doc)
        self.db.flush()
        return doc

    def get_by_id(self, doc_id: str) -> MedicalDocument | None:
        return self.db.query(MedicalDocument).filter(MedicalDocument.id == doc_id).first()

    def list_all(self, limit: int = 100) -> list[MedicalDocument]:
        return (
            self.db.query(MedicalDocument)
            .order_by(MedicalDocument.created_at.desc())
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(MedicalDocument).count()
