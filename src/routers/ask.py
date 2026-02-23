"""
MediGuard AI — Ask Router

Free-form medical Q&A powered by the agentic RAG pipeline.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from src.schemas.schemas import AskRequest, AskResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
async def ask_medical_question(body: AskRequest, request: Request):
    """Answer a free-form medical question via agentic RAG."""
    rag_service = getattr(request.app.state, "rag_service", None)
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service unavailable")

    request_id = f"req_{uuid.uuid4().hex[:12]}"
    t0 = time.time()

    try:
        result = rag_service.ask(
            query=body.question,
            biomarkers=body.biomarkers,
            patient_context=body.patient_context or "",
        )
    except Exception as exc:
        logger.exception("Agentic RAG failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {exc}")

    elapsed = (time.time() - t0) * 1000

    return AskResponse(
        status="success",
        request_id=request_id,
        question=body.question,
        answer=result.get("final_answer", ""),
        guardrail_score=result.get("guardrail_score"),
        documents_retrieved=len(result.get("retrieved_documents", [])),
        documents_relevant=len(result.get("relevant_documents", [])),
        processing_time_ms=round(elapsed, 1),
    )
