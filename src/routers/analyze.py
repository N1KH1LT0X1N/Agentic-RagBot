"""
MediGuard AI — Analyze Router

Unified /analyze/natural and /analyze/structured endpoints
that delegate to the ClinicalInsightGuild workflow.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from src.schemas.schemas import (
    AnalysisResponse,
    NaturalAnalysisRequest,
    StructuredAnalysisRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analysis"])

# Thread pool for running sync functions
_executor = ThreadPoolExecutor(max_workers=4)


def _score_disease_heuristic(biomarkers: Dict[str, float]) -> Dict[str, Any]:
    """Rule-based disease scoring (NOT ML prediction)."""
    scores = {
        "Diabetes": 0.0,
        "Anemia": 0.0,
        "Heart Disease": 0.0,
        "Thrombocytopenia": 0.0,
        "Thalassemia": 0.0
    }
    
    # Diabetes indicators
    glucose = biomarkers.get("Glucose")
    hba1c = biomarkers.get("HbA1c")
    if glucose is not None and glucose > 126:
        scores["Diabetes"] += 0.4
    if glucose is not None and glucose > 180:
        scores["Diabetes"] += 0.2
    if hba1c is not None and hba1c >= 6.5:
        scores["Diabetes"] += 0.5
    
    # Anemia indicators
    hemoglobin = biomarkers.get("Hemoglobin")
    mcv = biomarkers.get("Mean Corpuscular Volume", biomarkers.get("MCV"))
    if hemoglobin is not None and hemoglobin < 12.0:
        scores["Anemia"] += 0.6
    if hemoglobin is not None and hemoglobin < 10.0:
        scores["Anemia"] += 0.2
    if mcv is not None and mcv < 80:
        scores["Anemia"] += 0.2
    
    # Heart disease indicators
    cholesterol = biomarkers.get("Cholesterol")
    troponin = biomarkers.get("Troponin")
    ldl = biomarkers.get("LDL Cholesterol", biomarkers.get("LDL"))
    if cholesterol is not None and cholesterol > 240:
        scores["Heart Disease"] += 0.3
    if troponin is not None and troponin > 0.04:
        scores["Heart Disease"] += 0.6
    if ldl is not None and ldl > 190:
        scores["Heart Disease"] += 0.2
    
    # Thrombocytopenia indicators
    platelets = biomarkers.get("Platelets")
    if platelets is not None and platelets < 150000:
        scores["Thrombocytopenia"] += 0.6
    if platelets is not None and platelets < 50000:
        scores["Thrombocytopenia"] += 0.3
    
    # Thalassemia indicators
    if mcv is not None and hemoglobin is not None and mcv < 80 and hemoglobin < 12.0:
        scores["Thalassemia"] += 0.4
    
    # Find top prediction
    top_disease = max(scores, key=scores.get)
    confidence = min(scores[top_disease], 1.0)
    
    if confidence == 0.0:
        top_disease = "Undetermined"
    
    # Normalize probabilities
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


async def _run_guild_analysis(
    request: Request,
    biomarkers: Dict[str, float],
    patient_ctx: Dict[str, Any],
    extracted_biomarkers: Dict[str, float] | None = None,
) -> AnalysisResponse:
    """Execute the ClinicalInsightGuild and build the response envelope."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    t0 = time.time()

    ragbot = getattr(request.app.state, "ragbot_service", None)
    if ragbot is None or not ragbot.is_ready():
        raise HTTPException(status_code=503, detail="Analysis service unavailable. Please wait for initialization.")

    # Generate disease prediction
    model_prediction = _score_disease_heuristic(biomarkers)

    try:
        # Run sync function in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: ragbot.analyze(
                biomarkers=biomarkers,
                patient_context=patient_ctx,
                model_prediction=model_prediction,
                extracted_biomarkers=extracted_biomarkers
            )
        )
    except Exception as exc:
        logger.exception("Guild analysis failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline error: {exc}",
        )

    elapsed = (time.time() - t0) * 1000

    # Build response from result
    return AnalysisResponse(
        status="success",
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        extracted_biomarkers=extracted_biomarkers,
        input_biomarkers=biomarkers,
        patient_context=patient_ctx,
        processing_time_ms=round(elapsed, 1),
        prediction=result.prediction if hasattr(result, 'prediction') else None,
        analysis=result.analysis if hasattr(result, 'analysis') else None,
        conversational_summary=result.conversational_summary if hasattr(result, 'conversational_summary') else None,
    )


@router.post("/natural", response_model=AnalysisResponse)
async def analyze_natural(body: NaturalAnalysisRequest, request: Request):
    """Extract biomarkers from natural language and run full analysis."""
    extraction_svc = getattr(request.app.state, "extraction_service", None)
    if extraction_svc is None:
        raise HTTPException(status_code=503, detail="Extraction service unavailable")

    try:
        extracted = await extraction_svc.extract_biomarkers(body.message)
    except Exception as exc:
        logger.exception("Biomarker extraction failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not extract biomarkers: {exc}")

    patient_ctx = body.patient_context.model_dump(exclude_none=True) if body.patient_context else {}
    return await _run_guild_analysis(request, extracted, patient_ctx, extracted_biomarkers=extracted)


@router.post("/structured", response_model=AnalysisResponse)
async def analyze_structured(body: StructuredAnalysisRequest, request: Request):
    """Run full analysis on pre-structured biomarker data."""
    patient_ctx = body.patient_context.model_dump(exclude_none=True) if body.patient_context else {}
    return await _run_guild_analysis(request, body.biomarkers, patient_ctx)
