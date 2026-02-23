"""
MediGuard AI — Analysis repository (data-access layer).
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.analysis import PatientAnalysis


class AnalysisRepository:
    """CRUD operations for patient analyses."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, analysis: PatientAnalysis) -> PatientAnalysis:
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def get_by_request_id(self, request_id: str) -> Optional[PatientAnalysis]:
        return (
            self.db.query(PatientAnalysis)
            .filter(PatientAnalysis.request_id == request_id)
            .first()
        )

    def list_recent(self, limit: int = 20) -> List[PatientAnalysis]:
        return (
            self.db.query(PatientAnalysis)
            .order_by(PatientAnalysis.created_at.desc())
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(PatientAnalysis).count()
