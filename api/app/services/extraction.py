"""
Biomarker Extraction Service
Extracts biomarker values from natural language text using LLM
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from src.llm_config import get_chat_model


# ============================================================================
# EXTRACTION PROMPT
# ============================================================================

BIOMARKER_EXTRACTION_PROMPT = """You are a medical data extraction assistant. 
Extract biomarker values from the user's message.

Known biomarkers (24 total):
Glucose, Cholesterol, Triglycerides, HbA1c, LDL, HDL, Insulin, BMI,
Hemoglobin, Platelets, WBC (White Blood Cells), RBC (Red Blood Cells), 
Hematocrit, MCV, MCH, MCHC, Heart Rate, Systolic BP, Diastolic BP, 
Troponin, C-reactive Protein, ALT, AST, Creatinine

User message: {user_message}

Extract all biomarker names and their values. Return ONLY valid JSON (no other text):
{{
  "biomarkers": {{
    "Glucose": 140,
    "HbA1c": 7.5
  }},
  "patient_context": {{
    "age": null,
    "gender": null,
    "bmi": null
  }}
}}

If you cannot find any biomarkers, return {{"biomarkers": {{}}, "patient_context": {{}}}}.
"""


# ============================================================================
# BIOMARKER NAME NORMALIZATION
# ============================================================================

def normalize_biomarker_name(name: str) -> str:
    """
    Normalize biomarker names to standard format.
    Handles 30+ common variations (e.g., blood sugar -> Glucose)
    
    Args:
        name: Raw biomarker name from user input
    
    Returns:
        Standardized biomarker name
    """
    name_lower = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Comprehensive mapping of variations to standard names
    mappings = {
        # Glucose variations
        "glucose": "Glucose",
        "bloodsugar": "Glucose",
        "bloodglucose": "Glucose",
        
        # Lipid panel
        "cholesterol": "Cholesterol",
        "totalcholesterol": "Cholesterol",
        "triglycerides": "Triglycerides",
        "trig": "Triglycerides",
        "ldl": "LDL",
        "ldlcholesterol": "LDL",
        "hdl": "HDL",
        "hdlcholesterol": "HDL",
        
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
        "wbc": "WBC",
        "whitebloodcells": "WBC",
        "whitecells": "WBC",
        "rbc": "RBC",
        "redbloodcells": "RBC",
        "redcells": "RBC",
        "hematocrit": "Hematocrit",
        "hct": "Hematocrit",
        
        # Red blood cell indices
        "mcv": "MCV",
        "meancorpuscularvolume": "MCV",
        "mch": "MCH",
        "meancorpuscularhemoglobin": "MCH",
        "mchc": "MCHC",
        
        # Cardiovascular
        "heartrate": "Heart Rate",
        "hr": "Heart Rate",
        "pulse": "Heart Rate",
        "systolicbp": "Systolic BP",
        "systolic": "Systolic BP",
        "sbp": "Systolic BP",
        "diastolicbp": "Diastolic BP",
        "diastolic": "Diastolic BP",
        "dbp": "Diastolic BP",
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
    
    return mappings.get(name_lower, name)


# ============================================================================
# EXTRACTION FUNCTION
# ============================================================================

def extract_biomarkers(
    user_message: str, 
    ollama_base_url: str = None  # Kept for backward compatibility, ignored
) -> Tuple[Dict[str, float], Dict[str, Any], str]:
    """
    Extract biomarker values from natural language using LLM.
    
    Args:
        user_message: Natural language text containing biomarker information
        ollama_base_url: DEPRECATED - uses cloud LLM (Groq/Gemini) instead
    
    Returns:
        Tuple of (biomarkers_dict, patient_context_dict, error_message)
        - biomarkers_dict: Normalized biomarker names -> values
        - patient_context_dict: Extracted patient context (age, gender, BMI)
        - error_message: Empty string if successful, error description if failed
    
    Example:
        >>> biomarkers, context, error = extract_biomarkers("My glucose is 185 and HbA1c is 8.2")
        >>> print(biomarkers)
        {'Glucose': 185.0, 'HbA1c': 8.2}
    """
    try:
        # Initialize LLM (uses Groq/Gemini by default - FREE)
        llm = get_chat_model(temperature=0.0)
        
        prompt = ChatPromptTemplate.from_template(BIOMARKER_EXTRACTION_PROMPT)
        chain = prompt | llm
        
        # Invoke LLM
        response = chain.invoke({"user_message": user_message})
        content = response.content.strip()
        
        # Parse JSON from LLM response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        extracted = json.loads(content)
        biomarkers = extracted.get("biomarkers", {})
        patient_context = extracted.get("patient_context", {})
        
        # Normalize biomarker names and convert to float
        normalized = {}
        for key, value in biomarkers.items():
            try:
                standard_name = normalize_biomarker_name(key)
                normalized[standard_name] = float(value)
            except (ValueError, TypeError):
                # Skip invalid values
                continue
        
        # Clean up patient context (remove null values)
        patient_context = {k: v for k, v in patient_context.items() if v is not None}
        
        if not normalized:
            return {}, patient_context, "No biomarkers found in the input"
        
        return normalized, patient_context, ""
        
    except json.JSONDecodeError as e:
        return {}, {}, f"Failed to parse LLM response as JSON: {str(e)}"
    
    except Exception as e:
        return {}, {}, f"Extraction failed: {str(e)}"


# ============================================================================
# SIMPLE DISEASE PREDICTION (Fallback)
# ============================================================================

def predict_disease_simple(biomarkers: Dict[str, float]) -> Dict[str, Any]:
    """
    Simple rule-based disease prediction based on key biomarkers.
    Used as a fallback when no ML model is available.
    
    Args:
        biomarkers: Dictionary of biomarker names to values
    
    Returns:
        Dictionary with disease, confidence, and probabilities
    """
    scores = {
        "Diabetes": 0.0,
        "Anemia": 0.0,
        "Heart Disease": 0.0,
        "Thrombocytopenia": 0.0,
        "Thalassemia": 0.0
    }
    
    # Diabetes indicators
    glucose = biomarkers.get("Glucose", 0)
    hba1c = biomarkers.get("HbA1c", 0)
    if glucose > 126:
        scores["Diabetes"] += 0.4
    if glucose > 180:
        scores["Diabetes"] += 0.2
    if hba1c >= 6.5:
        scores["Diabetes"] += 0.5
    
    # Anemia indicators
    hemoglobin = biomarkers.get("Hemoglobin", 0)
    mcv = biomarkers.get("MCV", 0)
    if hemoglobin < 12.0:
        scores["Anemia"] += 0.6
    if hemoglobin < 10.0:
        scores["Anemia"] += 0.2
    if mcv < 80:
        scores["Anemia"] += 0.2
    
    # Heart disease indicators
    cholesterol = biomarkers.get("Cholesterol", 0)
    troponin = biomarkers.get("Troponin", 0)
    ldl = biomarkers.get("LDL", 0)
    if cholesterol > 240:
        scores["Heart Disease"] += 0.3
    if troponin > 0.04:
        scores["Heart Disease"] += 0.6
    if ldl > 190:
        scores["Heart Disease"] += 0.2
    
    # Thrombocytopenia indicators
    platelets = biomarkers.get("Platelets", 0)
    if platelets < 150000:
        scores["Thrombocytopenia"] += 0.6
    if platelets < 50000:
        scores["Thrombocytopenia"] += 0.3
    
    # Thalassemia indicators (simplified)
    if mcv < 80 and hemoglobin < 12.0:
        scores["Thalassemia"] += 0.4
    
    # Find top prediction
    top_disease = max(scores, key=scores.get)
    confidence = scores[top_disease]
    
    # Ensure minimum confidence
    if confidence < 0.5:
        confidence = 0.5
        top_disease = "Diabetes"  # Default
    
    # Normalize probabilities to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        probabilities = {k: v/total for k, v in scores.items()}
    else:
        probabilities = {k: 1.0/len(scores) for k in scores}
    
    return {
        "disease": top_disease,
        "confidence": confidence,
        "probabilities": probabilities
    }
