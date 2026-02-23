"""
MediGuard AI RAG-Helper
State definitions for LangGraph workflow
"""

from typing import Dict, List, Any, Optional, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel, ConfigDict
from src.config import ExplanationSOP
import operator


class AgentOutput(BaseModel):
    """Structured output from each specialist agent"""
    agent_name: str
    findings: Any
    metadata: Optional[Dict[str, Any]] = None


class BiomarkerFlag(BaseModel):
    """Structure for flagged biomarker values"""
    name: str
    value: float
    unit: str
    status: str  # "NORMAL", "HIGH", "LOW", "CRITICAL_HIGH", "CRITICAL_LOW"
    reference_range: str
    warning: Optional[str] = None


class SafetyAlert(BaseModel):
    """Structure for safety warnings"""
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    biomarker: Optional[str] = None
    message: str
    action: str


class KeyDriver(BaseModel):
    """Biomarker contribution to prediction"""
    biomarker: str
    value: Any
    contribution: Optional[str] = None
    explanation: str
    evidence: Optional[str] = None


class GuildState(TypedDict):
    """
    The shared state/workspace for the Clinical Insight Guild.
    Passed between all agent nodes in the LangGraph workflow.
    """
    
    # === Input Data ===
    patient_biomarkers: Dict[str, float]  # Raw biomarker values
    model_prediction: Dict[str, Any]  # Disease prediction from ML model
    patient_context: Optional[Dict[str, Any]]  # Age, gender, BMI, etc.
    
    # === Workflow Control ===
    plan: Optional[Dict[str, Any]]  # Execution plan from Planner
    sop: ExplanationSOP  # Current operating procedures
    
    # === Agent Outputs (Accumulated) - Use Annotated with operator.add for parallel updates ===
    agent_outputs: Annotated[List[AgentOutput], operator.add]
    biomarker_flags: Annotated[List[BiomarkerFlag], operator.add]
    safety_alerts: Annotated[List[SafetyAlert], operator.add]
    biomarker_analysis: Optional[Dict[str, Any]]
    
    # === Final Structured Output ===
    final_response: Optional[Dict[str, Any]]
    
    # === Metadata ===
    processing_timestamp: Optional[str]
    sop_version: Optional[str]


# === Input Schema for Patient Data ===
class PatientInput(BaseModel):
    """Standard input format for patient assessment"""
    
    biomarkers: Dict[str, float]
    
    model_prediction: Dict[str, Any]  # Contains: disease, confidence, probabilities
    
    patient_context: Optional[Dict[str, Any]] = None
    
    def model_post_init(self, __context: Any) -> None:
        if self.patient_context is None:
            self.patient_context = {"age": None, "gender": None, "bmi": None}
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "biomarkers": {
                "Glucose": 185,
                "HbA1c": 8.2,
                "Hemoglobin": 13.5,
                "Platelets": 220000,
                "Cholesterol": 210
            },
            "model_prediction": {
                "disease": "Diabetes",
                "confidence": 0.89,
                "probabilities": {
                    "Diabetes": 0.89,
                    "Heart Disease": 0.06,
                    "Anemia": 0.03,
                    "Thalassemia": 0.01,
                    "Thrombocytopenia": 0.01
                }
            },
            "patient_context": {
                "age": 52,
                "gender": "male",
                "bmi": 31.2
            }
        }
    })
