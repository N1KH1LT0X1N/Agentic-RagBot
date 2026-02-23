"""
MediGuard AI — Biomarker Validation Service

Wraps the existing BiomarkerValidator as a production service with caching,
observability, and Pydantic-typed outputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional

from src.biomarker_validator import BiomarkerValidator
from src.biomarker_normalization import normalize_biomarker_name
from src.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BiomarkerResult:
    """Validated result for a single biomarker."""

    name: str
    value: float
    unit: str
    status: str  # NORMAL | HIGH | LOW | CRITICAL_HIGH | CRITICAL_LOW
    reference_range: str
    warning: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete biomarker validation report."""

    results: List[BiomarkerResult] = field(default_factory=list)
    safety_alerts: List[Dict[str, Any]] = field(default_factory=list)
    recognized_count: int = 0
    unrecognized: List[str] = field(default_factory=list)


class BiomarkerService:
    """Production biomarker validation service."""

    def __init__(self) -> None:
        self._validator = BiomarkerValidator()

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def validate(
        self,
        biomarkers: Dict[str, float],
        gender: Optional[str] = None,
    ) -> ValidationReport:
        """Validate a dict of biomarker name → value and return a report."""
        report = ValidationReport()

        for raw_name, value in biomarkers.items():
            normalized = normalize_biomarker_name(raw_name)
            flag = self._validator.validate_biomarker(normalized, value, gender=gender)
            if flag is None:
                report.unrecognized.append(raw_name)
                continue
            if flag.status == "UNKNOWN":
                report.unrecognized.append(raw_name)
                continue
            report.recognized_count += 1
            report.results.append(
                BiomarkerResult(
                    name=flag.name,
                    value=flag.value,
                    unit=flag.unit,
                    status=flag.status,
                    reference_range=flag.reference_range,
                    warning=flag.warning,
                )
            )
            if flag.status.startswith("CRITICAL"):
                report.safety_alerts.append(
                    {
                        "severity": "CRITICAL",
                        "biomarker": normalized,
                        "message": flag.warning or f"{normalized} is critically out of range",
                        "action": "Seek immediate medical attention",
                    }
                )

        return report

    def list_supported(self) -> List[Dict[str, Any]]:
        """Return metadata for all supported biomarkers."""
        result = []
        for name, ref in self._validator.references.items():
            result.append({
                "name": name,
                "unit": ref.get("unit", ""),
                "normal_range": ref.get("normal_range", {}),
                "critical_low": ref.get("critical_low"),
                "critical_high": ref.get("critical_high"),
            })
        return result


@lru_cache(maxsize=1)
def make_biomarker_service() -> BiomarkerService:
    return BiomarkerService()
