"""
MediGuard AI RAG-Helper
State definitions for LangGraph workflow
"""

import operator
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

from src.config import ExplanationSOP


class AgentOutput(BaseModel):
    """Structured output from each specialist agent"""
    agent_name: str
    findings: Any
    metadata: dict[str, Any] | None = None


class BiomarkerFlag(BaseModel):
    """Structure for flagged biomarker values"""
    name: str
    value: float
    unit: str
    status: str  # "NORMAL", "HIGH", "LOW", "CRITICAL_HIGH", "CRITICAL_LOW"
    reference_range: str
    warning: str | None = None


class SafetyAlert(BaseModel):
    """Structure for safety warnings"""
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    biomarker: str | None = None
    message: str
    action: str


class KeyDriver(BaseModel):
    """Biomarker contribution to prediction"""
    biomarker: str
    value: Any
    contribution: str | None = None
    explanation: str
    evidence: str | None = None


class GuildState(TypedDict):
    """
    The shared state/workspace for the Clinical Insight Guild.
    Passed between all agent nodes in the LangGraph workflow.
    """

    # === Input Data ===
    patient_biomarkers: dict[str, float]  # Raw biomarker values
    model_prediction: dict[str, Any]  # Disease prediction from ML model
    patient_context: dict[str, Any] | None  # Age, gender, BMI, etc.

    # === Workflow Control ===
    plan: dict[str, Any] | None  # Execution plan from Planner
    sop: ExplanationSOP  # Current operating procedures

    # === Agent Outputs (Accumulated) - Use Annotated with operator.add for parallel updates ===
    agent_outputs: Annotated[list[AgentOutput], operator.add]
    biomarker_flags: Annotated[list[BiomarkerFlag], operator.add]
    safety_alerts: Annotated[list[SafetyAlert], operator.add]
    biomarker_analysis: dict[str, Any] | None

    # === Final Structured Output ===
    final_response: dict[str, Any] | None

    # === Metadata ===
    processing_timestamp: str | None
    sop_version: str | None


# === Input Schema for Patient Data ===
class PatientInput(BaseModel):
    """Standard input format for patient assessment"""

    biomarkers: dict[str, float]

    model_prediction: dict[str, Any]  # Contains: disease, confidence, probabilities

    patient_context: dict[str, Any] | None = None

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
