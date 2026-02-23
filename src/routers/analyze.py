"""
MediGuard AI — Analyze Router

Backward-compatible /analyze/natural and /analyze/structured endpoints
that delegate to the existing ClinicalInsightGuild workflow.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from src.schemas.schemas import (
    AnalysisResponse,
    ErrorResponse,
    NaturalAnalysisRequest,
    StructuredAnalysisRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analysis"])


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
    if ragbot is None:
        raise HTTPException(status_code=503, detail="Analysis service unavailable")

    try:
        result = await ragbot.analyze(biomarkers, patient_ctx)
    except Exception as exc:
        logger.exception("Guild analysis failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline error: {exc}",
        )

    elapsed = (time.time() - t0) * 1000

    # The guild returns a dict shaped like AnalysisResponse — pass through
    return AnalysisResponse(
        status="success",
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        extracted_biomarkers=extracted_biomarkers,
        input_biomarkers=biomarkers,
        patient_context=patient_ctx,
        processing_time_ms=round(elapsed, 1),
        **{k: v for k, v in result.items() if k not in ("status", "request_id", "timestamp", "extracted_biomarkers", "input_biomarkers", "patient_context", "processing_time_ms")},
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
