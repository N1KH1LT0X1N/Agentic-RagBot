"""
MediGuard AI — Agentic RAG Orchestrator

LangGraph StateGraph that wires all nodes into the guardrail → retrieve → grade → generate pipeline.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from src.services.agents.context import AgenticContext
from src.services.agents.nodes.generate_answer_node import generate_answer_node
from src.services.agents.nodes.grade_documents_node import grade_documents_node
from src.services.agents.nodes.guardrail_node import guardrail_node
from src.services.agents.nodes.out_of_scope_node import out_of_scope_node
from src.services.agents.nodes.retrieve_node import retrieve_node
from src.services.agents.nodes.rewrite_query_node import rewrite_query_node
from src.services.agents.state import AgenticRAGState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Edge routing helpers
# ---------------------------------------------------------------------------


def _route_after_guardrail(state: dict) -> str:
    """Decide path after guardrail evaluation."""
    if state.get("routing_decision") == "analyze":
        # Biomarker analysis pathway — goes straight to retrieve
        return "retrieve"
    if state.get("is_in_scope"):
        return "retrieve"
    return "out_of_scope"


def _route_after_grading(state: dict) -> str:
    """Decide whether to rewrite query or proceed to generation."""
    if state.get("needs_rewrite"):
        return "rewrite_query"
    if not state.get("relevant_documents"):
        return "generate_answer"  # will produce a "no evidence found" answer
    return "generate_answer"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_agentic_rag_graph(context: AgenticContext) -> Any:
    """Construct the compiled LangGraph for the agentic RAG pipeline.

    Parameters
    ----------
    context:
        Runtime dependencies (LLM, OpenSearch, embeddings, cache, tracer).

    Returns
    -------
    Compiled LangGraph graph ready for ``.invoke()`` / ``.stream()``.
    """
    workflow = StateGraph(AgenticRAGState)

    # Bind context to every node via functools.partial
    workflow.add_node("guardrail", partial(guardrail_node, context=context))
    workflow.add_node("retrieve", partial(retrieve_node, context=context))
    workflow.add_node("grade_documents", partial(grade_documents_node, context=context))
    workflow.add_node("rewrite_query", partial(rewrite_query_node, context=context))
    workflow.add_node("generate_answer", partial(generate_answer_node, context=context))
    workflow.add_node("out_of_scope", partial(out_of_scope_node, context=context))

    # Entry point
    workflow.set_entry_point("guardrail")

    # Conditional edges
    workflow.add_conditional_edges(
        "guardrail",
        _route_after_guardrail,
        {
            "retrieve": "retrieve",
            "out_of_scope": "out_of_scope",
        },
    )

    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        _route_after_grading,
        {
            "rewrite_query": "rewrite_query",
            "generate_answer": "generate_answer",
        },
    )

    # After rewrite, loop back to retrieve
    workflow.add_edge("rewrite_query", "retrieve")

    # Terminal edges
    workflow.add_edge("generate_answer", END)
    workflow.add_edge("out_of_scope", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class AgenticRAGService:
    """High-level wrapper around the compiled RAG graph."""

    def __init__(self, context: AgenticContext) -> None:
        self._context = context
        self._graph = build_agentic_rag_graph(context)

    def ask(
        self,
        query: str,
        biomarkers: dict | None = None,
        patient_context: str = "",
    ) -> dict:
        """Run the full agentic RAG pipeline and return the final state."""
        initial_state: dict[str, Any] = {
            "query": query,
            "biomarkers": biomarkers,
            "patient_context": patient_context,
            "errors": [],
        }

        trace_obj = None
        try:
            if self._context.tracer:
                trace_obj = self._context.tracer.trace(
                    name="agentic_rag_ask",
                    metadata={"query": query},
                )
            result = self._graph.invoke(initial_state)
            return result
        except Exception as exc:
            logger.error("Agentic RAG pipeline failed: %s", exc)
            return {
                **initial_state,
                "final_answer": (
                    "I apologize, but I'm temporarily unable to process your request. "
                    "Please consult a healthcare professional."
                ),
                "errors": [str(exc)],
            }
        finally:
            if self._context.tracer:
                self._context.tracer.flush()
