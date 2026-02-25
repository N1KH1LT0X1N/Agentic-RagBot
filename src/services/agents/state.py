"""
MediGuard AI — Agentic RAG State

Enhanced LangGraph state for the guardrail → retrieve → grade → generate
pipeline that wraps the existing 6-agent clinical workflow.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


class AgenticRAGState(TypedDict):
    """State flowing through the agentic RAG graph."""

    # ── Input ────────────────────────────────────────────────────────────
    query: str
    biomarkers: dict[str, float] | None
    patient_context: dict[str, Any] | None

    # ── Guardrail ────────────────────────────────────────────────────────
    guardrail_score: float            # 0-100 medical-relevance score
    is_in_scope: bool                 # passed guardrail?

    # ── Retrieval ────────────────────────────────────────────────────────
    retrieved_documents: list[dict[str, Any]]
    retrieval_attempts: int
    max_retrieval_attempts: int

    # ── Grading ──────────────────────────────────────────────────────────
    grading_results: list[dict[str, Any]]
    relevant_documents: list[dict[str, Any]]
    needs_rewrite: bool

    # ── Rewriting ────────────────────────────────────────────────────────
    rewritten_query: str | None

    # ── Generation / routing ─────────────────────────────────────────────
    routing_decision: str             # "analyze" | "rag_answer" | "out_of_scope"
    final_answer: str | None
    analysis_result: dict[str, Any] | None

    # ── Metadata ─────────────────────────────────────────────────────────
    trace_id: str | None
    errors: Annotated[list[str], operator.add]
