# Groq + Gemini Provider Swap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all Ollama usage with Groq for chat/completions and Gemini for hosted embeddings, and verify the system still runs end-to-end.

**Architecture:** Centralize chat model configuration through `src/llm_config.py` using Groq-backed LangChain chat models, and replace any direct `ChatOllama` usage in CLI/API/evaluation with the Groq model. Switch embeddings to Gemini via `GoogleGenerativeAIEmbeddings` in `src/pdf_processor.py`, and update health checks and env configuration. Update dependencies and run existing tests/scripts to validate.

**Tech Stack:** Python 3.11, LangChain, LangGraph, Groq (`langchain-groq`), Gemini embeddings (`langchain-google-genai`), FastAPI.

---

### Task 1: Add Groq/Gemini dependencies and env config

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.template`

**Step 1: Update dependencies**

Add required packages:
- `langchain-groq`
- `langchain-google-genai`

**Step 2: Update environment template**

Add:
- `GROQ_API_KEY="your_groq_api_key_here"`
- `GROQ_MODEL_FAST="llama-3.1-8b-instant"`
- `GROQ_MODEL_QUALITY="llama-3.1-70b-versatile"`
- `GEMINI_EMBEDDINGS_MODEL="models/embedding-001"`

**Step 3: Run dependency install**

Run: `pip install -r requirements.txt`
Expected: Packages install successfully.

**Step 4: Commit**

```bash
git add requirements.txt .env.template
git commit -m "chore: add groq and gemini dependencies"
```

### Task 2: Replace central LLM configuration with Groq

**Files:**
- Modify: `src/llm_config.py`

**Step 1: Write minimal failing import check**

Add a quick assertion in `tests/test_basic.py` to import Groq chat class to verify dependency wiring.

**Step 2: Run test to verify it fails (before implementation)**

Run: `python tests/test_basic.py`
Expected: Import error for Groq package.

**Step 3: Replace ChatOllama usage**

Change:
- Use `ChatGroq` for planner, analyzer, explainer, synthesizers, director.
- Use `GROQ_API_KEY` from env.
- Use model mapping:
  - Planner/Analyzer/Extraction: `GROQ_MODEL_FAST`
  - Explainer/Synthesizer/Director: `GROQ_MODEL_QUALITY`
- Update `print_config()` to reflect Groq + model names.
- Replace `check_ollama_connection()` with `check_groq_connection()` that invokes a quick test prompt.

**Step 4: Update tests to pass**

Update `tests/test_basic.py` to expect the Groq import.

**Step 5: Run test**

Run: `python tests/test_basic.py`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/llm_config.py tests/test_basic.py
git commit -m "feat: switch core llm config to groq"
```

### Task 3: Swap Ollama usage in CLI and API extraction

**Files:**
- Modify: `scripts/chat.py`
- Modify: `api/app/services/extraction.py`

**Step 1: Replace extraction LLM in CLI**

Swap `ChatOllama` with `ChatGroq` and use fast model (`GROQ_MODEL_FAST`).

**Step 2: Replace prediction LLM in CLI**

Swap to `ChatGroq` with fast model.

**Step 3: Replace API extraction LLM**

Swap to `ChatGroq` with fast model.

**Step 4: Run CLI smoke test**

Run: `python scripts/chat.py`
Expected: It initializes without Ollama dependency (you can exit immediately).

**Step 5: Commit**

```bash
git add scripts/chat.py api/app/services/extraction.py
git commit -m "feat: use groq for cli and api extraction"
```

### Task 4: Swap Ollama usage in evaluation and evolution components

**Files:**
- Modify: `src/evaluation/evaluators.py`
- Modify: `src/evolution/director.py`

**Step 1: Replace `ChatOllama` with `ChatGroq`**

Use:
- Fast model for evaluators (clinical accuracy, actionability).
- Quality model if needed for director (if any LLM usage is added in future, wire now for consistency).

**Step 2: Run quick evolution test**

Run: `python tests/test_evolution_quick.py`
Expected: PASS.

**Step 3: Commit**

```bash
git add src/evaluation/evaluators.py src/evolution/director.py
git commit -m "feat: use groq in evaluation and evolution"
```

### Task 5: Switch embeddings to Gemini hosted API

**Files:**
- Modify: `src/pdf_processor.py`

**Step 1: Update `get_all_retrievers()`**

Change default to use `get_embedding_model(provider="google")` (Gemini) instead of local HuggingFace.

**Step 2: Ensure Gemini model is configurable**

Use `GEMINI_EMBEDDINGS_MODEL` env var; default to `models/embedding-001`.

**Step 3: Run retriever initialization**

Run: `python -c "from src.pdf_processor import get_all_retrievers; get_all_retrievers()"`
Expected: Gemini embeddings initialized or helpful error if `GOOGLE_API_KEY` missing.

**Step 4: Commit**

```bash
git add src/pdf_processor.py
git commit -m "feat: use gemini embeddings by default"
```

### Task 6: Update health check for Groq

**Files:**
- Modify: `api/app/routes/health.py`

**Step 1: Replace Ollama health check**

Use `ChatGroq` test call; report `groq_status` and `available_models` from env.

**Step 2: Run API health check**

Run: `python -m uvicorn api.app.main:app --host 0.0.0.0 --port 8000`
Then: `Invoke-RestMethod http://localhost:8000/api/v1/health`
Expected: `groq_status` is `connected` (with valid API key).

**Step 3: Commit**

```bash
git add api/app/routes/health.py
git commit -m "feat: update health check for groq"
```

### Task 7: Full regression checks

**Files:**
- Modify: None

**Step 1: Run basic import test**

Run: `python tests/test_basic.py`
Expected: PASS.

**Step 2: Run evaluation quick test**

Run: `python tests/test_evolution_quick.py`
Expected: PASS.

**Step 3: Run API example**

Run:
- `python -m uvicorn api.app.main:app --host 0.0.0.0 --port 8000`
- `Invoke-RestMethod http://localhost:8000/api/v1/example`
Expected: JSON response with `status: success`.

---

Plan complete and saved to `docs/plans/2026-02-06-groq-gemini-swap.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
