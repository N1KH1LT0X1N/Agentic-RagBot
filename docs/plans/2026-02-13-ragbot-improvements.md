# RagBot Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align RagBot’s workflow outputs, normalization, and guardrails with a reliable, testable, and deterministic implementation.

**Architecture:** Introduce shared biomarker normalization and explicit state fields to remove nondeterminism, unify the workflow response schema, and tighten guardrails (citations, parsing, logging). Update prediction logic and confidence handling for safer outputs and strengthen observability.

**Tech Stack:** Python, LangGraph, FastAPI, Pydantic, LangChain, FAISS, pytest.

---

### Task 1: Shared Biomarker Normalization

**Files:**
- Create: `src/biomarker_normalization.py`
- Modify: `api/app/services/extraction.py`
- Modify: `scripts/chat.py`
- Test: `tests/test_normalization.py`

**Step 1: Write the failing test**

```python
from src.biomarker_normalization import normalize_biomarker_name

def test_normalizes_common_aliases():
    assert normalize_biomarker_name("ldl") == "LDL Cholesterol"
    assert normalize_biomarker_name("wbc") == "White Blood Cells"
    assert normalize_biomarker_name("systolic bp") == "Systolic Blood Pressure"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalization.py::test_normalizes_common_aliases -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.biomarker_normalization'`

**Step 3: Write minimal implementation**

```python
from typing import Dict

NORMALIZATION_MAP: Dict[str, str] = {
    "ldl": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "wbc": "White Blood Cells",
    "rbc": "Red Blood Cells",
    "systolicbp": "Systolic Blood Pressure",
    "diastolicbp": "Diastolic Blood Pressure",
}

def normalize_biomarker_name(name: str) -> str:
    key = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    return NORMALIZATION_MAP.get(key, name)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalization.py::test_normalizes_common_aliases -v`
Expected: PASS

**Step 5: Wire normalization into API + CLI**

Replace local normalization in `api/app/services/extraction.py` and `scripts/chat.py` with `normalize_biomarker_name` from the new module, and align returned names with `config/biomarker_references.json`.

**Step 6: Commit**

```bash
git add src/biomarker_normalization.py api/app/services/extraction.py scripts/chat.py tests/test_normalization.py
git commit -m "feat: centralize biomarker normalization"
```

### Task 2: Deterministic State Propagation

**Files:**
- Modify: `src/state.py`
- Modify: `src/agents/biomarker_analyzer.py`
- Modify: `src/agents/biomarker_linker.py`
- Modify: `src/agents/clinical_guidelines.py`
- Modify: `src/agents/confidence_assessor.py`
- Test: `tests/test_state_fields.py`

**Step 1: Write the failing test**

```python
from src.state import GuildState

def test_state_has_biomarker_analysis_field():
    required_fields = {"biomarker_analysis", "biomarker_flags", "safety_alerts"}
    assert required_fields.issubset(GuildState.__annotations__.keys())
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_state_fields.py::test_state_has_biomarker_analysis_field -v`
Expected: FAIL with `AssertionError`

**Step 3: Write minimal implementation**

```python
class GuildState(TypedDict):
    biomarker_analysis: Optional[Dict[str, Any]]
```

Update `biomarker_analyzer.analyze()` to return `biomarker_flags`, `safety_alerts`, and `biomarker_analysis` in the state payload. Update downstream agents to read from `state["biomarker_analysis"]` instead of scanning `agent_outputs`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_state_fields.py::test_state_has_biomarker_analysis_field -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/state.py src/agents/biomarker_analyzer.py src/agents/biomarker_linker.py src/agents/clinical_guidelines.py src/agents/confidence_assessor.py tests/test_state_fields.py
git commit -m "fix: propagate biomarker analysis via state"
```

### Task 3: Canonical Workflow Response Schema

**Files:**
- Modify: `src/agents/response_synthesizer.py`
- Modify: `api/app/services/ragbot.py`
- Test: `tests/test_response_mapping.py`

**Step 1: Write the failing test**

```python
from app.services.ragbot import RagBotService

