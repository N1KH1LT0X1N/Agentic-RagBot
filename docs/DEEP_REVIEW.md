# RagBot Deep Review

> **Last updated**: February 2026  
> Items marked **[RESOLVED]** have been fixed. Items marked **[OPEN]** remain as future work.

## Scope

This review covers the end-to-end workflow and supporting services for RagBot, focusing on design correctness, reliability, safety guardrails, and maintainability. The review is based on a close reading of the workflow orchestration, agent implementations, API wiring, extraction and prediction logic, and the knowledge base pipeline.

Primary files reviewed:
- `src/workflow.py`
- `src/state.py`
- `src/config.py`
- `src/agents/*`
- `src/biomarker_validator.py`
- `src/pdf_processor.py`
- `api/app/main.py`
- `api/app/routes/analyze.py`
- `api/app/services/extraction.py`
- `api/app/services/ragbot.py`
- `scripts/chat.py`

## Architectural Understanding (Condensed)

### End-to-End Flow
1. Input arrives via CLI (`scripts/chat.py`) or REST API (`api/app/routes/analyze.py`).
2. Natural language inputs are parsed by the extraction service (`api/app/services/extraction.py`) to produce normalized biomarkers and patient context.
3. A rule-based prediction (`predict_disease_simple`) produces a disease hypothesis and probabilities.
4. The LangGraph workflow (`src/workflow.py`) orchestrates six agents: Biomarker Analyzer, Disease Explainer, Biomarker Linker, Clinical Guidelines, Confidence Assessor, Response Synthesizer.
5. The synthesized output is formatted into API schemas (`api/app/services/ragbot.py`) or into CLI-friendly responses (`scripts/chat.py`).

### Key Data Structures
- `GuildState` in `src/state.py` is the shared workflow state; it depends on additive accumulation for parallel outputs.
- `PatientInput` holds structured biomarkers, prediction data, and patient context.
- The response format is built in `ResponseSynthesizerAgent` and then translated into API schemas in `RagBotService`.

### Knowledge Base
- PDFs are chunked and embedded into FAISS (`src/pdf_processor.py`).
- Three retrievers (disease explainer, biomarker linker, clinical guidelines) share the same FAISS index with varying `k` values.

## Deep Review Findings

### Critical Issues

1. **[OPEN] State propagation is incomplete across the workflow.**
   - `src/agents/biomarker_analyzer.py` returns only `agent_outputs` and not the computed `biomarker_flags` or `safety_alerts` into the top-level `GuildState` keys that the workflow expects to accumulate.
   - `src/workflow.py` initializes `biomarker_flags` and `safety_alerts` in the state, but none of the agents return updates to those keys. As a result, `workflow_result.get("biomarker_flags")` and `workflow_result.get("safety_alerts")` are likely empty when the API response is formatted in `api/app/services/ragbot.py`.
   - Effect: API output will frequently miss biomarkers and alerts, and downstream consumers will incorrectly assume a clean result set.
   - Recommendation: return `biomarker_flags` and `safety_alerts` from the Biomarker Analyzer agent so they accumulate in the state. Ensure the response synth uses those same keys.

2. **[OPEN] LangGraph merge behavior is unsafe for parallel outputs.**
   - `GuildState` uses `Annotated[List[AgentOutput], operator.add]` for additive merging, but the nodes return only `{ 'agent_outputs': [output] }` and nothing else. This is okay for `agent_outputs`, but parallel agents also read from the full `agent_outputs` list inside the state to infer prior results.
   - In parallel branches, a given agent might read a partial `agent_outputs` list depending on execution order. This is visible in the `BiomarkerDiseaseLinkerAgent` and `ClinicalGuidelinesAgent` which read the prior Biomarker Analyzer output by searching `agent_outputs`.
   - Effect: nondeterministic behavior if LangGraph schedules a branch before the Biomarker Analyzer output is merged, or if merges occur after the branch starts. This can degrade evidence selection and recommendations.
   - Recommendation: explicitly pass relevant artifacts as dedicated state fields updated by the Biomarker Analyzer, and read those fields directly instead of scanning `agent_outputs`.

