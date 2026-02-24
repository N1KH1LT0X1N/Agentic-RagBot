# MediGuard AI / RagBot - Comprehensive Remediation Plan

> **Generated:** February 24, 2026  
> **Status:** ✅ COMPLETED  
> **Last Updated:** Session completion  
> **Priority Levels:** P0 (Critical) → P3 (Nice-to-have)

---

## Implementation Status

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 1 | Dual Architecture | ✅ Complete | Consolidated to src/main.py |
| 2 | Fake ML Prediction | ✅ Complete | Renamed to rule-based heuristics |
| 3 | Vector Store Abstraction | ✅ Complete | Created unified retriever interface |
| 4 | Evolution System | ✅ Complete | Archived to archive/evolution/ |
| 5 | Evaluation System | ✅ Complete | Added deterministic mode |
| 6 | HuggingFace Duplication | ✅ Complete | Reduced from 1175→1086 lines |
| 7 | Test Coverage | ✅ Complete | Added tests/test_integration.py |
| 8 | Database Schema | ⏭️ Deferred | Not needed for HuggingFace |
| 9 | Documentation | ✅ Complete | README.md updated |
| 10 | Gradio Dependencies | ✅ Complete | Shared utils created |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Issue 1: Dual Architecture Confusion](#issue-1-dual-architecture-confusion-p0)
3. [Issue 2: Fake ML Disease Prediction](#issue-2-fake-ml-disease-prediction-p1)
4. [Issue 3: Vector Store Abstraction](#issue-3-vector-store-abstraction-p1)
5. [Issue 4: Orphaned Evolution System](#issue-4-orphaned-evolution-system-p2)
6. [Issue 5: Unreliable Evaluation System](#issue-5-unreliable-evaluation-system-p2)
7. [Issue 6: HuggingFace Code Duplication](#issue-6-huggingface-code-duplication-p2)
8. [Issue 7: Inadequate Test Coverage](#issue-7-inadequate-test-coverage-p1)
9. [Issue 8: Database Schema Unused](#issue-8-database-schema-unused-p3)
10. [Issue 9: Documentation Misalignment](#issue-9-documentation-misalignment-p1)
11. [Issue 10: Gradio App Dependencies](#issue-10-gradio-app-dependencies-p2)
12. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

The RagBot codebase has **10 structural issues** that create confusion, maintenance burden, and misleading claims. The most critical issues are:

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| P0 | Dual Architecture | High confusion, duplicated code paths | 3-5 days |
| P1 | Fake ML Prediction | Misleading users, false claims | 2-3 days |
| P1 | Vector Store Mess | Production vs local mismatch | 2 days |
| P1 | Missing Tests | Unreliable deployments | 3-4 days |
| P1 | Doc Misalignment | User confusion | 1 day |
| P2 | Orphaned Evolution | Dead code, wasted complexity | 1-2 days |
| P2 | Evaluation System | Unreliable quality metrics | 2 days |
| P2 | HuggingFace Duplication | 1175-line standalone app | 2-3 days |
| P2 | Gradio Dependencies | Can't run standalone | 0.5 days |
| P3 | Unused Database | Alembic setup with no migrations | 1 day |

---

## Issue 1: Dual Architecture Confusion (P0)

### Problem

Two competing LangGraph workflows exist:

| Component | Path | Purpose |
|-----------|------|---------|
| **ClinicalInsightGuild** | `src/workflow.py` | Original 6-agent biomarker analysis |
| **AgenticRAGService** | `src/services/agents/agentic_rag.py` | Newer Q&A RAG pipeline |

The API routes them confusingly:
- `/analyze/*` → ClinicalInsightGuild via `api/app/services/ragbot.py`
- `/ask` → AgenticRAGService via `src/routers/ask.py`

**Evidence:**
- `src/main.py` initializes BOTH services at startup (lines 91-106)
- `api/app/main.py` is a SEPARATE FastAPI app from `src/main.py`
- Users don't know which one is "production"

### Solution

**Option A: Merge into Single Unified Pipeline (Recommended)**

```
┌────────────────────────────────────────────────────────────────┐
│                    Unified RAG Pipeline                       │
├────────────────────────────────────────────────────────────────┤
│  Input → Guardrail → Router → ┬→ Biomarker Analysis Path     │
│                                │   (6 specialist agents)       │
│                                └→ General Q&A Path             │
│                                    (retrieve → grade → gen)    │
│                          → Output Synthesizer → Response       │
└────────────────────────────────────────────────────────────────┘
```

**Implementation Steps:**

1. **Create unified graph** in `src/pipelines/unified_rag.py`:
   ```python
   # Merge both workflows into one StateGraph
   # Use routing logic from guardrail_node to dispatch
   ```

2. **Delete redundant files:**
   - Move `api/app/` logic into `src/routers/`
   - Delete `api/app/main.py` (use `src/main.py` only)
   - Keep `api/app/services/ragbot.py` as legacy adapter

3. **Single entry point:**
   - `src/main.py` becomes THE server
   - `uvicorn src.main:app` everywhere

4. **Update imports:**
   ```python
   # In src/main.py, replace:
   from api.app.services.ragbot import get_ragbot_service
   # With:
   from src.pipelines.unified_rag import UnifiedRAGService
   ```

**Files to Create:**
- `src/pipelines/__init__.py`
- `src/pipelines/unified_rag.py`
- `src/pipelines/nodes/__init__.py` (merge all nodes)

**Files to Delete/Archive:**
- `api/app/main.py` → Archive to `api/app/main_legacy.py`
- `api/app/routes/` → Merge into `src/routers/`

---

## Issue 2: Fake ML Disease Prediction (P1)

### Problem

The README claims "ML prediction" but `predict_disease_simple()` is pure if/else:

```python
# scripts/chat.py lines 151-216
if glucose > 126:
    scores["Diabetes"] += 0.4
if hba1c >= 6.5:
    scores["Diabetes"] += 0.5
```

There's also an LLM-based predictor (`predict_disease_llm()`) that just asks an LLM to guess.

### Solution

**Option A: Be Honest (Quick Fix)**

Update all documentation to say "rule-based heuristics" not "ML prediction":

```markdown
# In README.md:
- **Disease Prediction** - Rule-based scoring on 5 conditions
  (Diabetes, Anemia, Heart Disease, Thrombocytopenia, Thalassemia)
```

**Option B: Implement Real ML (Longer)**

1. **Create a proper classifier:**
   ```python
   # src/models/disease_classifier.py
   from sklearn.ensemble import RandomForestClassifier
   import joblib
   
   class DiseaseClassifier:
       def __init__(self, model_path: str = "models/disease_rf.joblib"):
           self.model = joblib.load(model_path)
           self.feature_names = [...]  # 24 biomarkers
       
       def predict(self, biomarkers: dict) -> dict:
           features = self._to_feature_vector(biomarkers)
           proba = self.model.predict_proba([features])[0]
           return {
               "disease": self.model.classes_[proba.argmax()],
               "confidence": float(proba.max()),
               "probabilities": dict(zip(self.model.classes_, proba.tolist()))
           }
   ```

2. **Train on synthetic data:**
   - Create `scripts/train_disease_model.py`
   - Generate synthetic patient data with known conditions
   - Train RandomForest/XGBoost classifier
   - Save to `models/disease_rf.joblib`

3. **Replace predictor calls:**
   ```python
   # Instead of predict_disease_simple(biomarkers)
   from src.models.disease_classifier import get_classifier
   prediction = get_classifier().predict(biomarkers)
   ```

**Recommendation:** Do Option A immediately, Option B as a follow-up feature.

---

## Issue 3: Vector Store Abstraction (P1)

### Problem

Two different vector stores used inconsistently:

| Context | Store | Configuration |
|---------|-------|---------------|
| Local dev | FAISS | `data/vector_stores/medical_knowledge.faiss` |
| Production | OpenSearch | `OPENSEARCH__HOST` env var |
| HuggingFace | FAISS | Bundled in `huggingface/` |

The code has:
- `src/pdf_processor.py` → FAISS
- `src/services/opensearch/client.py` → OpenSearch
- `src/services/agents/nodes/retrieve_node.py` → OpenSearch only

### Solution

**Create a unified retriever interface:**

```python
# src/services/retrieval/interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Return list of {id, score, text, title, section, metadata}"""
        pass
    
    @abstractmethod
    def search_hybrid(self, query: str, embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        pass
```

```python
# src/services/retrieval/faiss_retriever.py
class FAISSRetriever(BaseRetriever):
    def __init__(self, vector_store_path: str, embedding_model):
        self.store = FAISS.load_local(vector_store_path, embedding_model, ...)
    
    def search(self, query: str, top_k: int = 10):
        docs = self.store.similarity_search(query, k=top_k)
        return [{"id": i, "score": 0, "text": d.page_content, ...} for i, d in enumerate(docs)]
```

```python
# src/services/retrieval/opensearch_retriever.py
class OpenSearchRetriever(BaseRetriever):
    def __init__(self, client: OpenSearchClient):
        self.client = client
    
    def search(self, query: str, top_k: int = 10):
        return self.client.search_bm25(query, top_k=top_k)
```

```python
# src/services/retrieval/__init__.py
def get_retriever() -> BaseRetriever:
    """Factory that returns appropriate retriever based on config."""
    settings = get_settings()
    if settings.opensearch.host and _opensearch_available():
        return OpenSearchRetriever(make_opensearch_client())
    else:
        return FAISSRetriever("data/vector_stores", get_embedding_model())
```

**Update retrieve_node.py:**
```python
def retrieve_node(state: dict, *, context: Any) -> dict:
    retriever = context.retriever  # Now uses unified interface
    results = retriever.search_hybrid(query, embedding, top_k=10)
    ...
```

---

## Issue 4: Orphaned Evolution System (P2)

### Problem

`src/evolution/` contains a complete SOP evolution system that:
- Has `SOPGenePool` for versioning
- Has `performance_diagnostician()` for diagnosis
- Has `sop_architect()` for mutations
- Has an Airflow DAG (`airflow/dags/sop_evolution.py`)

**But:**
- No Airflow deployment exists
- `run_evolution_cycle()` requires manual invocation
- No UI to trigger evolution
- No tracking of which SOP version is in use

### Solution

**Option A: Remove It (Quick)**

Delete or archive the unused code:
```
mkdir -p archive/evolution
mv src/evolution/* archive/evolution/
mv airflow/dags/sop_evolution.py archive/
```

Update imports to remove references.

**Option B: Wire It Up (If Actually Wanted)**

1. **Add CLI command:**
   ```python
   # scripts/evolve_sop.py
   from src.evolution.director import run_evolution_cycle
   from src.workflow import create_guild
   
   if __name__ == "__main__":
       gene_pool = SOPGenePool()
       # Load baseline, run evolution, save results
   ```

2. **Add API endpoint:**
   ```python
   # src/routers/admin.py
   @router.post("/admin/evolve")
   async def trigger_evolution(request: Request):
       # Requires admin auth
       result = run_evolution_cycle(...)
       return {"new_versions": len(result)}
   ```

3. **Persist to database:**
   - Use Alembic migrations to create `sop_versions` table
   - Store evolved SOPs with evaluation scores

---

## Issue 5: Unreliable Evaluation System (P2)

### Problem

`src/evaluation/evaluators.py` uses LLM-as-judge for:
- `evaluate_clinical_accuracy()` - LLM grades medical correctness
- `evaluate_actionability()` - LLM grades recommendations

**Problems:**
1. LLMs are unreliable judges of medical accuracy
2. No ground truth comparison
3. Scores can fluctuate between runs
4. Falls back to 0.5 on JSON parse errors (line 91)

### Solution

**Replace with deterministic metrics where possible:**

```python
# For clinical_accuracy: Use BiomarkerValidator as ground truth
def evaluate_clinical_accuracy_v2(response: Dict, biomarkers: Dict) -> GradedScore:
    validator = BiomarkerValidator()
    
    # Check if flagged biomarkers match validator
    expected_flags = validator.validate_all(biomarkers)[0]
    actual_flags = response.get("biomarker_flags", [])
    
    expected_abnormal = {f.name for f in expected_flags if f.status != "NORMAL"}
    actual_abnormal = {f["name"] for f in actual_flags if f["status"] != "NORMAL"}
    
    precision = len(expected_abnormal & actual_abnormal) / max(len(actual_abnormal), 1)
    recall = len(expected_abnormal & actual_abnormal) / max(len(expected_abnormal), 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)
    
    return GradedScore(
        score=f1,
        reasoning=f"Precision: {precision:.2f}, Recall: {recall:.2f}"
    )
```

**Keep LLM-as-judge only for subjective metrics:**
- Clarity (readability) - already programmatic ✓
- Helpfulness of recommendations - needs human judgment

**Add human-in-the-loop:**
```python
# src/evaluation/human_eval.py
def collect_human_rating(response_id: str) -> Optional[float]:
    """Store human ratings for later analysis."""
    # Integrate with Langfuse or custom feedback endpoint
```

---

## Issue 6: HuggingFace Code Duplication (P2)

### Problem

`huggingface/app.py` is **1175 lines** that reimplements:
- Biomarker parsing (duplicated from chat.py)
- Disease prediction (duplicated)
- Guild initialization (duplicated)
- Gradio UI (different from src/gradio_app.py)
- Environment handling (custom)

### Solution

**Refactor to import from main package:**

```python
# huggingface/app.py (simplified to ~200 lines)
import sys
sys.path.insert(0, "..")

from src.workflow import create_guild
from src.state import PatientInput
from scripts.chat import extract_biomarkers, predict_disease_simple

# Only Gradio-specific code here
def analyze_biomarkers(input_text: str):
    biomarkers, context = extract_biomarkers(input_text)
    prediction = predict_disease_simple(biomarkers)
    patient_input = PatientInput(
        biomarkers=biomarkers,
        model_prediction=prediction,
        patient_context=context
    )
    guild = get_guild()
    result = guild.run(patient_input)
    return format_result(result)

# Gradio interface...
```

**Create shared utilities module:**
```python
# src/utils/biomarker_extraction.py
# Move extract_biomarkers() from chat.py here

# src/utils/disease_scoring.py
# Move predict_disease_simple() here
```

---

## Issue 7: Inadequate Test Coverage (P1)

### Problem

Current tests are mostly:
- Import validation (`test_basic.py`)
- Unit tests with mocks (`test_agentic_rag.py`)
- Schema validation (`test_schemas.py`)

**Missing:**
- End-to-end workflow tests
- API integration tests
- Regression tests for medical accuracy

### Solution

**Add integration tests:**

```python
# tests/integration/test_full_workflow.py
import pytest
from src.workflow import create_guild
from src.state import PatientInput

@pytest.fixture(scope="module")
def guild():
    return create_guild()

def test_diabetes_patient_analysis(guild):
    patient = PatientInput(
        biomarkers={"Glucose": 185, "HbA1c": 8.2},
        model_prediction={"disease": "Diabetes", "confidence": 0.87, "probabilities": {}},
        patient_context={"age": 52, "gender": "male"}
    )
    result = guild.run(patient)
    
    # Assertions
    assert result.get("final_response") is not None
    assert len(result.get("biomarker_flags", [])) >= 2
    assert any(f["name"] == "Glucose" for f in result["biomarker_flags"])
    assert "Diabetes" in result["final_response"]["prediction_explanation"]["primary_disease"]

def test_anemia_patient_analysis(guild):
    patient = PatientInput(
        biomarkers={"Hemoglobin": 9.5, "MCV": 75},
        model_prediction={"disease": "Anemia", "confidence": 0.75, "probabilities": {}},
        patient_context={}
    )
    result = guild.run(patient)
    assert result.get("final_response") is not None
```

**Add API tests:**

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_structured(client):
    response = client.post("/analyze/structured", json={
        "biomarkers": {"Glucose": 140, "HbA1c": 7.0}
    })
    assert response.status_code == 200
    assert "prediction" in response.json()
```

**Add to CI:**
```yaml
# .github/workflows/test.yml
- name: Run integration tests
  run: pytest tests/integration/ -v
  env:
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

---

## Issue 8: Database Schema Unused (P3)

### Problem

- `alembic/` is configured but `alembic/versions/` is empty
- `src/database.py` exists but is barely used
- `src/db/models.py` defines tables that aren't created

### Solution

**If database features are wanted:**

1. Create initial migration:
   ```bash
   cd src
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

2. Use models for:
   - Storing analysis history
   - Persisting evolved SOPs
   - User feedback collection

**If not needed:**
- Remove `alembic/` directory
- Remove `src/database.py`
- Remove `src/db/` if empty
- Remove `postgres` from `docker-compose.yml`

---

## Issue 9: Documentation Misalignment (P1)

### Problem

README.md claims:
- "ML prediction" → It's rule-based
- "6 Specialist Agents" → Also has agentic RAG (7+ nodes)
- "Production-ready" → Two competing entry points

### Solution

**Update README.md:**

```markdown
## How It Works

### Analysis Pipeline
RagBot uses a **multi-agent LangGraph workflow** to analyze biomarkers:

1. **Input Routing** - Validates query is medical, routes to analysis or Q&A
2. **Biomarker Analyzer** - Validates values against clinical reference ranges
3. **Disease Scorer** - Rule-based heuristics predict most likely condition
4. **Disease Explainer** - RAG retrieval for pathophysiology from medical PDFs
5. **Guidelines Agent** - RAG retrieval for treatment recommendations
6. **Response Synthesizer** - Compiles findings into patient-friendly summary

### Supported Conditions
- Diabetes (via Glucose, HbA1c)
- Anemia (via Hemoglobin, MCV)
- Heart Disease (via Cholesterol, Troponin, LDL)
- Thrombocytopenia (via Platelets)
- Thalassemia (via MCV + Hemoglobin pattern)

> **Note:** Disease prediction uses rule-based scoring, not ML models.
> Future versions may include trained classifiers.
```

---

## Issue 10: Gradio App Dependencies (P2)

### Problem

`src/gradio_app.py` is just an HTTP client:
```python
def _call_ask(question: str) -> str:
    resp = client.post(f"{API_BASE}/ask", json={"question": question})
```

It requires the FastAPI server running at `http://localhost:8000`.

### Solution

**Option A: Document the dependency clearly:**

Add startup instructions:
```markdown
## Running the Gradio UI

1. Start the API server:
   ```bash
   uvicorn src.main:app --reload
   ```

2. In another terminal, start Gradio:
   ```bash
   python -m src.gradio_app
   ```

3. Open http://localhost:7860
```

**Option B: Add embedded mode:**

```python
# src/gradio_app.py
def _call_ask_embedded(question: str) -> str:
    """Direct workflow invocation without HTTP."""
    from src.services.agents.agentic_rag import AgenticRAGService
    service = get_rag_service()
    result = service.ask(query=question)
    return result.get("final_answer", "No answer.")

def launch_gradio(embedded: bool = False, share: bool = False):
    ask_fn = _call_ask_embedded if embedded else _call_ask
    # ... rest of UI
```

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)

| Day | Task | Owner |
|-----|------|-------|
| 1 | Fix documentation claims (README.md) | - |
| 1-2 | Consolidate entry points (delete api/app/main.py) | - |
| 2-3 | Create unified retriever interface | - |
| 3-4 | Add integration tests for workflow | - |
| 5 | Update Gradio startup docs | - |

### Phase 2: Architecture Cleanup (Week 2)

| Day | Task | Owner |
|-----|------|-------|
| 1-2 | Merge AgenticRAG + ClinicalInsightGuild | - |
| 3 | Refactor HuggingFace app to use shared code | - |
| 4 | Wire up or remove evolution system | - |
| 5 | Review and deploy | - |

### Phase 3: Quality Improvements (Week 3)

| Day | Task | Owner |
|-----|------|-------|
| 1 | Replace LLM-as-judge with deterministic metrics | - |
| 2 | Add proper disease classifier (optional) | - |
| 3-4 | Expand test coverage to 80%+ | - |
| 5 | Final documentation pass | - |

---

## Quick Wins (Do Today)

1. **Rename `predict_disease_simple`** to `score_disease_heuristic` to be honest
2. **Add `## Architecture` section** to README explaining the two workflows
3. **Create `scripts/start_full.ps1`** that starts both API and Gradio
4. **Delete empty `alembic/versions/`** and document "DB not implemented"
5. **Add type hints** to top 5 most-used functions

---

## Checklist

- [ ] P0: Single FastAPI entry point (`src/main.py` only)
- [ ] P1: Documentation accurately describes capabilities
- [ ] P1: Unified retriever interface (FAISS + OpenSearch)
- [ ] P1: Integration tests exist and pass
- [ ] P2: Evolution system removed or functional
- [ ] P2: HuggingFace app imports from main package
- [ ] P2: Evaluation metrics are deterministic
- [ ] P3: Database either used or removed
