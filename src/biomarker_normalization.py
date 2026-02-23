"""
MediGuard AI RAG-Helper
Shared biomarker normalization utilities
"""

from typing import Dict

# Normalization map for biomarker aliases to canonical names.
NORMALIZATION_MAP: Dict[str, str] = {
    # Glucose variations
    "glucose": "Glucose",
    "bloodsugar": "Glucose",
    "bloodglucose": "Glucose",

    # Lipid panel
    "cholesterol": "Cholesterol",
    "totalcholesterol": "Cholesterol",
    "triglycerides": "Triglycerides",
    "trig": "Triglycerides",
    "ldl": "LDL Cholesterol",
    "ldlcholesterol": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "hdlcholesterol": "HDL Cholesterol",

    # Diabetes markers
    "hba1c": "HbA1c",
    "a1c": "HbA1c",
    "hemoglobina1c": "HbA1c",
    "insulin": "Insulin",

    # Body metrics
    "bmi": "BMI",
    "bodymassindex": "BMI",

    # Complete Blood Count (CBC)
    "hemoglobin": "Hemoglobin",
    "hgb": "Hemoglobin",
    "hb": "Hemoglobin",
    "platelets": "Platelets",
    "plt": "Platelets",
    "wbc": "White Blood Cells",
    "whitebloodcells": "White Blood Cells",
    "whitecells": "White Blood Cells",
    "rbc": "Red Blood Cells",
    "redbloodcells": "Red Blood Cells",
    "redcells": "Red Blood Cells",
    "hematocrit": "Hematocrit",
    "hct": "Hematocrit",

    # Red blood cell indices
    "mcv": "Mean Corpuscular Volume",
    "meancorpuscularvolume": "Mean Corpuscular Volume",
    "mch": "Mean Corpuscular Hemoglobin",
    "meancorpuscularhemoglobin": "Mean Corpuscular Hemoglobin",
    "mchc": "Mean Corpuscular Hemoglobin Concentration",

    # Cardiovascular
    "heartrate": "Heart Rate",
    "hr": "Heart Rate",
    "pulse": "Heart Rate",
    "systolicbp": "Systolic Blood Pressure",
    "systolic": "Systolic Blood Pressure",
    "sbp": "Systolic Blood Pressure",
    "diastolicbp": "Diastolic Blood Pressure",
    "diastolic": "Diastolic Blood Pressure",
    "dbp": "Diastolic Blood Pressure",
    "troponin": "Troponin",

    # Inflammation and liver
    "creactiveprotein": "C-reactive Protein",
    "crp": "C-reactive Protein",
    "alt": "ALT",
    "alanineaminotransferase": "ALT",
    "ast": "AST",
    "aspartateaminotransferase": "AST",

    # Kidney
    "creatinine": "Creatinine",
}


def normalize_biomarker_name(name: str) -> str:
    """
    Normalize biomarker names to standard format.

    Args:
        name: Raw biomarker name from user input

    Returns:
        Standardized biomarker name
    """
    key = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    return NORMALIZATION_MAP.get(key, name)
