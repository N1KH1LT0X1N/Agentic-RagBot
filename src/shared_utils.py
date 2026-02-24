"""
MediGuard AI — Shared Utilities

Common functions used by both the main API and HuggingFace deployment:
- Biomarker parsing
- Disease scoring heuristics
- Result formatting
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Biomarker Parsing
# ---------------------------------------------------------------------------

# Canonical biomarker name mapping (aliases -> standard name)
BIOMARKER_ALIASES: Dict[str, str] = {
    # Glucose
    "glucose": "Glucose",
    "fasting glucose": "Glucose",
    "fastingglucose": "Glucose",
    "blood sugar": "Glucose",
    "blood glucose": "Glucose",
    "fbg": "Glucose",
    "fbs": "Glucose",
    
    # HbA1c
    "hba1c": "HbA1c",
    "a1c": "HbA1c",
    "hemoglobin a1c": "HbA1c",
    "hemoglobina1c": "HbA1c",
    "glycated hemoglobin": "HbA1c",
    
    # Cholesterol
    "cholesterol": "Cholesterol",
    "total cholesterol": "Cholesterol",
    "totalcholesterol": "Cholesterol",
    "tc": "Cholesterol",
    
    # LDL
    "ldl": "LDL",
    "ldl cholesterol": "LDL",
    "ldlcholesterol": "LDL",
    "ldl-c": "LDL",
    
    # HDL
    "hdl": "HDL",
    "hdl cholesterol": "HDL",
    "hdlcholesterol": "HDL",
    "hdl-c": "HDL",
    
    # Triglycerides
    "triglycerides": "Triglycerides",
    "tg": "Triglycerides",
    "trigs": "Triglycerides",
    
    # Hemoglobin
    "hemoglobin": "Hemoglobin",
    "hgb": "Hemoglobin",
    "hb": "Hemoglobin",
    
    # TSH
    "tsh": "TSH",
    "thyroid stimulating hormone": "TSH",
    
    # Creatinine
    "creatinine": "Creatinine",
    "cr": "Creatinine",
    
    # ALT/AST
    "alt": "ALT",
    "sgpt": "ALT",
    "ast": "AST",
    "sgot": "AST",
    
    # Blood pressure
    "systolic": "Systolic_BP",
    "systolic bp": "Systolic_BP",
    "sbp": "Systolic_BP",
    "diastolic": "Diastolic_BP",
    "diastolic bp": "Diastolic_BP",
    "dbp": "Diastolic_BP",
    
    # BMI
    "bmi": "BMI",
    "body mass index": "BMI",
}


def normalize_biomarker_name(name: str) -> str:
    """
    Normalize a biomarker name to its canonical form.
    
    Args:
        name: Raw biomarker name (may be alias, mixed case, etc.)
    
    Returns:
        Canonical biomarker name
    """
    key = name.lower().strip().replace("_", " ")
    return BIOMARKER_ALIASES.get(key, name)


def parse_biomarkers(text: str) -> Dict[str, float]:
    """
    Parse biomarkers from natural language text or JSON.
    
    Supports formats like:
    - JSON: {"Glucose": 140, "HbA1c": 7.5}
    - Key-value: "Glucose: 140, HbA1c: 7.5"
    - Natural: "glucose 140 mg/dL and hba1c 7.5%"
    
    Args:
        text: Input text containing biomarker values
    
    Returns:
        Dictionary of normalized biomarker names to float values
    """
    text = text.strip()
    
    if not text:
        return {}
    
    # Try JSON first
    if text.startswith("{"):
        try:
            raw = json.loads(text)
            return {normalize_biomarker_name(k): float(v) for k, v in raw.items()}
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    
    # Regex patterns for biomarker extraction
    patterns = [
        # "Glucose: 140" or "Glucose = 140" or "Glucose - 140"
        r"([A-Za-z][A-Za-z0-9_\s]{0,30})\s*[:=\-]\s*([\d.]+)",
        # "Glucose 140 mg/dL" (value after name with optional unit)
        r"\b([A-Za-z][A-Za-z0-9_]{0,15})\s+([\d.]+)\s*(?:mg/dL|mmol/L|%|g/dL|U/L|mIU/L|ng/mL|pg/mL|μmol/L|umol/L)?(?:\s|,|$)",
    ]
    
    biomarkers: Dict[str, float] = {}
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name, value = match.groups()
            name = name.strip()
            
            # Skip common non-biomarker words
            if name.lower() in {"the", "a", "an", "and", "or", "is", "was", "are", "were", "be"}:
                continue
            
            try:
                fval = float(value)
                canonical = normalize_biomarker_name(name)
                # Don't overwrite if already found (first match wins)
                if canonical not in biomarkers:
                    biomarkers[canonical] = fval
            except ValueError:
                continue
    
    return biomarkers


# ---------------------------------------------------------------------------
# Disease Scoring Heuristics
# ---------------------------------------------------------------------------

# Reference ranges for biomarkers (approximate clinical ranges)
BIOMARKER_REFERENCE_RANGES: Dict[str, Tuple[float, float, str]] = {
    # (low, high, unit)
    "Glucose": (70, 100, "mg/dL"),
    "HbA1c": (4.0, 5.6, "%"),
    "Cholesterol": (0, 200, "mg/dL"),
    "LDL": (0, 100, "mg/dL"),
    "HDL": (40, 999, "mg/dL"),  # Higher is better
    "Triglycerides": (0, 150, "mg/dL"),
    "Hemoglobin": (12.0, 17.5, "g/dL"),
    "TSH": (0.4, 4.0, "mIU/L"),
    "Creatinine": (0.6, 1.2, "mg/dL"),
    "ALT": (7, 56, "U/L"),
    "AST": (10, 40, "U/L"),
    "Systolic_BP": (90, 120, "mmHg"),
    "Diastolic_BP": (60, 80, "mmHg"),
    "BMI": (18.5, 24.9, "kg/m²"),
}


def classify_biomarker(name: str, value: float) -> str:
    """
    Classify a biomarker value as normal, low, or high.
    
    Args:
        name: Canonical biomarker name
        value: Measured value
    
    Returns:
        "normal", "low", or "high"
    """
    ranges = BIOMARKER_REFERENCE_RANGES.get(name)
    if not ranges:
        return "unknown"
    
    low, high, _ = ranges
    
    if value < low:
        return "low"
    elif value > high:
        return "high"
    else:
        return "normal"


def score_disease_diabetes(biomarkers: Dict[str, float]) -> Tuple[float, str]:
    """
    Score diabetes risk based on biomarkers.
    
    Returns: (score 0-1, severity)
    """
    glucose = biomarkers.get("Glucose", 0)
    hba1c = biomarkers.get("HbA1c", 0)
    
    score = 0.0
    reasons = []
    
    # HbA1c scoring (most important)
    if hba1c >= 6.5:
        score += 0.5
        reasons.append(f"HbA1c {hba1c}% >= 6.5% (diabetes threshold)")
    elif hba1c >= 5.7:
        score += 0.3
        reasons.append(f"HbA1c {hba1c}% in prediabetes range")
    
    # Fasting glucose scoring
    if glucose >= 126:
        score += 0.35
        reasons.append(f"Glucose {glucose} mg/dL >= 126 (diabetes threshold)")
    elif glucose >= 100:
        score += 0.2
        reasons.append(f"Glucose {glucose} mg/dL in prediabetes range")
    
    # Normalize to 0-1
    score = min(1.0, score)
    
    # Determine severity
    if score >= 0.7:
        severity = "high"
    elif score >= 0.4:
        severity = "moderate"
    else:
        severity = "low"
    
    return score, severity


def score_disease_dyslipidemia(biomarkers: Dict[str, float]) -> Tuple[float, str]:
    """Score dyslipidemia risk based on lipid panel."""
    cholesterol = biomarkers.get("Cholesterol", 0)
    ldl = biomarkers.get("LDL", 0)
    hdl = biomarkers.get("HDL", 999)  # High default (higher is better)
    triglycerides = biomarkers.get("Triglycerides", 0)
    
    score = 0.0
    
    if cholesterol >= 240:
        score += 0.3
    elif cholesterol >= 200:
        score += 0.15
    
    if ldl >= 160:
        score += 0.3
    elif ldl >= 130:
        score += 0.15
    
    if hdl < 40:
        score += 0.2
    
    if triglycerides >= 200:
        score += 0.2
    elif triglycerides >= 150:
        score += 0.1
    
    score = min(1.0, score)
    
    if score >= 0.6:
        severity = "high"
    elif score >= 0.3:
        severity = "moderate"
    else:
        severity = "low"
    
    return score, severity


def score_disease_anemia(biomarkers: Dict[str, float]) -> Tuple[float, str]:
    """Score anemia risk based on hemoglobin."""
    hemoglobin = biomarkers.get("Hemoglobin", 0)
    
    if not hemoglobin:
        return 0.0, "unknown"
    
    if hemoglobin < 8:
        return 0.9, "critical"
    elif hemoglobin < 10:
        return 0.7, "high"
    elif hemoglobin < 12:
        return 0.5, "moderate"
    elif hemoglobin < 13:
        return 0.2, "low"
    else:
        return 0.0, "normal"


def score_disease_thyroid(biomarkers: Dict[str, float]) -> Tuple[float, str, str]:
    """Score thyroid disorder risk. Returns: (score, severity, direction)."""
    tsh = biomarkers.get("TSH", 0)
    
    if not tsh:
        return 0.0, "unknown", "none"
    
    if tsh > 10:
        return 0.8, "high", "hypothyroid"
    elif tsh > 4.5:
        return 0.5, "moderate", "hypothyroid"
    elif tsh < 0.1:
        return 0.8, "high", "hyperthyroid"
    elif tsh < 0.4:
        return 0.5, "moderate", "hyperthyroid"
    else:
        return 0.0, "normal", "none"


def score_all_diseases(biomarkers: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """
    Score all disease risks based on available biomarkers.
    
    Args:
        biomarkers: Dictionary of biomarker values
    
    Returns:
        Dictionary of disease -> {score, severity, disease, confidence}
    """
    results = {}
    
    # Diabetes
    score, severity = score_disease_diabetes(biomarkers)
    if score > 0:
        results["diabetes"] = {
            "disease": "Diabetes",
            "confidence": score,
            "severity": severity,
        }
    
    # Dyslipidemia
    score, severity = score_disease_dyslipidemia(biomarkers)
    if score > 0:
        results["dyslipidemia"] = {
            "disease": "Dyslipidemia",
            "confidence": score,
            "severity": severity,
        }
    
    # Anemia
    score, severity = score_disease_anemia(biomarkers)
    if score > 0:
        results["anemia"] = {
            "disease": "Anemia",
            "confidence": score,
            "severity": severity,
        }
    
    # Thyroid
    score, severity, direction = score_disease_thyroid(biomarkers)
    if score > 0:
        disease_name = "Hypothyroidism" if direction == "hypothyroid" else "Hyperthyroidism"
        results["thyroid"] = {
            "disease": disease_name,
            "confidence": score,
            "severity": severity,
        }
    
    return results


def get_primary_prediction(biomarkers: Dict[str, float]) -> Dict[str, Any]:
    """
    Get the highest-confidence disease prediction.
    
    Args:
        biomarkers: Dictionary of biomarker values
    
    Returns:
        Dictionary with disease, confidence, severity
    """
    scores = score_all_diseases(biomarkers)
    
    if not scores:
        return {
            "disease": "General Health Screening",
            "confidence": 0.5,
            "severity": "low",
        }
    
    # Return highest confidence
    best = max(scores.values(), key=lambda x: x["confidence"])
    return best


# ---------------------------------------------------------------------------
# Biomarker Flagging
# ---------------------------------------------------------------------------

def flag_biomarkers(biomarkers: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Flag abnormal biomarkers with classification and reference ranges.
    
    Args:
        biomarkers: Dictionary of biomarker values
    
    Returns:
        List of flagged biomarkers with details
    """
    flags = []
    
    for name, value in biomarkers.items():
        classification = classify_biomarker(name, value)
        ranges = BIOMARKER_REFERENCE_RANGES.get(name)
        
        flag = {
            "name": name,
            "value": value,
            "status": classification,
        }
        
        if ranges:
            low, high, unit = ranges
            flag["reference_range"] = f"{low}-{high} {unit}"
            flag["unit"] = unit
        
        if classification != "normal":
            flag["flagged"] = True
        
        flags.append(flag)
    
    # Sort: flagged first, then by name
    flags.sort(key=lambda x: (not x.get("flagged", False), x["name"]))
    
    return flags


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def format_confidence_percent(score: float) -> str:
    """Format confidence score as percentage string."""
    return f"{int(score * 100)}%"


def severity_to_emoji(severity: str) -> str:
    """Convert severity level to emoji."""
    mapping = {
        "critical": "🔴",
        "high": "🟠",
        "moderate": "🟡",
        "low": "🟢",
        "normal": "✅",
        "unknown": "❓",
    }
    return mapping.get(severity.lower(), "⚪")
