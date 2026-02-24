"""
MediGuard AI — Ask Router

Free-form medical Q&A powered by the agentic RAG pipeline.
Supports both synchronous and SSE streaming responses.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

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


# ---------------------------------------------------------------------------
# SSE Streaming Endpoint
# ---------------------------------------------------------------------------


async def _stream_rag_response(
    rag_service,
    question: str,
    biomarkers: dict | None,
    patient_context: str,
    request_id: str,
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for streaming RAG responses.
    
    Event types:
    - status: Pipeline stage updates
    - token: Individual response tokens
    - metadata: Retrieval/grading info
    - done: Final completion signal
    - error: Error information
    """
    t0 = time.time()
    
    try:
        # Send initial status
        yield f"event: status\ndata: {json.dumps({'stage': 'guardrail', 'message': 'Validating query...'})}\n\n"
        await asyncio.sleep(0)  # Allow event loop to flush
        
        # Run the RAG pipeline (synchronous, but we yield progress)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: rag_service.ask(
                query=question,
                biomarkers=biomarkers,
                patient_context=patient_context,
            )
        )
        
        # Send retrieval metadata
        yield f"event: metadata\ndata: {json.dumps({'documents_retrieved': len(result.get('retrieved_documents', [])), 'documents_relevant': len(result.get('relevant_documents', [])), 'guardrail_score': result.get('guardrail_score')})}\n\n"
        await asyncio.sleep(0)
        
        # Stream the answer token by token for smooth UI
        answer = result.get("final_answer", "")
        if answer:
            yield f"event: status\ndata: {json.dumps({'stage': 'generating', 'message': 'Generating response...'})}\n\n"
            
            # Simulate streaming by chunking the response
            words = answer.split()
            chunk_size = 3  # Send 3 words at a time
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
                await asyncio.sleep(0.02)  # Small delay for visual streaming effect
        
        # Send completion
        elapsed = (time.time() - t0) * 1000
        yield f"event: done\ndata: {json.dumps({'request_id': request_id, 'processing_time_ms': round(elapsed, 1), 'status': 'success'})}\n\n"
        
    except Exception as exc:
        logger.exception("Streaming RAG failed: %s", exc)
        yield f"event: error\ndata: {json.dumps({'error': str(exc), 'request_id': request_id})}\n\n"


@router.post("/ask/stream")
async def ask_medical_question_stream(body: AskRequest, request: Request):
    """
    Stream a medical Q&A response via Server-Sent Events (SSE).
    
    Events:
    - `status`: Pipeline stage updates (guardrail, retrieve, grade, generate)
    - `token`: Individual response tokens for real-time display
    - `metadata`: Retrieval statistics (documents found, relevance scores)
    - `done`: Completion signal with timing info
    - `error`: Error details if something fails
    
    Example client code (JavaScript):
    ```javascript
    const eventSource = new EventSource('/ask/stream', {
        method: 'POST',
        body: JSON.stringify({ question: 'What causes high glucose?' })
    });
    
    eventSource.addEventListener('token', (e) => {
        const data = JSON.parse(e.data);
        document.getElementById('response').innerHTML += data.text;
    });
    ```
    """
    rag_service = getattr(request.app.state, "rag_service", None)
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    
    return StreamingResponse(
        _stream_rag_response(
            rag_service,
            body.question,
            body.biomarkers,
            body.patient_context or "",
            request_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
