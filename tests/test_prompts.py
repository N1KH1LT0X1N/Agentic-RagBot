"""
Tests for src/services/agents/prompts.py — prompt templates.
"""

from src.services.agents.prompts import (
    GRADING_SYSTEM,
    GUARDRAIL_SYSTEM,
    OUT_OF_SCOPE_RESPONSE,
    RAG_GENERATION_SYSTEM,
    REWRITE_SYSTEM,
)


def test_guardrail_prompt_has_score():
    """Guardrail prompt should ask for a 0-100 score."""
    assert "score" in GUARDRAIL_SYSTEM.lower()
    assert "0" in GUARDRAIL_SYSTEM
    assert "100" in GUARDRAIL_SYSTEM


def test_grading_prompt_has_relevant():
    """Grading prompt should ask for relevant true/false."""
    assert "relevant" in GRADING_SYSTEM.lower()


def test_rag_generation_has_citation():
    """RAG generation prompt should mention citations."""
    assert "citation" in RAG_GENERATION_SYSTEM.lower() or "cite" in RAG_GENERATION_SYSTEM.lower()


def test_out_of_scope_is_polite():
    """Out-of-scope response should be informative and polite."""
    assert "medical" in OUT_OF_SCOPE_RESPONSE.lower()
    assert len(OUT_OF_SCOPE_RESPONSE) > 50


def test_rewrite_prompt_exists():
    assert len(REWRITE_SYSTEM) > 50
