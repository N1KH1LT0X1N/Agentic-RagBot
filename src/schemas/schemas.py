"""
MediGuard AI — Production API Schemas

Pydantic v2 request/response models for the new production API layer.
Keeps backward compatibility with existing schemas where possible.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# REQUEST MODELS
# ============================================================================


class PatientContext(BaseModel):
    """Patient demographic and context information."""

    age: Optional[int] = Field(None, ge=0, le=120, description="Patient age in years")
    gender: Optional[str] = Field(None, description="Patient gender (male/female)")
    bmi: Optional[float] = Field(None, ge=10, le=60, description="Body Mass Index")
    patient_id: Optional[str] = Field(None, description="Patient identifier")


class NaturalAnalysisRequest(BaseModel):
    """Natural language biomarker analysis request."""

    message: str = Field(
        ..., min_length=5, max_length=2000,
        description="Natural language message with biomarker values",
    )
    patient_context: Optional[PatientContext] = Field(
        default_factory=PatientContext,
    )


class StructuredAnalysisRequest(BaseModel):
    """Structured biomarker analysis request."""

    biomarkers: Dict[str, float] = Field(
        ..., description="Dict of biomarker name → measured value",
    )
    patient_context: Optional[PatientContext] = Field(
        default_factory=PatientContext,
    )

    @field_validator("biomarkers")
    @classmethod
    def biomarkers_not_empty(cls, v: Dict[str, float]) -> Dict[str, float]:
        if not v:
            raise ValueError("biomarkers must contain at least one entry")
        return v


class AskRequest(BaseModel):
    """Free‑form medical question (agentic RAG pipeline)."""

    question: str = Field(
        ..., min_length=3, max_length=4000,
        description="Medical question",
    )
    biomarkers: Optional[Dict[str, float]] = Field(
        None, description="Optional biomarker context",
    )
    patient_context: Optional[str] = Field(
        None, description="Free‑text patient context",
    )


class SearchRequest(BaseModel):
    """Direct hybrid search (no LLM generation)."""

    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)
    mode: str = Field("hybrid", description="Search mode: bm25 | vector | hybrid")


# ============================================================================
# RESPONSE BUILDING BLOCKS
# ============================================================================


class BiomarkerFlag(BaseModel):
    name: str
    value: float
    unit: str
    status: str
    reference_range: str
    warning: Optional[str] = None


class SafetyAlert(BaseModel):
    severity: str
    biomarker: Optional[str] = None
    message: str
    action: str


class KeyDriver(BaseModel):
    biomarker: str
    value: Any
    contribution: Optional[str] = None
    explanation: str
    evidence: Optional[str] = None


class Prediction(BaseModel):
    disease: str
    confidence: float = Field(ge=0, le=1)
    probabilities: Dict[str, float]


class DiseaseExplanation(BaseModel):
    pathophysiology: str
    citations: List[str] = Field(default_factory=list)
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None


class Recommendations(BaseModel):
    immediate_actions: List[str] = Field(default_factory=list)
    lifestyle_changes: List[str] = Field(default_factory=list)
    monitoring: List[str] = Field(default_factory=list)
    follow_up: Optional[str] = None


class ConfidenceAssessment(BaseModel):
    prediction_reliability: str
    evidence_strength: str
    limitations: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None


class AgentOutput(BaseModel):
    agent_name: str
    findings: Any
    metadata: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None


class Analysis(BaseModel):
    biomarker_flags: List[BiomarkerFlag]
    safety_alerts: List[SafetyAlert]
    key_drivers: List[KeyDriver]
    disease_explanation: DiseaseExplanation
    recommendations: Recommendations
    confidence_assessment: ConfidenceAssessment
    alternative_diagnoses: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# TOP‑LEVEL RESPONSES
# ============================================================================


class AnalysisResponse(BaseModel):
    """Full clinical analysis response (backward‑compatible)."""

    status: str
    request_id: str
    timestamp: str
    extracted_biomarkers: Optional[Dict[str, float]] = None
    input_biomarkers: Dict[str, float]
    patient_context: Dict[str, Any]
    prediction: Prediction
    analysis: Analysis
    agent_outputs: List[AgentOutput]
    workflow_metadata: Dict[str, Any]
    conversational_summary: Optional[str] = None
    processing_time_ms: float
    sop_version: Optional[str] = None


class AskResponse(BaseModel):
    """Response from the agentic RAG /ask endpoint."""

    status: str = "success"
    request_id: str
    question: str
    answer: str
    guardrail_score: Optional[float] = None
    documents_retrieved: int = 0
    documents_relevant: int = 0
    processing_time_ms: float = 0.0


class SearchResponse(BaseModel):
    """Direct hybrid search response."""

    status: str = "success"
    query: str
    mode: str
    total_hits: int
    results: List[Dict[str, Any]]
    processing_time_ms: float = 0.0


class ErrorResponse(BaseModel):
    """Error envelope."""

    status: str = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: Optional[str] = None


# ============================================================================
# HEALTH / INFO
# ============================================================================


class ServiceHealth(BaseModel):
    name: str
    status: str  # ok | degraded | unavailable
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Production health check."""

    status: str  # healthy | degraded | unhealthy
    timestamp: str
    version: str
    uptime_seconds: float
    services: List[ServiceHealth] = Field(default_factory=list)


class BiomarkerReferenceRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    male: Optional[Dict[str, float]] = None
    female: Optional[Dict[str, float]] = None


class BiomarkerInfo(BaseModel):
    name: str
    unit: str
    normal_range: BiomarkerReferenceRange
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
