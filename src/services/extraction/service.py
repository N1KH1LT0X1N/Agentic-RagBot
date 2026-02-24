"""
MediGuard AI — Biomarker Extraction Service

Extracts biomarker values from natural language text using LLM.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any, Tuple

from src.biomarker_normalization import normalize_biomarker_name

logger = logging.getLogger(__name__)


class ExtractionService:
    """Extracts biomarkers from natural language text."""

    def __init__(self, llm=None):
        self._llm = llm

    def _parse_llm_json(self, content: str) -> Dict[str, Any]:
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

    def _regex_extract(self, text: str) -> Dict[str, float]:
        """Fallback regex-based extraction."""
        biomarkers = {}
        
        # Pattern: "Glucose: 140" or "Glucose = 140" or "glucose 140"
        patterns = [
            r"([A-Za-z0-9_\s]+?)[\s:=]+(\d+\.?\d*)\s*(?:mg/dL|mmol/L|%|g/dL|U/L|mIU/L|cells/μL)?",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for name, value in matches:
                name = name.strip()
                try:
                    canonical = normalize_biomarker_name(name)
                    biomarkers[canonical] = float(value)
                except (ValueError, KeyError):
                    continue
        
        return biomarkers

    async def extract_biomarkers(self, text: str) -> Dict[str, float]:
        """
        Extract biomarkers from natural language text.
        
        Returns:
            Dict mapping biomarker names to values
        """
        if not self._llm:
            # Fallback to regex extraction
            return self._regex_extract(text)
        
        prompt = f"""You are a medical data extraction assistant. 
Extract biomarker values from the user's message.

Known biomarkers (24 total):
Glucose, Cholesterol, Triglycerides, HbA1c, LDL, HDL, Insulin, BMI,
Hemoglobin, Platelets, WBC (White Blood Cells), RBC (Red Blood Cells), 
Hematocrit, MCV, MCH, MCHC, Heart Rate, Systolic BP, Diastolic BP, 
Troponin, C-reactive Protein, ALT, AST, Creatinine

User message: {text}

Extract all biomarker names and their values. Return ONLY valid JSON (no other text):
{{"Glucose": 140, "HbA1c": 7.5}}

If you cannot find any biomarkers, return {{}}.
"""
        
        try:
            response = self._llm.invoke(prompt)
            content = response.content.strip()
            extracted = self._parse_llm_json(content)
            
            # Normalize biomarker names
            normalized = {}
            for key, value in extracted.items():
                try:
                    standard_name = normalize_biomarker_name(key)
                    normalized[standard_name] = float(value)
                except (ValueError, KeyError, TypeError):
                    logger.warning(f"Skipping invalid biomarker: {key}={value}")
                    continue
            
            return normalized
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, falling back to regex")
            return self._regex_extract(text)


def make_extraction_service(llm=None) -> ExtractionService:
    """Factory function for extraction service."""
    return ExtractionService(llm=llm)
