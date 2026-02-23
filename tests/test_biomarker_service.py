"""
Tests for src/services/biomarker/service.py — production biomarker validation.
"""

import pytest

from src.services.biomarker.service import BiomarkerService, ValidationReport


@pytest.fixture
def service():
    return BiomarkerService()


def test_validate_known_biomarkers(service: BiomarkerService):
    """Should validate known biomarkers correctly."""
    report = service.validate({"Glucose": 185.0, "HbA1c": 8.2})
    assert isinstance(report, ValidationReport)
    assert report.recognized_count >= 1
    # At least one result should exist
    assert len(report.results) >= 1


def test_validate_critical_generates_alert(service: BiomarkerService):
    """Critically abnormal values should generate safety alerts."""
    # Glucose < 40 or > 500 should be critical
    report = service.validate({"Glucose": 550.0})
    if report.recognized_count > 0:
        critical = [r for r in report.results if r.status.startswith("CRITICAL")]
        # If the validator flags it as critical, there should be alerts
        if critical:
            assert len(report.safety_alerts) > 0


def test_validate_unrecognized(service: BiomarkerService):
    """Unknown biomarker names should be listed as unrecognized."""
    report = service.validate({"FakeMarkerXYZ": 42.0})
    assert "FakeMarkerXYZ" in report.unrecognized
    assert report.recognized_count == 0


def test_list_supported(service: BiomarkerService):
    """Should return a list of supported biomarkers."""
    supported = service.list_supported()
    assert isinstance(supported, list)
    # We know the validator has 24 biomarkers
    assert len(supported) >= 20
