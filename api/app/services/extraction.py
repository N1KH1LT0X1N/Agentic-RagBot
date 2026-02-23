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
from src.biomarker_normalization import normalize_biomarker_name
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
# EXTRACTION HELPERS
# ============================================================================

def _parse_llm_json(content: str) -> Dict[str, Any]:
    """Parse JSON payload from LLM output with fallback recovery."""
    text = content.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        left = text.find("{")
        right = text.rfind("}")
        if left != -1 and right != -1 and right > left:
            return json.loads(text[left:right + 1])
        raise


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
        
        extracted = _parse_llm_json(content)
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
    
    # Helper: check both abbreviated and normalized biomarker names
    # Returns None when biomarker is not present (avoids false triggers)
    def _get(name, *alt_names):
        val = biomarkers.get(name, None)
        if val is not None:
            return val
        for alt in alt_names:
            val = biomarkers.get(alt, None)
            if val is not None:
                return val
        return None

    # Diabetes indicators
    glucose = _get("Glucose")
    hba1c = _get("HbA1c")
    if glucose is not None and glucose > 126:
        scores["Diabetes"] += 0.4
    if glucose is not None and glucose > 180:
        scores["Diabetes"] += 0.2
    if hba1c is not None and hba1c >= 6.5:
        scores["Diabetes"] += 0.5
    
    # Anemia indicators
    hemoglobin = _get("Hemoglobin")
    mcv = _get("Mean Corpuscular Volume", "MCV")
    if hemoglobin is not None and hemoglobin < 12.0:
        scores["Anemia"] += 0.6
    if hemoglobin is not None and hemoglobin < 10.0:
        scores["Anemia"] += 0.2
    if mcv is not None and mcv < 80:
        scores["Anemia"] += 0.2
    
    # Heart disease indicators
    cholesterol = _get("Cholesterol")
    troponin = _get("Troponin")
    ldl = _get("LDL Cholesterol", "LDL")
    if cholesterol is not None and cholesterol > 240:
        scores["Heart Disease"] += 0.3
    if troponin is not None and troponin > 0.04:
        scores["Heart Disease"] += 0.6
    if ldl is not None and ldl > 190:
        scores["Heart Disease"] += 0.2
    
    # Thrombocytopenia indicators
    platelets = _get("Platelets")
    if platelets is not None and platelets < 150000:
        scores["Thrombocytopenia"] += 0.6
    if platelets is not None and platelets < 50000:
        scores["Thrombocytopenia"] += 0.3
    
    # Thalassemia indicators (simplified)
    if mcv is not None and hemoglobin is not None and mcv < 80 and hemoglobin < 12.0:
        scores["Thalassemia"] += 0.4
    
    # Find top prediction
    top_disease = max(scores, key=scores.get)
    confidence = min(scores[top_disease], 1.0)  # Cap at 1.0 for Pydantic validation

    if confidence == 0.0:
        top_disease = "Undetermined"
    
    # Normalize probabilities to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        probabilities = {k: v / total for k, v in scores.items()}
    else:
        probabilities = {k: 1.0 / len(scores) for k in scores}
    
    return {
        "disease": top_disease,
        "confidence": confidence,
        "probabilities": probabilities
    }
