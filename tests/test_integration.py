"""
MediGuard AI — Integration Tests

End-to-end tests verifying the complete analysis workflow.
These tests ensure all components work together correctly.

Run with: pytest tests/test_integration.py -v
"""

import os
from typing import Any

import pytest

# Set deterministic mode for evaluation tests
os.environ["EVALUATION_DETERMINISTIC"] = "true"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_biomarkers() -> dict[str, float]:
    """Standard diabetic biomarker panel."""
    return {
        "Glucose": 145,
        "HbA1c": 7.2,
        "Cholesterol": 220,
        "LDL": 140,
        "HDL": 45,
        "Triglycerides": 180,
    }


@pytest.fixture
def normal_biomarkers() -> dict[str, float]:
    """Normal healthy biomarkers."""
    return {
        "Glucose": 90,
        "HbA1c": 5.2,
        "Cholesterol": 180,
        "LDL": 90,
        "HDL": 55,
        "Triglycerides": 120,
    }


# ---------------------------------------------------------------------------
# Shared Utilities Tests
# ---------------------------------------------------------------------------

class TestBiomarkerParsing:
    """Tests for biomarker parsing from natural language."""

    def test_parse_json_input(self):
        """Should parse valid JSON biomarker input."""
        from src.shared_utils import parse_biomarkers

        result = parse_biomarkers('{"Glucose": 140, "HbA1c": 7.5}')

        assert result["Glucose"] == 140
        assert result["HbA1c"] == 7.5

    def test_parse_key_value_format(self):
        """Should parse key:value format."""
        from src.shared_utils import parse_biomarkers

        result = parse_biomarkers("Glucose: 140, HbA1c: 7.5")

        assert result["Glucose"] == 140
        assert result["HbA1c"] == 7.5

    def test_parse_natural_language(self):
        """Should parse natural language with units."""
        from src.shared_utils import parse_biomarkers

        result = parse_biomarkers("glucose 140 mg/dL and hemoglobin 13.5 g/dL")

        assert "Glucose" in result or "glucose" in result
        assert 140 in result.values()

    def test_normalize_biomarker_aliases(self):
        """Should normalize biomarker aliases to canonical names."""
        from src.shared_utils import normalize_biomarker_name

        assert normalize_biomarker_name("a1c") == "HbA1c"
        assert normalize_biomarker_name("fasting glucose") == "Glucose"
        assert normalize_biomarker_name("ldl-c") == "LDL"

    def test_empty_input(self):
        """Should return empty dict for empty input."""
        from src.shared_utils import parse_biomarkers

        assert parse_biomarkers("") == {}
        assert parse_biomarkers("  ") == {}


class TestDiseaseScoring:
    """Tests for rule-based disease scoring heuristics."""

    def test_diabetes_scoring_diabetic(self, sample_biomarkers):
        """Should detect diabetes with elevated glucose/HbA1c."""
        from src.shared_utils import score_disease_diabetes

        score, severity = score_disease_diabetes(sample_biomarkers)

        assert score > 0.5
        assert severity in ["moderate", "high"]

    def test_diabetes_scoring_normal(self, normal_biomarkers):
        """Should not flag diabetes with normal biomarkers."""
        from src.shared_utils import score_disease_diabetes

        score, severity = score_disease_diabetes(normal_biomarkers)

        assert score < 0.3

    def test_dyslipidemia_scoring(self, sample_biomarkers):
        """Should detect dyslipidemia with elevated lipids."""
        from src.shared_utils import score_disease_dyslipidemia

        score, severity = score_disease_dyslipidemia(sample_biomarkers)

        assert score > 0.3

    def test_primary_prediction(self, sample_biomarkers):
        """Should return highest-confidence prediction."""
        from src.shared_utils import get_primary_prediction

        result = get_primary_prediction(sample_biomarkers)

        assert "disease" in result
        assert "confidence" in result
        assert "severity" in result
        assert result["confidence"] > 0


class TestBiomarkerFlagging:
    """Tests for biomarker classification and flagging."""

    def test_classify_abnormal_biomarker(self):
        """Should classify abnormal biomarkers correctly."""
        from src.shared_utils import classify_biomarker

        assert classify_biomarker("Glucose", 200) == "high"
        assert classify_biomarker("Glucose", 50) == "low"
        assert classify_biomarker("Glucose", 90) == "normal"

    def test_flag_biomarkers(self, sample_biomarkers):
        """Should flag abnormal biomarkers with details."""
        from src.shared_utils import flag_biomarkers

        flags = flag_biomarkers(sample_biomarkers)

        assert len(flags) == len(sample_biomarkers)

        # Check that flagged items have expected fields
        for flag in flags:
            assert "name" in flag
            assert "value" in flag
            assert "status" in flag


# ---------------------------------------------------------------------------
# Retrieval Tests
# ---------------------------------------------------------------------------

class TestRetrieverInterface:
    """Tests for the unified retriever interface."""

    def test_retrieval_result_dataclass(self):
        """Should create RetrievalResult with correct fields."""
        from src.services.retrieval.interface import RetrievalResult

        result = RetrievalResult(
            doc_id="test-123",
            content="Test content about diabetes.",
            score=0.85,
            metadata={"source": "test.pdf"}
        )

        assert result.doc_id == "test-123"
        assert result.score == 0.85
        assert "diabetes" in result.content

    @pytest.mark.skipif(
        not os.path.exists("data/vector_stores/medical_knowledge.faiss"),
        reason="FAISS index not available"
    )
    def test_faiss_retriever_loads(self):
        """Should load FAISS retriever from local index."""
        from src.services.retrieval import make_retriever

        retriever = make_retriever(backend="faiss")

        assert retriever.health()
        assert retriever.doc_count() > 0


