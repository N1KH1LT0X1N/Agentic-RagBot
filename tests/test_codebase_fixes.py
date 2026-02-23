"""
Tests for codebase fixes: confidence cap, validator, thresholds, schema validation
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app.services.extraction import predict_disease_simple as api_predict
from scripts.chat import predict_disease_simple as cli_predict
from src.biomarker_validator import BiomarkerValidator
from api.app.models.schemas import StructuredAnalysisRequest, HealthResponse


# ============================================================================
# Confidence cap tests
# ============================================================================

class TestConfidenceCap:
    """Verify confidence never exceeds 1.0"""

    def test_api_confidence_capped_at_one(self):
        # Glucose>126 (+0.4), Glucose>180 (+0.2), HbA1c>=6.5 (+0.5) = 1.1 raw
        result = api_predict({"Glucose": 200, "HbA1c": 7.0})
        assert result["confidence"] <= 1.0

    def test_cli_confidence_capped_at_one(self):
        result = cli_predict({"Glucose": 200, "HbA1c": 7.0})
        assert result["confidence"] <= 1.0

    def test_confidence_is_exactly_one_for_high_diabetes(self):
        result = api_predict({"Glucose": 200, "HbA1c": 7.0})
        assert result["confidence"] == 1.0

    def test_confidence_not_capped_when_below_one(self):
        result = api_predict({"Glucose": 130})
        assert result["confidence"] == 0.4


# ============================================================================
# Updated critical threshold tests
# ============================================================================

class TestCriticalThresholds:
    """Verify biomarker_references.json has clinically appropriate critical thresholds"""

    def setup_method(self):
        config_path = Path(__file__).parent.parent / "config" / "biomarker_references.json"
        with open(config_path) as f:
            self.refs = json.load(f)["biomarkers"]

    def test_glucose_critical_high_is_emergency(self):
        assert self.refs["Glucose"]["critical_high"] >= 300

    def test_glucose_critical_low_is_emergency(self):
        assert self.refs["Glucose"]["critical_low"] <= 54

    def test_hba1c_critical_high_is_emergency(self):
        assert self.refs["HbA1c"]["critical_high"] >= 10

    def test_troponin_critical_high_above_normal(self):
        normal_max = self.refs["Troponin"]["normal_range"]["max"]
        assert self.refs["Troponin"]["critical_high"] > normal_max

    def test_bmi_critical_high_is_morbid(self):
        assert self.refs["BMI"]["critical_high"] >= 40

    def test_systolic_bp_critical_high_is_crisis(self):
        assert self.refs["Systolic Blood Pressure"]["critical_high"] >= 180

    def test_diastolic_bp_critical_low_is_shock(self):
        assert self.refs["Diastolic Blood Pressure"]["critical_low"] <= 40


# ============================================================================
# Validator threshold removal tests
# ============================================================================

class TestValidatorNoThreshold:
    """Verify validator flags all out-of-range values (no 15% threshold)"""

    def setup_method(self):
        self.validator = BiomarkerValidator()

    def test_slightly_high_glucose_is_flagged(self):
        """Glucose=105 is above normal max=100 — should be HIGH, not NORMAL"""
        flag = self.validator.validate_biomarker("Glucose", 105.0)
        assert flag.status == "HIGH"

    def test_slightly_low_hemoglobin_is_flagged(self):
        """Hemoglobin=13.0 for male (min=13.5) should be LOW"""
        flag = self.validator.validate_biomarker("Hemoglobin", 13.0, gender="male")
        assert flag.status == "LOW"

    def test_normal_glucose_stays_normal(self):
        flag = self.validator.validate_biomarker("Glucose", 90.0)
        assert flag.status == "NORMAL"

    def test_critical_high_glucose_flagged(self):
        flag = self.validator.validate_biomarker("Glucose", 500.0)
        assert flag.status == "CRITICAL_HIGH"

    def test_high_glucose_200_not_critical(self):
        """Glucose=200 is above normal but below critical_high=400"""
        flag = self.validator.validate_biomarker("Glucose", 200.0)
        assert flag.status == "HIGH"


# ============================================================================
# Pydantic schema validation tests
# ============================================================================

class TestSchemaValidation:
    """Verify Pydantic models enforce constraints correctly"""

    def test_structured_request_rejects_empty_biomarkers(self):
        import pytest
        with pytest.raises(Exception):
            StructuredAnalysisRequest(biomarkers={})

    def test_structured_request_accepts_valid_biomarkers(self):
        req = StructuredAnalysisRequest(biomarkers={"Glucose": 100.0})
        assert req.biomarkers == {"Glucose": 100.0}

    def test_health_response_uses_llm_status_field(self):
        resp = HealthResponse(
            status="healthy",
            timestamp="2025-01-01T00:00:00",
            llm_status="connected",
            vector_store_loaded=True,
            available_models=["test"],
            uptime_seconds=100.0,
            version="1.0.0"
        )
        assert resp.llm_status == "connected"
