"""
MediGuard AI — Guardrail Node

Validates that the user query is within the medical domain (score 0-100).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.services.agents.prompts import GUARDRAIL_SYSTEM

logger = logging.getLogger(__name__)


def guardrail_node(state: dict, *, context: Any) -> dict:
    """Score the query for medical relevance (0-100)."""
    query = state.get("query", "")
    biomarkers = state.get("biomarkers")

    if context.tracer:
        context.tracer.trace(name="guardrail_node", metadata={"query": query})

    # Fast path: if biomarkers are provided, it's definitely medical
    if biomarkers:
        return {
            "guardrail_score": 95.0,
            "is_in_scope": True,
            "routing_decision": "analyze",
        }

    try:
        response = context.llm.invoke(
            [
                {"role": "system", "content": GUARDRAIL_SYSTEM},
                {"role": "user", "content": query},
            ]
        )
        content = response.content.strip()
        # Parse JSON response
        if "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            if content.startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        score = float(data.get("score", 0))
    except Exception as exc:
        logger.warning("Guardrail LLM failed: %s — defaulting to in-scope", exc)
        score = 70.0  # benefit of the doubt

    is_in_scope = score >= 40
    routing = "rag_answer" if is_in_scope else "out_of_scope"

    return {
        "guardrail_score": score,
        "is_in_scope": is_in_scope,
        "routing_decision": routing,
    }