# ---------------------------------------------------------------------------
# Evaluation Tests
# ---------------------------------------------------------------------------

class TestEvaluationSystem:
    """Tests for the 5D evaluation system."""

    @pytest.fixture
    def sample_response(self) -> dict[str, Any]:
        """Sample analysis response for evaluation."""
        return {
            "patient_summary": {
                "narrative": "Patient shows elevated blood glucose and HbA1c indicating diabetes.",
                "primary_finding": "Type 2 Diabetes",
            },
            "prediction_explanation": {
                "key_drivers": [
                    {"biomarker": "Glucose", "evidence": "Elevated at 145 mg/dL"},
                    {"biomarker": "HbA1c", "evidence": "7.2% indicates poor glycemic control"},
                ],
                "pdf_references": [
                    {"source": "guidelines.pdf", "page": 12},
                    {"source": "diabetes.pdf", "page": 45},
                ],
            },
            "clinical_recommendations": {
                "immediate_actions": ["Confirm HbA1c", "Schedule follow-up"],
                "lifestyle_changes": ["Dietary modifications", "Regular exercise"],
                "monitoring": ["Weekly glucose checks"],
            },
            "biomarker_flags": [
                {"name": "Glucose", "value": 145, "status": "high"},
                {"name": "HbA1c", "value": 7.2, "status": "high"},
            ],
            "key_findings": ["Diabetes indicators present"],
        }

    def test_graded_score_validation(self):
        """Should validate score range 0-1."""
        from src.evaluation.evaluators import GradedScore

        valid = GradedScore(score=0.75, reasoning="Test")
        assert valid.score == 0.75

        with pytest.raises(ValueError):
            GradedScore(score=1.5, reasoning="Invalid")

    def test_evidence_grounding_programmatic(self, sample_response):
        """Should evaluate evidence grounding programmatically."""
        from src.evaluation.evaluators import evaluate_evidence_grounding

        result = evaluate_evidence_grounding(sample_response)

        assert 0 <= result.score <= 1
        assert "Citations" in result.reasoning or "citations" in result.reasoning.lower()

    def test_safety_completeness_programmatic(self, sample_response, sample_biomarkers):
        """Should evaluate safety completeness programmatically."""
        from src.evaluation.evaluators import evaluate_safety_completeness

        # Add required field for safety evaluation
        sample_response["confidence_assessment"] = {
            "limitations": ["Requires clinical confirmation"],
            "confidence_score": 0.75,
        }

        result = evaluate_safety_completeness(sample_response, sample_biomarkers)

        assert 0 <= result.score <= 1

    def test_deterministic_clinical_accuracy(self, sample_response):
        """Should evaluate clinical accuracy deterministically."""
        from src.evaluation.evaluators import evaluate_clinical_accuracy

        # EVALUATION_DETERMINISTIC=true set at top of file
        result = evaluate_clinical_accuracy(sample_response, "Test context")

        assert 0 <= result.score <= 1
        assert "[DETERMINISTIC]" in result.reasoning

    def test_evaluation_result_average(self, sample_response, sample_biomarkers):
        """Should calculate average score across all dimensions."""
        from src.evaluation.evaluators import EvaluationResult, GradedScore

        result = EvaluationResult(
            clinical_accuracy=GradedScore(score=0.8, reasoning="Good"),
            evidence_grounding=GradedScore(score=0.7, reasoning="Good"),
            actionability=GradedScore(score=0.9, reasoning="Good"),
            clarity=GradedScore(score=0.6, reasoning="OK"),
            safety_completeness=GradedScore(score=0.8, reasoning="Good"),
        )

        avg = result.average_score()

        assert 0.7 < avg < 0.8  # (0.8+0.7+0.9+0.6+0.8)/5 = 0.76


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

class TestAPIRoutes:
    """Tests for FastAPI routes (requires running server or test client)."""

    def test_analyze_router_import(self):
        """Should import analyze router without errors."""
        from src.routers import analyze

        assert hasattr(analyze, "router")

    def test_health_check_import(self):
        """Should have health check endpoint."""
        from src.routers import health

        assert hasattr(health, "router")


# ---------------------------------------------------------------------------
# HuggingFace App Tests
# ---------------------------------------------------------------------------

class TestHuggingFaceApp:
    """Tests for HuggingFace Gradio app components."""

    def test_shared_utils_import_in_hf(self):
        """HuggingFace app should import shared utilities."""
        import sys
        from pathlib import Path

        # Add project root to path (as HF app does)
        project_root = str(Path(__file__).parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from src.shared_utils import parse_biomarkers

        # Should work without errors
        result = parse_biomarkers("Glucose: 140")
        assert "Glucose" in result or len(result) > 0


# ---------------------------------------------------------------------------
# Workflow Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY") and not os.environ.get("GOOGLE_API_KEY"),
    reason="No LLM API key available"
)
class TestWorkflow:
    """Tests requiring LLM API access."""

    def test_create_guild(self):
        """Should create ClinicalInsightGuild without errors."""
        from src.workflow import create_guild

        guild = create_guild()

        assert guild is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
