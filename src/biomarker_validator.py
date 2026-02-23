"""
MediGuard AI RAG-Helper
Biomarker analysis and validation utilities
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from src.state import BiomarkerFlag, SafetyAlert


class BiomarkerValidator:
    """Validates biomarker values against reference ranges"""
    
    def __init__(self, reference_file: str = "config/biomarker_references.json"):
        """Load biomarker reference ranges from JSON file"""
        ref_path = Path(__file__).parent.parent / reference_file
        with open(ref_path, 'r') as f:
            self.references = json.load(f)['biomarkers']
    
    def validate_biomarker(
        self, 
        name: str, 
        value: float, 
        gender: Optional[str] = None,
        threshold_pct: float = 0.0
    ) -> BiomarkerFlag:
        """
        Validate a single biomarker value against reference ranges.
        
        Args:
            name: Biomarker name
            value: Measured value
            gender: "male" or "female" (for gender-specific ranges)
            threshold_pct: Only flag LOW/HIGH if deviation from boundary exceeds this fraction (e.g. 0.15 = 15%)
        
        Returns:
            BiomarkerFlag object with status and warnings
        """
        if name not in self.references:
            return BiomarkerFlag(
                name=name,
                value=value,
                unit="unknown",
                status="UNKNOWN",
                reference_range="No reference data available",
                warning=f"No reference range found for {name}"
            )
        
        ref = self.references[name]
        unit = ref['unit']
        
        # Handle gender-specific ranges
        if ref.get('gender_specific', False) and gender:
            if gender.lower() in ['male', 'm']:
                normal = ref['normal_range']['male']
            elif gender.lower() in ['female', 'f']:
                normal = ref['normal_range']['female']
            else:
                normal = ref['normal_range']
        else:
            normal = ref['normal_range']
        
        min_val = normal.get('min', 0)
        max_val = normal.get('max', float('inf'))
        critical_low = ref.get('critical_low')
        critical_high = ref.get('critical_high')
        
        # Determine status
        status = "NORMAL"
        warning = None
        
        # Check critical values first (threshold_pct does not suppress critical alerts)
        if critical_low and value < critical_low:
            status = "CRITICAL_LOW"
            warning = f"CRITICAL: {name} is {value} {unit}, below critical threshold of {critical_low} {unit}. {ref['clinical_significance'].get('low', 'Seek immediate medical attention.')}"
        elif critical_high and value > critical_high:
            status = "CRITICAL_HIGH"
            warning = f"CRITICAL: {name} is {value} {unit}, above critical threshold of {critical_high} {unit}. {ref['clinical_significance'].get('high', 'Seek immediate medical attention.')}"
        elif value < min_val:
            # Only flag if deviation exceeds threshold_pct fraction of the boundary
            deviation = (min_val - value) / min_val if min_val != 0 else 1.0
            if deviation > threshold_pct:
                status = "LOW"
                warning = f"{name} is {value} {unit}, below normal range ({min_val}-{max_val} {unit}). {ref['clinical_significance'].get('low', '')}"
        elif value > max_val:
            deviation = (value - max_val) / max_val if max_val != 0 else 1.0
            if deviation > threshold_pct:
                status = "HIGH"
                warning = f"{name} is {value} {unit}, above normal range ({min_val}-{max_val} {unit}). {ref['clinical_significance'].get('high', '')}"
        
        reference_range = f"{min_val}-{max_val} {unit}"
        
        return BiomarkerFlag(
            name=name,
            value=value,
            unit=unit,
            status=status,
            reference_range=reference_range,
            warning=warning
        )
    
    def validate_all(
        self,
        biomarkers: Dict[str, float],
        gender: Optional[str] = None,
        threshold_pct: float = 0.0
    ) -> Tuple[List[BiomarkerFlag], List[SafetyAlert]]:
        """
        Validate all biomarker values.
        
        Args:
            biomarkers: Dict of biomarker name -> value
            gender: "male" or "female" (for gender-specific ranges)
            threshold_pct: Only flag LOW/HIGH if deviation exceeds this fraction (e.g. 0.15 = 15%)
        
        Returns:
            Tuple of (biomarker_flags, safety_alerts)
        """
        flags = []
        alerts = []
        
        for name, value in biomarkers.items():
            flag = self.validate_biomarker(name, value, gender, threshold_pct)
            flags.append(flag)
            
            # Generate safety alerts for critical values
            if flag.status in ["CRITICAL_LOW", "CRITICAL_HIGH"]:
                alerts.append(SafetyAlert(
                    severity="CRITICAL",
                    biomarker=name,
                    message=flag.warning or f"{name} at critical level",
                    action="SEEK IMMEDIATE MEDICAL ATTENTION"
                ))
            elif flag.status in ["LOW", "HIGH"]:
                severity = "HIGH" if "severe" in (flag.warning or "").lower() else "MEDIUM"
                alerts.append(SafetyAlert(
                    severity=severity,
                    biomarker=name,
                    message=flag.warning or f"{name} out of normal range",
                    action="Consult with healthcare provider"
                ))
        
        return flags, alerts
    
    def get_biomarker_info(self, name: str) -> Optional[Dict]:
        """Get reference information for a biomarker"""
        return self.references.get(name)

    def expected_biomarker_count(self) -> int:
        """Return expected number of biomarkers from reference ranges."""
        return len(self.references)
    
    def get_disease_relevant_biomarkers(self, disease: str) -> List[str]:
        """
        Get list of biomarkers most relevant to a specific disease.
        
        This is a simplified mapping - in production, this would be more sophisticated.
        """
        disease_map = {
            "Diabetes": [
                "Glucose", "HbA1c", "Insulin", "BMI", 
                "Triglycerides", "HDL Cholesterol", "LDL Cholesterol"
            ],
            "Anemia": [
                "Hemoglobin", "Red Blood Cells", "Hematocrit", 
                "Mean Corpuscular Volume", "Mean Corpuscular Hemoglobin",
                "Mean Corpuscular Hemoglobin Concentration"
            ],
            "Thrombocytopenia": [
                "Platelets", "White Blood Cells", "Hemoglobin"
            ],
            "Thalassemia": [
                "Hemoglobin", "Red Blood Cells", "Mean Corpuscular Volume",
                "Mean Corpuscular Hemoglobin", "Hematocrit"
            ],
            "Heart Disease": [
                "Cholesterol", "LDL Cholesterol", "HDL Cholesterol",
                "Triglycerides", "Troponin", "C-reactive Protein",
                "Systolic Blood Pressure", "Diastolic Blood Pressure",
                "Heart Rate", "BMI"
            ]
        }
        
        return disease_map.get(disease, [])
