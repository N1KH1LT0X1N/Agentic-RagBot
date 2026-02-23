"""
Tests for src/models/analysis.py — SQLAlchemy ORM models.
"""

from src.models.analysis import MedicalDocument, PatientAnalysis, SOPVersion


def test_patient_analysis_tablename():
    assert PatientAnalysis.__tablename__ == "patient_analyses"


def test_medical_document_tablename():
    assert MedicalDocument.__tablename__ == "medical_documents"


def test_sop_version_tablename():
    assert SOPVersion.__tablename__ == "sop_versions"


def test_patient_analysis_has_columns():
    cols = {c.name for c in PatientAnalysis.__table__.columns}
    expected = {"id", "request_id", "biomarkers", "predicted_disease", "created_at"}
    assert expected.issubset(cols)


def test_medical_document_has_columns():
    cols = {c.name for c in MedicalDocument.__table__.columns}
    expected = {"id", "title", "content_hash", "parse_status", "created_at"}
    assert expected.issubset(cols)