def test_format_response_uses_synthesizer_payload():
    service = RagBotService()
    workflow_result = {
        "biomarker_flags": [{"name": "Glucose", "value": 120, "unit": "mg/dL", "status": "HIGH", "reference_range": "70-100 mg/dL"}],
        "safety_alerts": [],
        "prediction_explanation": {"primary_disease": "Diabetes", "confidence": 0.6, "key_drivers": []},
        "clinical_recommendations": {"immediate_actions": [], "lifestyle_changes": [], "monitoring": []},
        "confidence_assessment": {"prediction_reliability": "LOW", "evidence_strength": "WEAK", "limitations": []},
        "patient_summary": {"narrative": ""}
    }
    response = service._format_response(
        request_id="req_test",
        workflow_result=workflow_result,
        input_biomarkers={"Glucose": 120},
        extracted_biomarkers=None,
        patient_context={},
        model_prediction={"disease": "Diabetes", "confidence": 0.6, "probabilities": {}},
        processing_time_ms=10.0
    )
    assert response.analysis.biomarker_flags[0].name == "Glucose"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_response_mapping.py::test_format_response_uses_synthesizer_payload -v`
Expected: FAIL because `_format_response` reads absent top-level keys.

**Step 3: Write minimal implementation**

Update `ResponseSynthesizerAgent` to include both the existing narrative schema and the API-expected keys at top-level (e.g., `biomarker_flags`, `safety_alerts`, `key_drivers`, `disease_explanation`, `recommendations`, `confidence_assessment`, `alternative_diagnoses`).

Update `_format_response` in `RagBotService` to read from the synthesizer payload first, falling back to legacy keys where needed.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_response_mapping.py::test_format_response_uses_synthesizer_payload -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agents/response_synthesizer.py api/app/services/ragbot.py tests/test_response_mapping.py
git commit -m "fix: align workflow response schema"
```

### Task 4: Safe Prediction Confidence Handling

**Files:**
- Modify: `api/app/services/extraction.py`
- Modify: `scripts/chat.py`
- Test: `tests/test_prediction_confidence.py`

**Step 1: Write the failing test**

```python
from app.services.extraction import predict_disease_simple

def test_low_confidence_returns_undetermined():
    result = predict_disease_simple({})
    assert result["confidence"] == 0.0
    assert result["disease"] == "Undetermined"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_prediction_confidence.py::test_low_confidence_returns_undetermined -v`
Expected: FAIL because confidence is forced to 0.5 and disease defaults to Diabetes.

**Step 3: Write minimal implementation**

Update both `predict_disease_simple` functions to:
- Preserve computed confidence (no forced minimum).
- Return `{ disease: "Undetermined", confidence: 0.0 }` when all scores are 0.
- Keep probabilities normalized when totals are > 0, otherwise return uniform probabilities.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_prediction_confidence.py::test_low_confidence_returns_undetermined -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/app/services/extraction.py scripts/chat.py tests/test_prediction_confidence.py
git commit -m "fix: remove forced disease default"
```

### Task 5: Citation Enforcement Guardrails

**Files:**
- Modify: `src/agents/disease_explainer.py`
- Modify: `src/agents/biomarker_linker.py`
- Modify: `src/agents/clinical_guidelines.py`
- Test: `tests/test_citation_guardrails.py`

**Step 1: Write the failing test**

```python
from src.agents.disease_explainer import create_disease_explainer_agent

class EmptyRetriever:
    def invoke(self, query):
        return []

def test_disease_explainer_requires_citations():
    agent = create_disease_explainer_agent(EmptyRetriever())
    state = {"model_prediction": {"disease": "Diabetes", "confidence": 0.6}, "sop": type("SOP", (), {"disease_explainer_k": 3, "require_pdf_citations": True})()}
    result = agent.explain(state)
    findings = result["agent_outputs"][0].findings
    assert findings["citations"] == []
    assert "insufficient" in findings["pathophysiology"].lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_citation_guardrails.py::test_disease_explainer_requires_citations -v`
Expected: FAIL because empty docs still produce a normal explanation.

**Step 3: Write minimal implementation**

Update each RAG agent to:
- If `state["sop"].require_pdf_citations` is True and `docs` is empty, return a safe fallback explanation and empty citations.
- Include a `citations_missing` flag in their findings for visibility.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_citation_guardrails.py::test_disease_explainer_requires_citations -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agents/disease_explainer.py src/agents/biomarker_linker.py src/agents/clinical_guidelines.py tests/test_citation_guardrails.py
git commit -m "fix: enforce citation guardrails"
```

### Task 6: Logging Cleanup (ASCII Only for API)

**Files:**
- Modify: `src/workflow.py`
- Modify: `api/app/main.py`
- Modify: `api/app/services/ragbot.py`
- Modify: `src/pdf_processor.py`
- Modify: `scripts/setup_embeddings.py`

