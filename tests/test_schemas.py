"""
Tests for src/schemas/schemas.py — Pydantic request/response models.
"""

import pytest
from pydantic import ValidationError

from src.schemas.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    NaturalAnalysisRequest,
    SearchRequest,
    SearchResponse,
    StructuredAnalysisRequest,
)


class TestNaturalAnalysisRequest:
    def test_valid(self):
        req = NaturalAnalysisRequest(message="My glucose is 185 and HbA1c 8.2")
        assert req.message == "My glucose is 185 and HbA1c 8.2"

    def test_too_short(self):
        with pytest.raises(ValidationError):
            NaturalAnalysisRequest(message="hi")


class TestStructuredAnalysisRequest:
    def test_valid(self):
        req = StructuredAnalysisRequest(biomarkers={"Glucose": 185.0})
        assert req.biomarkers["Glucose"] == 185.0

    def test_empty_biomarkers(self):
        with pytest.raises(ValidationError):
            StructuredAnalysisRequest(biomarkers={})


class TestAskRequest:
    def test_valid(self):
        req = AskRequest(question="What does high HbA1c mean?")
        assert "HbA1c" in req.question

    def test_too_short(self):
        with pytest.raises(ValidationError):
            AskRequest(question="ab")

    def test_with_biomarkers(self):
        req = AskRequest(
            question="Explain my results",
            biomarkers={"Glucose": 200.0},
            patient_context="52-year-old male",
        )
        assert req.biomarkers is not None


class TestSearchRequest:
    def test_defaults(self):
        req = SearchRequest(query="diabetes guidelines")
        assert req.top_k == 10
        assert req.mode == "hybrid"


class TestAskResponse:
    def test_round_trip(self):
        resp = AskResponse(
            request_id="req_abc",
            question="test?",
            answer="test answer",
            documents_retrieved=5,
            documents_relevant=3,
            processing_time_ms=123.4,
        )
        data = resp.model_dump()
        assert data["status"] == "success"
        assert data["documents_relevant"] == 3


class TestHealthResponse:
    def test_basic(self):
        resp = HealthResponse(
            status="healthy",
            timestamp="2025-01-01T00:00:00Z",
            version="2.0.0",
            uptime_seconds=42.0,
        )
        assert resp.status == "healthy"
