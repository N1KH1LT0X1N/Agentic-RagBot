"""
MediGuard AI — Production API Schemas

Pydantic v2 request/response models for the new production API layer.
Keeps backward compatibility with existing schemas where possible.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# REQUEST MODELS
# ============================================================================


class PatientContext(BaseModel):
    """Patient demographic and context information."""

    age: int | None = Field(None, ge=0, le=120, description="Patient age in years")
    gender: str | None = Field(None, description="Patient gender (male/female)")
    bmi: float | None = Field(None, ge=10, le=60, description="Body Mass Index")
    patient_id: str | None = Field(None, description="Patient identifier")


class NaturalAnalysisRequest(BaseModel):
    """Natural language biomarker analysis request."""

    message: str = Field(
        ..., min_length=5, max_length=2000,
        description="Natural language message with biomarker values",
    )
    patient_context: PatientContext | None = Field(
        default_factory=PatientContext,
    )


class StructuredAnalysisRequest(BaseModel):
    """Structured biomarker analysis request."""

    biomarkers: dict[str, float] = Field(
        ..., description="Dict of biomarker name → measured value",
    )
    patient_context: PatientContext | None = Field(
        default_factory=PatientContext,
    )

    @field_validator("biomarkers")
    @classmethod
    def biomarkers_not_empty(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("biomarkers must contain at least one entry")
        return v


class AskRequest(BaseModel):
    """Free‑form medical question (agentic RAG pipeline)."""

    question: str = Field(
        ..., min_length=3, max_length=4000,
        description="Medical question",
    )
    biomarkers: dict[str, float] | None = Field(
        None, description="Optional biomarker context",
    )
    patient_context: str | None = Field(
        None, description="Free‑text patient context",
    )


class SearchRequest(BaseModel):
    """Direct hybrid search (no LLM generation)."""

    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)
    mode: str = Field("hybrid", description="Search mode: bm25 | vector | hybrid")


class FeedbackRequest(BaseModel):
    """User feedback for RAG responses."""
    request_id: str = Field(..., description="ID of the request being rated")
    score: float = Field(..., ge=0, le=1, description="Normalized score 0.0 to 1.0")
    comment: str | None = Field(None, description="Optional textual feedback")


class FeedbackResponse(BaseModel):
    status: str = "success"
    request_id: str


# ============================================================================
# RESPONSE BUILDING BLOCKS
# ============================================================================


class BiomarkerFlag(BaseModel):
    name: str
    value: float
    unit: str
    status: str
    reference_range: str
    warning: str | None = None


class SafetyAlert(BaseModel):
    severity: str
    biomarker: str | None = None
    message: str
    action: str


class KeyDriver(BaseModel):
    biomarker: str
    value: Any
    contribution: str | None = None
    explanation: str
    evidence: str | None = None


class Prediction(BaseModel):
    disease: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]


class DiseaseExplanation(BaseModel):
    pathophysiology: str
    citations: list[str] = Field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] | None = None


class Recommendations(BaseModel):
    immediate_actions: list[str] = Field(default_factory=list)
    lifestyle_changes: list[str] = Field(default_factory=list)
    monitoring: list[str] = Field(default_factory=list)
    follow_up: str | None = None


class ConfidenceAssessment(BaseModel):
    prediction_reliability: str
    evidence_strength: str
    limitations: list[str] = Field(default_factory=list)
    reasoning: str | None = None


class AgentOutput(BaseModel):
    agent_name: str
    findings: Any
    metadata: dict[str, Any] | None = None
    execution_time_ms: float | None = None


class Analysis(BaseModel):
    biomarker_flags: list[BiomarkerFlag]
    safety_alerts: list[SafetyAlert]
    key_drivers: list[KeyDriver]
    disease_explanation: DiseaseExplanation
    recommendations: Recommendations
    confidence_assessment: ConfidenceAssessment
    alternative_diagnoses: list[dict[str, Any]] | None = None


# ============================================================================
# TOP‑LEVEL RESPONSES
# ============================================================================


class AnalysisResponse(BaseModel):
    """Full clinical analysis response (backward‑compatible)."""

    status: str
    request_id: str
    timestamp: str
    extracted_biomarkers: dict[str, float] | None = None
    input_biomarkers: dict[str, float]
    patient_context: dict[str, Any]
    prediction: Prediction
    analysis: Analysis
    agent_outputs: list[AgentOutput]
    workflow_metadata: dict[str, Any]
    conversational_summary: str | None = None
    processing_time_ms: float
    sop_version: str | None = None


class AskResponse(BaseModel):
    """Response from the agentic RAG /ask endpoint."""

    status: str = "success"
    request_id: str
    question: str
    answer: str
    guardrail_score: float | None = None
    documents_retrieved: int = 0
    documents_relevant: int = 0
    processing_time_ms: float = 0.0


class SearchResponse(BaseModel):
    """Direct hybrid search response."""

    status: str = "success"
    query: str
    mode: str
    total_hits: int
    results: list[dict[str, Any]]
    processing_time_ms: float = 0.0


class ErrorResponse(BaseModel):
    """Error envelope."""

    status: str = "error"
    error_code: str
    message: str
    details: dict[str, Any] | None = None
    timestamp: str
    request_id: str | None = None


# ============================================================================
# HEALTH / INFO
# ============================================================================


class ServiceHealth(BaseModel):
    name: str
    status: str  # ok | degraded | unavailable
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """Production health check."""

    status: str  # healthy | degraded | unhealthy
    timestamp: str
    version: str
    uptime_seconds: float
    services: list[ServiceHealth] = Field(default_factory=list)


class BiomarkerReferenceRange(BaseModel):
    min: float | None = None
    max: float | None = None
    male: dict[str, float] | None = None
    female: dict[str, float] | None = None


class BiomarkerInfo(BaseModel):
    name: str
    unit: str
    normal_range: BiomarkerReferenceRange
    critical_low: float | None = None
    critical_high: float | None = None
