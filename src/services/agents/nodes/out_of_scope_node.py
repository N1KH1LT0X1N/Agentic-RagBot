"""
MediGuard AI — Out-of-Scope Node

Returns a polite rejection for non-medical queries.
"""

from __future__ import annotations

from typing import Any

from src.services.agents.prompts import OUT_OF_SCOPE_RESPONSE


def out_of_scope_node(state: dict, *, context: Any) -> dict:
    """Return polite out-of-scope message."""
    if context.tracer:
        context.tracer.trace(name="out_of_scope_node", metadata={"query": state.get("query", "")})
    return {"final_answer": OUT_OF_SCOPE_RESPONSE}
