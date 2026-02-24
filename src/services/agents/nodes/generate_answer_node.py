"""
MediGuard AI — Generate Answer Node

Produces a RAG-grounded medical answer with citations.
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.agents.prompts import RAG_GENERATION_SYSTEM

logger = logging.getLogger(__name__)


def generate_answer_node(state: dict, *, context: Any) -> dict:
    """Generate a cited medical answer from relevant documents."""
    query = state.get("rewritten_query") or state.get("query", "")
    documents = state.get("relevant_documents", [])
    biomarkers = state.get("biomarkers")
    patient_context = state.get("patient_context", "")

    # Build evidence block
    evidence_parts: list[str] = []
    for i, doc in enumerate(documents, 1):
        meta = doc.get("metadata", {})
        title = meta.get("title", doc.get("title", "Unknown"))
        section = meta.get("section_title", doc.get("section", ""))
        text = (doc.get("content") or doc.get("text", ""))[:2000]
        header = f"[{i}] {title}"
        if section:
            header += f" — {section}"
        evidence_parts.append(f"{header}\n{text}")
    evidence_block = "\n\n---\n\n".join(evidence_parts) if evidence_parts else "(No evidence retrieved)"

    # Build user message
    user_msg = f"Question: {query}\n\n"
    if biomarkers:
        user_msg += f"Biomarkers: {biomarkers}\n\n"
    if patient_context:
        user_msg += f"Patient context: {patient_context}\n\n"
    user_msg += f"Evidence:\n{evidence_block}"

    try:
        response = context.llm.invoke(
            [
                {"role": "system", "content": RAG_GENERATION_SYSTEM},
                {"role": "user", "content": user_msg},
            ]
        )
        answer = response.content.strip()
    except Exception as exc:
        logger.error("Generation LLM failed: %s", exc)
        answer = (
            "I apologize, but I'm temporarily unable to generate a response. "
            "Please consult a healthcare professional for guidance."
        )
        return {"final_answer": answer, "errors": [str(exc)]}

    return {"final_answer": answer}
