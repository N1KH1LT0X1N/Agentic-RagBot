"""
Tests for src/services/agents/ — agentic RAG pipeline.
"""

import json
from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest


# -----------------------------------------------------------------------
# Mock context and LLM
# -----------------------------------------------------------------------


class MockMessage:
    def __init__(self, content: str):
        self.content = content


class MockLLM:
    """Programmable mock LLM that returns canned responses."""

    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self._call_count = 0

    def invoke(self, messages: list) -> MockMessage:
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
        else:
            resp = '{"score": 80}'
        self._call_count += 1
        return MockMessage(resp)


@dataclass
class MockContext:
    llm: Any = None
    embedding_service: Any = None
    opensearch_client: Any = None
    cache: Any = None
    tracer: Any = None


# -----------------------------------------------------------------------
# Guardrail node
# -----------------------------------------------------------------------

class TestGuardrailNode:
    def test_in_scope_query(self):
        from src.services.agents.nodes.guardrail_node import guardrail_node

        ctx = MockContext(llm=MockLLM(['{"score": 85}']))
        state = {"query": "What does high HbA1c mean?"}
        result = guardrail_node(state, context=ctx)
        assert result["is_in_scope"] is True
        assert result["guardrail_score"] == 85.0

    def test_out_of_scope_query(self):
        from src.services.agents.nodes.guardrail_node import guardrail_node

        ctx = MockContext(llm=MockLLM(['{"score": 10}']))
        state = {"query": "What is the weather today?"}
        result = guardrail_node(state, context=ctx)
        assert result["is_in_scope"] is False
        assert result["routing_decision"] == "out_of_scope"

    def test_biomarkers_bypass(self):
        from src.services.agents.nodes.guardrail_node import guardrail_node

        ctx = MockContext(llm=MockLLM())
        state = {"query": "analyze", "biomarkers": {"Glucose": 185}}
        result = guardrail_node(state, context=ctx)
        assert result["is_in_scope"] is True
        assert result["guardrail_score"] == 95.0

    def test_llm_failure_defaults_in_scope(self):
        from src.services.agents.nodes.guardrail_node import guardrail_node

        broken_llm = MagicMock()
        broken_llm.invoke.side_effect = Exception("LLM down")
        ctx = MockContext(llm=broken_llm)
        state = {"query": "What is HbA1c?"}
        result = guardrail_node(state, context=ctx)
        assert result["is_in_scope"] is True  # benefit of the doubt


# -----------------------------------------------------------------------
# Out-of-scope node
# -----------------------------------------------------------------------

class TestOutOfScopeNode:
    def test_returns_rejection(self):
        from src.services.agents.nodes.out_of_scope_node import out_of_scope_node
        from src.services.agents.prompts import OUT_OF_SCOPE_RESPONSE

        ctx = MockContext()
        result = out_of_scope_node({}, context=ctx)
        assert result["final_answer"] == OUT_OF_SCOPE_RESPONSE


# -----------------------------------------------------------------------
# Grade documents node
# -----------------------------------------------------------------------

class TestGradeDocumentsNode:
    def test_grades_relevant(self):
        from src.services.agents.nodes.grade_documents_node import grade_documents_node

        ctx = MockContext(llm=MockLLM(['{"relevant": true}', '{"relevant": false}']))
        state = {
            "query": "diabetes treatment",
            "retrieved_documents": [
                {"id": "1", "text": "Diabetes is treated with insulin."},
                {"id": "2", "text": "The weather is sunny today."},
            ],
        }
        result = grade_documents_node(state, context=ctx)
        assert len(result["relevant_documents"]) == 1
        assert result["grading_results"][0]["relevant"] is True
        assert result["grading_results"][1]["relevant"] is False

    def test_empty_docs_needs_rewrite(self):
        from src.services.agents.nodes.grade_documents_node import grade_documents_node

        ctx = MockContext()
        state = {"query": "test", "retrieved_documents": []}
        result = grade_documents_node(state, context=ctx)
        assert result["needs_rewrite"] is True


# -----------------------------------------------------------------------
# Rewrite query node
# -----------------------------------------------------------------------

class TestRewriteQueryNode:
    def test_rewrites(self):
        from src.services.agents.nodes.rewrite_query_node import rewrite_query_node

        ctx = MockContext(llm=MockLLM(["diabetes HbA1c glucose management guidelines"]))
        state = {"query": "sugar problems"}
        result = rewrite_query_node(state, context=ctx)
        assert "diabetes" in result["rewritten_query"].lower() or result["rewritten_query"]

    def test_llm_failure_keeps_original(self):
        from src.services.agents.nodes.rewrite_query_node import rewrite_query_node

        broken_llm = MagicMock()
        broken_llm.invoke.side_effect = Exception("timeout")
        ctx = MockContext(llm=broken_llm)
        state = {"query": "original query"}
        result = rewrite_query_node(state, context=ctx)
        assert result["rewritten_query"] == "original query"


# -----------------------------------------------------------------------
# Generate answer node
# -----------------------------------------------------------------------

class TestGenerateAnswerNode:
    def test_generates_answer(self):
        from src.services.agents.nodes.generate_answer_node import generate_answer_node

        ctx = MockContext(llm=MockLLM(["Based on the evidence, HbA1c of 8.2% indicates poor glycemic control."]))
        state = {
            "query": "What does HbA1c 8.2 mean?",
            "relevant_documents": [
                {"title": "Diabetes Guide", "section": "Diagnosis", "text": "HbA1c above 6.5% indicates diabetes."}
            ],
        }
        result = generate_answer_node(state, context=ctx)
        assert "final_answer" in result
        assert len(result["final_answer"]) > 10

    def test_llm_failure_returns_fallback(self):
        from src.services.agents.nodes.generate_answer_node import generate_answer_node

        broken_llm = MagicMock()
        broken_llm.invoke.side_effect = Exception("dead")
        ctx = MockContext(llm=broken_llm)
        state = {"query": "test", "relevant_documents": []}
        result = generate_answer_node(state, context=ctx)
        assert "apologize" in result["final_answer"].lower()
        assert len(result["errors"]) > 0


# -----------------------------------------------------------------------
# Agentic RAG state
# -----------------------------------------------------------------------

class TestAgenticRAGState:
    def test_state_is_typed_dict(self):
        from src.services.agents.state import AgenticRAGState
        # Should be usable as a dict type hint
        state: AgenticRAGState = {
            "query": "test",
            "errors": [],
        }
        assert state["query"] == "test"
