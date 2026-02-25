"""
MediGuard AI — Rewrite Query Node

Reformulates the user query to improve retrieval recall.
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.agents.prompts import REWRITE_SYSTEM

logger = logging.getLogger(__name__)


def rewrite_query_node(state: dict, *, context: Any) -> dict:
    """Rewrite the original query for better retrieval."""
    original = state.get("query", "")
    patient_context = state.get("patient_context", "")

    if context.tracer:
        context.tracer.trace(name="rewrite_query_node", metadata={"query": original})

    user_msg = f"Original query: {original}"
    if patient_context:
        user_msg += f"\n\nPatient context: {patient_context}"

    try:
        response = context.llm.invoke(
            [
                {"role": "system", "content": REWRITE_SYSTEM},
                {"role": "user", "content": user_msg},
            ]
        )
        rewritten = response.content.strip()
        if not rewritten:
            rewritten = original
    except Exception as exc:
        logger.warning("Rewrite LLM failed: %s — keeping original query", exc)
        rewritten = original

    return {"rewritten_query": rewritten}
