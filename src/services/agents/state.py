"""
MediGuard AI — Agentic RAG State

Enhanced LangGraph state for the guardrail → retrieve → grade → generate
pipeline that wraps the existing 6-agent clinical workflow.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Annotated
from typing_extensions import TypedDict
import operator


class AgenticRAGState(TypedDict):
    """State flowing through the agentic RAG graph."""

    # ── Input ────────────────────────────────────────────────────────────
    query: str
    biomarkers: Optional[Dict[str, float]]
    patient_context: Optional[Dict[str, Any]]

    # ── Guardrail ────────────────────────────────────────────────────────
    guardrail_score: float            # 0-100 medical-relevance score
    is_in_scope: bool                 # passed guardrail?

    # ── Retrieval ────────────────────────────────────────────────────────
    retrieved_documents: List[Dict[str, Any]]
    retrieval_attempts: int
    max_retrieval_attempts: int

    # ── Grading ──────────────────────────────────────────────────────────
    grading_results: List[Dict[str, Any]]
    relevant_documents: List[Dict[str, Any]]
    needs_rewrite: bool

    # ── Rewriting ────────────────────────────────────────────────────────
    rewritten_query: Optional[str]

    # ── Generation / routing ─────────────────────────────────────────────
    routing_decision: str             # "analyze" | "rag_answer" | "out_of_scope"
    final_answer: Optional[str]
    analysis_result: Optional[Dict[str, Any]]

    # ── Metadata ─────────────────────────────────────────────────────────
    trace_id: Optional[str]
    errors: Annotated[List[str], operator.add]
