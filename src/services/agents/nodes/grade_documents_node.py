"""
MediGuard AI — Grade Documents Node

Uses the LLM to judge whether each retrieved document is relevant to the query.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.services.agents.prompts import GRADING_SYSTEM

logger = logging.getLogger(__name__)


def grade_documents_node(state: dict, *, context: Any) -> dict:
    """Grade each retrieved document for relevance."""
    query = state.get("rewritten_query") or state.get("query", "")
    documents = state.get("retrieved_documents", [])

    if context.tracer:
        context.tracer.trace(name="grade_documents_node", metadata={"query": query})

    if not documents:
        return {
            "grading_results": [],
            "relevant_documents": [],
            "needs_rewrite": True,
        }

    relevant: list[dict] = []
    grading_results: list[dict] = []

    for doc in documents:
        text = doc.get("content") or doc.get("text", "")
        user_msg = f"Query: {query}\n\nDocument:\n{text[:2000]}"
        try:
            response = context.llm.invoke(
                [
                    {"role": "system", "content": GRADING_SYSTEM},
                    {"role": "user", "content": user_msg},
                ]
            )
            content = response.content.strip()
            if "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                if content.startswith("json"):
                    content = content[4:].strip()
            data = json.loads(content)
            is_relevant = str(data.get("relevant", "false")).lower() == "true"
        except Exception as exc:
            logger.warning("Grading LLM failed for doc %s: %s — marking relevant", doc.get("id"), exc)
            is_relevant = True  # benefit of the doubt

        grading_results.append({"doc_id": doc.get("id", doc.get("_id")), "relevant": is_relevant})
        if is_relevant:
            relevant.append(doc)

    attempts = state.get("retrieval_attempts", 1)
    max_attempts = state.get("max_retrieval_attempts", 2)
    needs_rewrite = len(relevant) < 2 and attempts < max_attempts

    return {
        "grading_results": grading_results,
        "relevant_documents": relevant,
        "needs_rewrite": needs_rewrite,
    }