**Step 1: Replace non-ASCII log glyphs**

Search for prefixes like `dY`, `s,?`, `o.` in non-CLI modules and replace with ASCII equivalents (e.g., `INFO:`, `WARN:`, `OK:`). Keep CLI in `scripts/chat.py` untouched unless it impacts API.

**Step 2: Run a quick lint-like grep check**

Run: `python -c "import pathlib, re; files=[p for p in pathlib.Path('.').rglob('*.py') if 'scripts/chat.py' not in str(p)]; bad=[p for p in files if re.search(r'dY|s,\?|o\.', p.read_text(encoding='utf-8'))]; print(bad)"`
Expected: `[]`

**Step 3: Commit**

```bash
git add src/workflow.py api/app/main.py api/app/services/ragbot.py src/pdf_processor.py scripts/setup_embeddings.py
git commit -m "chore: normalize API logging"
```

### Task 7: Model Selection Centralization

**Files:**
- Modify: `src/llm_config.py`
- Modify: `src/agents/response_synthesizer.py`

**Step 1: Write the failing test**

```python
from src.llm_config import llm_config

def test_get_synthesizer_returns_default():
    assert llm_config.get_synthesizer() is not None
```

**Step 2: Run test to verify it fails (if needed)**

Run: `pytest tests/test_llm_config.py::test_get_synthesizer_returns_default -v`
Expected: PASS (if already works) or FAIL if missing. If it passes, skip to Step 3.

**Step 3: Write minimal implementation**

Ensure `LLMConfig.get_synthesizer()` honors optional model names from config/SOP and `ResponseSynthesizerAgent` uses this method without hard-coded model strings.

**Step 4: Commit**

```bash
git add src/llm_config.py src/agents/response_synthesizer.py
git commit -m "refactor: centralize synthesizer selection"
```

### Task 8: Robust JSON Extraction Parsing

**Files:**
- Modify: `api/app/services/extraction.py`
- Modify: `scripts/chat.py`
- Test: `tests/test_json_parsing.py`

**Step 1: Write the failing test**

```python
from api.app.services.extraction import _parse_llm_json

def test_parse_llm_json_recovers_embedded_object():
    content = "Here is your JSON:\n```json\n{\"biomarkers\": {\"Glucose\": 140}}\n```"
    parsed = _parse_llm_json(content)
    assert parsed["biomarkers"]["Glucose"] == 140
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_json_parsing.py::test_parse_llm_json_recovers_embedded_object -v`
Expected: FAIL with `AttributeError` or JSON decode error.

**Step 3: Write minimal implementation**

Add `_parse_llm_json` helper to isolate JSON parsing with:
- Code fence stripping.
- Fallback to first `{` and last `}` if parsing fails.

Use the helper in both `extract_biomarkers` functions.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_json_parsing.py::test_parse_llm_json_recovers_embedded_object -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/app/services/extraction.py scripts/chat.py tests/test_json_parsing.py
git commit -m "fix: harden JSON extraction parsing"
```

### Task 9: Error Context + Expected Biomarker Count

**Files:**
- Modify: `src/biomarker_validator.py`
- Modify: `src/agents/confidence_assessor.py`
- Modify: `api/app/services/ragbot.py`

**Step 1: Write the failing test**

```python
from src.biomarker_validator import BiomarkerValidator

def test_expected_biomarker_count_is_reference_size():
    validator = BiomarkerValidator()
    assert validator.expected_biomarker_count() == len(validator.references)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_validator_count.py::test_expected_biomarker_count_is_reference_size -v`
Expected: FAIL with `AttributeError: expected_biomarker_count`

**Step 3: Write minimal implementation**

Add `expected_biomarker_count()` to `BiomarkerValidator` and use it in `ConfidenceAssessorAgent` instead of hard-coded 24.

Wrap errors in `RagBotService.analyze()` with an error message that includes the agent or stage if available (e.g., `Analysis failed during workflow execution`).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_validator_count.py::test_expected_biomarker_count_is_reference_size -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/biomarker_validator.py src/agents/confidence_assessor.py api/app/services/ragbot.py tests/test_validator_count.py
git commit -m "fix: derive expected biomarker count"
```

---

## Full Test Pass (Post-Implementation)

Run: `pytest -v`
Expected: All tests pass.

---

## Notes

- If any tests require API keys, mark them with `@pytest.mark.integration` and skip by default.
- Keep CLI behavior intact while removing non-ASCII logging in API modules.