3. **[RESOLVED] Schema mismatch between workflow output and API formatter.**
   - `ResponseSynthesizerAgent` returns a structured response with keys like `patient_summary`, `prediction_explanation`, `clinical_recommendations`, `confidence_assessment`, and `safety_alerts`.
   - `RagBotService._format_response()` now correctly reads from `final_response` and handles both Pydantic objects and dicts.
   - The CLI (`scripts/chat.py`) uses `_coerce_to_dict()` and `format_conversational()` to safely handle all output types.
   - **Fix applied**: `_format_response()` updated + `_coerce_to_dict()` helper added.

### High Priority Issues

1. **[OPEN] Prediction confidence is forced to 0.5 and default disease is always Diabetes.**
   - Both the API and CLI `predict_disease_simple` functions enforce a minimum confidence of 0.5 and default to Diabetes when confidence is low.
   - Effect: leads to biased predictions and false confidence. This is risky in a medical domain and undermines reliability assessments.
   - Recommendation: return a low-confidence prediction explicitly and mark reliability as low; avoid forcing a disease when evidence is insufficient.

2. **[RESOLVED] Different biomarker naming schemes across extraction modules.**
   - Both CLI and API now use the shared `src/biomarker_normalization.py` module with 80+ aliases mapped to 24 canonical names.
   - **Fix applied**: unified normalization in both `scripts/chat.py` and `api/app/services/extraction.py`.

3. **[RESOLVED] Use of console glyphs and non-ASCII prefixes in logs and output.**
   - Debug prints removed from CLI. Logging suppressed for noisy HuggingFace/transformers output.
   - API responses use clean JSON only; CLI uses UTF-8 emojis only in user-facing output.
   - **Fix applied**: `[DEBUG]` prints removed, `BertModel LOAD REPORT` suppressed, HuggingFace deprecation warnings filtered.

### Medium Priority Issues

1. **[RESOLVED] Inconsistent model selection between agents.**
   - All agents now use `llm_config` centralized configuration (planner, analyzer, explainer, synthesizer properties).
   - **Fix applied**: `src/llm_config.py` provides `LLMConfig` singleton with per-role properties.

2. **[RESOLVED] Potential JSON parsing fragility in extraction.**
   - `_parse_llm_json()` now handles markdown fences, trailing text, and partial JSON recovery.
   - **Fix applied**: robust JSON parser in `api/app/services/extraction.py` with test coverage (`test_json_parsing.py`).

3. **[RESOLVED] Knowledge base retrieval does not enforce citations.**
   - Disease Explainer agent now checks `sop.require_pdf_citations` and returns "insufficient evidence" when no documents are retrieved.
   - **Fix applied**: citation guardrail in `src/agents/disease_explainer.py` with test (`test_citation_guardrails.py`).

### Low Priority Issues

1. **[OPEN] Error handling does not preserve original exceptions cleanly in API layer.**
   - Exceptions are wrapped in `RuntimeError` without detail separation; `RagBotService.analyze()` does not attach contextual hints (e.g., which agent failed).
   - Recommendation: wrap exceptions with agent name and error classification to improve observability.

2. **[RESOLVED] Hard-coded expected biomarker count (24) in Confidence Assessor.**
   - Now uses `BiomarkerValidator().expected_biomarker_count()` which reads from `config/biomarker_references.json`.
   - Test: `test_validator_count.py` verifies count matches reference config.

## Suggested Improvements (Summary)

1. ~~Align workflow output and API schema.~~ **[RESOLVED]**
2. Promote biomarker flags and safety alerts to first-class state fields in the workflow. **[OPEN]**
3. ~~Use a shared normalization utility.~~ **[RESOLVED]**
4. Remove forced minimum confidence and default disease; permit "low confidence" results. **[OPEN]**
5. ~~Introduce citation enforcement as a guardrail for RAG outputs.~~ **[RESOLVED]**
6. ~~Centralize model selection and logging format.~~ **[RESOLVED]**

## Verification Gaps

The following should be tested once fixes are made:
- Natural language extraction with partial and noisy inputs.
- Workflow run where no abnormal biomarkers are detected.
- API response schema validation for both natural and structured routes.
- Parallel agent execution determinism (state access to biomarker analysis).
- CLI behavior for biomarker names that differ from API normalization.
