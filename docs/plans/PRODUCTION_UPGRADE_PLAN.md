# MediGuard AI — Production Upgrade Plan

## From Prototype to Production-Grade MedTech RAG System

> **Generated**: 2026-02-23  
> **Based on**: Deep review of production-agentic-rag-course (Weeks 1–7) + existing RagBot codebase  
> **Goal**: Take the existing MediGuard AI (clinical biomarker analysis + RAG explanation system) to full production quality, applying every lesson from the arXiv Paper Curator course — adapted for the MedTech domain.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Deep Review: Course vs. Your Codebase](#2-deep-review-course-vs-your-codebase)
3. [Architecture Gap Analysis](#3-architecture-gap-analysis)
4. [Phase 1: Infrastructure Foundation](#phase-1-infrastructure-foundation-week-1-equivalent)
5. [Phase 2: Medical Data Ingestion Pipeline](#phase-2-medical-data-ingestion-pipeline-week-2-equivalent)
6. [Phase 3: Production Search Foundation](#phase-3-production-search-foundation-week-3-equivalent)
7. [Phase 4: Hybrid Search & Intelligent Chunking](#phase-4-hybrid-search--intelligent-chunking-week-4-equivalent)
8. [Phase 5: Complete RAG Pipeline with Streaming](#phase-5-complete-rag-pipeline-with-streaming-week-5-equivalent)
9. [Phase 6: Monitoring, Caching & Observability](#phase-6-monitoring-caching--observability-week-6-equivalent)
10. [Phase 7: Agentic RAG & Messaging Bot](#phase-7-agentic-rag--messaging-bot-week-7-equivalent)
11. [Phase 8: MedTech-Specific Additions](#phase-8-medtech-specific-additions-beyond-course)
12. [Implementation Priority Matrix](#implementation-priority-matrix)
13. [Migration Strategy](#migration-strategy)

---

## 1. Executive Summary

Your RagBot is a **working prototype** with strong domain logic (biomarker validation, multi-agent clinical analysis, 5D evaluation, SOP evolution). The course teaches **production infrastructure** (Docker orchestration, OpenSearch hybrid search, Airflow pipelines, Redis caching, Langfuse observability, LangGraph agentic workflows, Telegram bot).

**The strategy**: Keep your excellent medical domain logic and multi-agent architecture, but rebuild the infrastructure layer to match production standards. Your domain is *harder* than arXiv papers — medical data demands stricter validation, HIPAA-aware patterns, and safety guardrails.

### What You Have (Strengths)
- ✅ 6 specialized medical agents (Biomarker Analyzer, Disease Explainer, Biomarker-Disease Linker, Clinical Guidelines, Confidence Assessor, Response Synthesizer)
- ✅ LangGraph orchestration with parallel execution
- ✅ Robust biomarker validation with 24 biomarkers, reference ranges, critical values
- ✅ 5D evaluation framework (Clinical Accuracy, Evidence Grounding, Actionability, Clarity, Safety)
- ✅ SOP evolution engine (Outer Loop optimization)
- ✅ Multi-provider LLM support (Groq, Gemini, Ollama)
- ✅ Basic FastAPI with analysis endpoints
- ✅ CLI chatbot with natural language biomarker extraction

### What You're Missing (Gaps)
- ❌ No Docker Compose orchestration (only minimal single-service Dockerfile)
- ❌ No production database (PostgreSQL) — no patient/report persistence
- ❌ No production search engine — using FAISS (in-memory, single-file, no filtering)
- ❌ No chunking strategy — basic RecursiveCharacterTextSplitter only
- ❌ No hybrid search (BM25 + vector) — vector-only retrieval
- ❌ No production embeddings — using local HuggingFace MiniLM (384d) or Google free tier
- ❌ No data ingestion pipeline (Airflow) — manual PDF loading
- ❌ No caching layer (Redis) — every query hits LLM
- ❌ No observability (Langfuse) — no tracing, no cost tracking
- ❌ No streaming responses — synchronous only
- ❌ No Gradio interface — CLI only (besides basic API)
- ❌ No messaging bot (Telegram/WhatsApp) — no mobile access
- ❌ No agentic RAG with guardrails, document grading, query rewriting
- ❌ No proper dependency injection pattern (FastAPI `Depends()`)
- ❌ No Pydantic Settings with env-nested config
- ❌ No factory pattern for service initialization
- ❌ No proper exception hierarchy
- ❌ No health checks for all services
- ❌ No Makefile / dev tooling (ruff, mypy, pre-commit)
- ❌ No proper test infrastructure (pytest fixtures, test containers)

---

## 2. Deep Review: Course vs. Your Codebase

### Course Architecture (What Production Looks Like)

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Compose Orchestration                │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ FastAPI  │PostgreSQL│OpenSearch│  Ollama  │   Airflow       │
│ (8000)   │ (5432)   │ (9200)   │ (11434)  │   (8080)        │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│  Redis   │ Langfuse │ClickHouse│  MinIO   │ Langfuse-PG     │
│ (6379)   │ (3001)   │          │          │ (5433)          │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│            Gradio UI (7861) │ Telegram Bot                    │
└──────────────────────────────────────────────────────────────┘
```

**Key Patterns from Course:**
- **Pydantic Settings** with `env_nested_delimiter="__"` for hierarchical config
- **Factory pattern** (`make_*` functions) for every service
- **Dependency injection** via FastAPI `Depends()` with typed annotations
- **Lifespan context** for startup/shutdown with proper resource management
- **Service layer separation**: `routers/` → `services/` → `clients/`
- **Schema-driven**: Separate Pydantic schemas for API, database, embeddings, indexing
- **Exception hierarchy**: Domain-specific exceptions (`PDFParsingException`, `OllamaException`, etc.)
- **Context dataclass** for LangGraph runtime dependency injection
- **Structured LLM output** via `.with_structured_output(PydanticModel)`

### Your Codebase Architecture (Current State)

```
┌─────────────────────────────────────────────┐
│           Basic FastAPI (api/app/)           │
│     Single Dockerfile, no orchestration      │
├─────────────────────────────────────────────┤
│        src/ (Core Domain Logic)              │
│  ┌─────────────────────────────────────┐    │
│  │ workflow.py (LangGraph StateGraph)   │    │
│  │ 6 agents/ (parallel execution)       │    │
│  │ biomarker_validator.py (24 markers)  │    │
│  │ pdf_processor.py (FAISS + PyPDF)     │    │
│  │ evaluation/ (5D framework)           │    │
│  │ evolution/ (SOP optimization)        │    │
│  └─────────────────────────────────────┘    │
├─────────────────────────────────────────────┤
│   FAISS vector store (single file)           │
│   No PostgreSQL, No Redis, No OpenSearch     │
└─────────────────────────────────────────────┘
```

---

## 3. Architecture Gap Analysis

| Dimension | Course (Production) | Your Codebase (Prototype) | Gap Severity |
|-----------|-------------------|--------------------------|--------------|
| **Container Orchestration** | Docker Compose with 12+ services, health checks, networks | Single Dockerfile, manual startup | 🔴 Critical |
| **Database** | PostgreSQL 16 with SQLAlchemy models, repositories | None (in-memory only) | 🔴 Critical |
| **Search Engine** | OpenSearch 2.19 with BM25 + KNN hybrid, RRF fusion | FAISS (vector-only, no filtering) | 🔴 Critical |
| **Chunking** | Section-aware chunking (600w, 100w overlap, metadata) | Basic RecursiveCharacterTextSplitter (1000 char) | 🟡 Major |
| **Embeddings** | Jina AI v3 (1024d, passage/query differentiation) | HuggingFace MiniLM (384d) or Google free tier | 🟡 Major |
| **Data Pipeline** | Airflow DAGs (daily schedule, fetch→parse→chunk→index) | Manual PDF loading, one-time setup | 🟡 Major |
| **Caching** | Redis with TTL, exact-match, SHA256 keys | None | 🟡 Major |
| **Observability** | Langfuse v3 (traces, spans, generations, cost tracking) | None (print statements only) | 🟡 Major |
| **Streaming** | SSE streaming with Gradio UI | None (synchronous responses) | 🟡 Major |
| **Agentic RAG** | LangGraph with guardrails, grading, rewriting, context_schema | Basic LangGraph (no guardrails, no grading) | 🟡 Major |
| **Bot Integration** | Telegram bot with /search, Q&A, caching | None | 🟢 Enhancement |
| **Config Management** | Pydantic Settings, hierarchical env vars, frozen models | Basic os.getenv, dotenv | 🟡 Major |
| **Dependency Injection** | FastAPI Depends() with typed annotations | Manual global singletons | 🟡 Major |
| **Error Handling** | Domain exception hierarchy, graceful fallbacks | Basic try/except with prints | 🟡 Major |
| **Code Quality** | Ruff, MyPy, pre-commit, pytest with fixtures | Minimal pytest, no linting | 🟢 Enhancement |
| **API Design** | Versioned (/api/v1/), health checks for all services | Basic routes, minimal health check | 🟡 Major |

---

## Phase 1: Infrastructure Foundation (Week 1 Equivalent)

> **Goal**: Containerize everything, add PostgreSQL for persistence, set up OpenSearch, establish professional development environment.

### 1.1 Docker Compose Orchestration

Create a production `docker-compose.yml` with all services:

```yaml
# Target services for MediGuard AI:
services:
  api:           # FastAPI application (port 8000)
  postgres:      # Patient reports, analysis history (port 5432)
  opensearch:    # Medical document search engine (port 9200)
  opensearch-dashboards:  # Search UI (port 5601)
  redis:         # Response caching (port 6379)
  ollama:        # Local LLM for privacy-sensitive medical data (port 11434)
  airflow:       # Medical literature pipeline (port 8080)
  langfuse-web:  # Observability dashboard (port 3001)
  langfuse-worker/postgres/redis/clickhouse/minio:  # Langfuse infra
```

**Tasks:**
- [ ] Create root `docker-compose.yml` adapting course pattern to MedTech services
- [ ] Create multi-stage `Dockerfile` using UV package manager (copy course pattern)
- [ ] Add health checks for every service (PostgreSQL, OpenSearch, Redis, Ollama)
- [ ] Set up Docker network `mediguard-network` with proper service dependencies
- [ ] Configure volume persistence for all data stores
- [ ] Create `.env.example` with all configuration variables documented

### 1.2 Pydantic Settings Configuration

Replace scattered `os.getenv()` calls with hierarchical Pydantic Settings:

```python
# New: src/config.py (course-inspired)
class MedicalPDFSettings(BaseConfigSettings):    # PDF parser config
class ChunkingSettings(BaseConfigSettings):       # Chunking parameters  
class OpenSearchSettings(BaseConfigSettings):     # Search engine config
class LangfuseSettings(BaseConfigSettings):       # Observability config
class RedisSettings(BaseConfigSettings):          # Cache config
class TelegramSettings(BaseConfigSettings):       # Bot config
class BiomarkerSettings(BaseConfigSettings):      # Biomarker thresholds
class Settings(BaseConfigSettings):               # Root settings
```

**Tasks:**
- [ ] Rewrite `src/config.py` — keep `ExplanationSOP` but add infrastructure settings classes
- [ ] Use `env_nested_delimiter="__"` for hierarchical environment variables
- [ ] Add `frozen=True` for immutable configuration
- [ ] Move all hardcoded values to environment variables with sensible defaults
- [ ] Create `get_settings()` factory with `@lru_cache`

### 1.3 PostgreSQL Database Setup

Add persistent storage for analysis history — critical for medical audit trail:

```python
# New models:
class PatientAnalysis(Base):      # Store each analysis run
class AnalysisReport(Base):       # Store final reports
class MedicalDocument(Base):      # Track ingested medical PDFs
class BiomarkerReference(Base):   # Biomarker reference ranges (currently JSON file)
```

**Tasks:**
- [ ] Create `src/db/` package mirroring course pattern (factory, interfaces, postgresql)
- [ ] Define SQLAlchemy models for analysis history and medical documents
- [ ] Create repository pattern for data access
- [ ] Set up Alembic for database migrations
- [ ] Migrate `biomarker_references.json` to database (keep JSON as seed data)

### 1.4 Project Structure Refactor

Reorganize to match production patterns:

```
src/
├── config.py                    # Pydantic Settings (hierarchical)
├── main.py                      # FastAPI app with lifespan
├── database.py                  # Database utilities
├── dependencies.py              # FastAPI dependency injection
├── exceptions.py                # Domain exception hierarchy
├── middlewares.py               # Request logging, timing
├── db/                          # Database layer
│   ├── factory.py
│   └── interfaces/
├── models/                      # SQLAlchemy models
│   ├── analysis.py
│   └── document.py  
├── repositories/                # Data access
│   ├── analysis.py
│   └── document.py
├── routers/                     # API endpoints
│   ├── analyze.py               # Biomarker analysis
│   ├── ask.py                   # RAG Q&A (streaming + standard)
│   ├── health.py                # Comprehensive health checks
│   └── search.py                # Medical document search
├── schemas/                     # Pydantic request/response models
│   ├── api/
│   ├── medical/
│   └── embeddings/
├── services/                    # Business logic
│   ├── agents/                  # Your 6 medical agents (KEEP!)
│   │   ├── biomarker_analyzer.py
│   │   ├── disease_explainer.py
│   │   ├── biomarker_linker.py
│   │   ├── clinical_guidelines.py
│   │   ├── confidence_assessor.py
│   │   ├── response_synthesizer.py
│   │   ├── agentic_rag.py       # NEW: LangGraph agentic wrapper
│   │   ├── nodes/               # NEW: Guardrail, grading, rewriting
│   │   ├── state.py             # Enhanced state
│   │   ├── context.py           # Runtime dependency injection
│   │   └── prompts.py           # Medical-domain prompts
│   ├── opensearch/              # NEW: Search engine client
│   ├── embeddings/              # NEW: Production embeddings
│   ├── cache/                   # NEW: Redis caching
│   ├── langfuse/                # NEW: Observability
│   ├── ollama/                  # NEW: Local LLM client
│   ├── indexing/                # NEW: Chunking + indexing
│   ├── pdf_parser/              # Enhanced: Use Docling
│   ├── telegram/                # NEW: Bot integration
│   └── biomarker/               # Extracted: validation + normalization
├── evaluation/                  # KEEP: 5D evaluation
└── evolution/                   # KEEP: SOP evolution
```

**Tasks:**
- [ ] Create the new directory structure
- [ ] Move API from `api/app/` into `src/` (single application)
- [ ] Create `exceptions.py` with medical-domain exception hierarchy
- [ ] Create `dependencies.py` with typed FastAPI dependency injection
- [ ] Create `main.py` with proper lifespan context manager

### 1.5 Development Tooling

**Tasks:**
- [ ] Create `pyproject.toml` replacing `requirements.txt` (use UV)
- [ ] Create `Makefile` with start/stop/test/lint/format/health commands
- [ ] Add `ruff` for linting and formatting
- [ ] Add `mypy` for type checking
- [ ] Add `.pre-commit-config.yaml`
- [ ] Create `.env.example` and `.env.test`

---

## Phase 2: Medical Data Ingestion Pipeline (Week 2 Equivalent)

> **Goal**: Automated ingestion of medical PDFs, clinical guidelines, and reference documents with Airflow orchestration.

### 2.1 Medical PDF Parser Upgrade

Replace basic PyPDF with Docling for better medical document handling:

**Tasks:**
- [ ] Create `src/services/pdf_parser/` with Docling integration (copy course pattern)
- [ ] Add medical-specific section detection (Abstract, Methods, Results, Discussion, Clinical Guidelines)
- [ ] Add table extraction for lab reference ranges
- [ ] Add validation: file size limits, page limits, PDF header check
- [ ] Add metadata extraction: title, authors, publication date, journal

### 2.2 Medical Document Sources

Unlike arXiv (single API), medical literature comes from multiple sources:

**Tasks:**
- [ ] Create `src/services/medical_sources/` package
- [ ] Implement PubMed API client (free, rate-limited) for research papers
- [ ] Implement local PDF upload endpoint for clinical guidelines
- [ ] Implement reference document ingestion (WHO, CDC, ADA guidelines)
- [ ] Create document deduplication logic (by title hash + content fingerprint)
- [ ] Add `MedicalDocument` model tracking: source, parse status, indexing status

### 2.3 Airflow Pipeline for Medical Literature

**Tasks:**
- [ ] Create `airflow/` directory with Dockerfile and entrypoint
- [ ] Create `airflow/dags/medical_ingestion.py` DAG:
  - `setup_environment` → `fetch_new_documents` → `parse_pdfs` → `chunk_and_index` → `generate_report`
- [ ] Schedule: Daily at 6 AM for PubMed updates, on-demand for uploaded PDFs
- [ ] Add retry logic with exponential backoff
- [ ] Mount `src/` into Airflow container for shared code

### 2.4 PostgreSQL Storage for Documents

**Tasks:**
- [ ] Create `MedicalDocument` model: id, title, source, source_type, authors, abstract, raw_text, sections, parse_status, indexed_at
- [ ] Create `PaperRepository` with CRUD + upsert + status tracking
- [ ] Track processing pipeline: `uploaded → parsed → chunked → indexed`
- [ ] Store parsed sections as JSON for re-indexing without re-parsing

---

## Phase 3: Production Search Foundation (Week 3 Equivalent)

> **Goal**: Replace FAISS with OpenSearch for production BM25 keyword search with medical-specific optimizations.

### 3.1 OpenSearch Client

**Tasks:**
- [ ] Create `src/services/opensearch/` package (adapt course pattern)
- [ ] Implement `OpenSearchClient` with:
  - Health check, index management, BM25 search, bulk indexing
  - **Medical-specific**: Boost clinical term matches, support ICD-10 code filtering
- [ ] Create `QueryBuilder` with medical field boosting:
  ```
  fields: ["chunk_text^3", "title^2", "section_title^1.5", "abstract^1"]
  ```
- [ ] Create `index_config_hybrid.py` with medical document mapping:
  - Fields: chunk_text, title, authors, abstract, document_type (guideline/research/reference), condition_tags, publication_year

### 3.2 Medical Document Index Mapping

```python
MEDICAL_CHUNKS_MAPPING = {
    "settings": {
        "index.knn": True,
        "analysis": {
            "analyzer": {
                "medical_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "medical_synonyms", "stop", "snowball"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "chunk_text": {"type": "text", "analyzer": "medical_analyzer"},
            "document_type": {"type": "keyword"},  # guideline, research, reference
            "condition_tags": {"type": "keyword"},  # diabetes, anemia, etc.
            "biomarkers_mentioned": {"type": "keyword"},  # Glucose, HbA1c, etc.
            "embedding": {"type": "knn_vector", "dimension": 1024},
            # ... more fields
        }
    }
}
```

**Tasks:**
- [ ] Design medical-optimized OpenSearch mapping
- [ ] Add medical synonym analyzer (e.g., "diabetes mellitus" ↔ "DM", "HbA1c" ↔ "glycated hemoglobin")
- [ ] Create search endpoint `POST /api/v1/search` with filtering by document_type, condition_tags
- [ ] Implement BM25 search with medical field boosting
- [ ] Create index verification in startup lifespan

---

## Phase 4: Hybrid Search & Intelligent Chunking (Week 4 Equivalent)

> **Goal**: Section-aware chunking for medical documents + hybrid search (BM25 + semantic) with RRF fusion.

### 4.1 Medical-Aware Text Chunking

**Tasks:**
- [ ] Create `src/services/indexing/text_chunker.py` adapting course's `TextChunker`:
  - Section-aware chunking (detect: Introduction, Methods, Results, Discussion, Guidelines, References)
  - Target: 600 words per chunk, 100 word overlap
  - Medical metadata: section_title, biomarkers_mentioned, condition_tags
- [ ] Create `MedicalTextChunker` subclass with:
  - Biomarker mention detection (scan for any of 24+ biomarker names)
  - Condition tag extraction (diabetes, anemia, heart disease, etc.)
  - Table-aware chunking (keep tables together)
  - Reference section filtering (skip bibliography chunks)
- [ ] Create `HybridIndexingService` for chunk → embed → index pipeline

### 4.2 Production Embeddings

**Tasks:**
- [ ] Create `src/services/embeddings/` with Jina AI client (1024d, passage/query differentiation)
- [ ] Add fallback chain: Jina → Google → HuggingFace
- [ ] Implement batch embedding for efficient indexing
- [ ] Track embedding model in chunk metadata for versioning

### 4.3 Hybrid Search with RRF

**Tasks:**
- [ ] Implement `search_unified()` supporting: BM25-only, vector-only, hybrid modes
- [ ] Set up OpenSearch RRF (Reciprocal Rank Fusion) pipeline
- [ ] Create unified search endpoint `POST /api/v1/hybrid-search/`
- [ ] Add min_score filtering and result deduplication
- [ ] Benchmark: BM25 vs. vector vs. hybrid on medical queries

---

## Phase 5: Complete RAG Pipeline with Streaming (Week 5 Equivalent)

> **Goal**: Replace synchronous analysis with streaming RAG, add Gradio UI, optimize prompts.

### 5.1 Ollama Client Upgrade

**Tasks:**
- [ ] Create `src/services/ollama/` package (adapt course pattern)
- [ ] Implement `OllamaClient` with:
  - Health check, model listing, generate, streaming generate
  - Usage metadata extraction (tokens, latency)
  - LangChain integration: `get_langchain_model()` for structured output
- [ ] Create medical-specific RAG prompt templates:
  - `rag_medical_system.txt` — optimized for medical explanation generation
  - Structured output format for clinical responses
- [ ] Create `OllamaFactory` with `@lru_cache`

### 5.2 Streaming RAG Endpoints

**Tasks:**
- [ ] Create `POST /api/v1/ask` — standard RAG with medical context retrieval
- [ ] Create `POST /api/v1/stream` — SSE streaming for real-time responses
- [ ] Create `POST /api/v1/analyze/stream` — streaming biomarker analysis
- [ ] Integrate with existing multi-agent pipeline:
  ```
  Query → Hybrid Search → Medical Chunks → Agent Pipeline → Streaming Response
  ```

### 5.3 Gradio Medical Interface

**Tasks:**
- [ ] Create `src/gradio_app.py` for interactive medical RAG:
  - Biomarker input form (structured entry)
  - Natural language input (free text)
  - Streaming response display
  - Search mode selector (BM25, hybrid, vector)
  - Model selector
  - Analysis history display
- [ ] Create `gradio_launcher.py` for easy startup
- [ ] Expose on port 7861

### 5.4 Prompt Optimization

**Tasks:**
- [ ] Reduce prompt size by 60-80% (course achieved 80% reduction)
- [ ] Create focused medical prompts (separate: biomarker analysis, disease explanation, guidelines)
- [ ] Test prompt variants using 5D evaluation framework
- [ ] Store best prompts as SOP parameters (tie into evolution engine)

---

## Phase 6: Monitoring, Caching & Observability (Week 6 Equivalent)

> **Goal**: Add Langfuse tracing for the entire pipeline, Redis caching, and production monitoring.

### 6.1 Langfuse Integration

**Tasks:**
- [ ] Create `src/services/langfuse/` package (adapt course pattern):
  - `client.py` — LangfuseTracer wrapper with v3 SDK
  - `factory.py` — cached tracer factory
  - `tracer.py` — medical-specific RAGTracer with named steps
- [ ] Add spans for every pipeline step:
  - `biomarker_validation` → `query_embedding` → `search_retrieval` → `agent_execution` → `response_synthesis`
- [ ] Track per-request metrics:
  - Total latency, LLM tokens used, search results count, cache hit/miss, agent execution time
- [ ] Add Langfuse Docker services to docker-compose.yml
- [ ] Create trace visualization for medical analysis pipeline

### 6.2 Redis Caching

**Tasks:**
- [ ] Create `src/services/cache/` package (adapt course pattern):
  - Exact-match cache: SHA256(query + model + top_k + biomarkers) → cached response
  - TTL: 6 hours for general queries, 1 hour for biomarker analysis (values may change)
- [ ] Add caching to:
  - `/api/v1/ask` — cache RAG responses
  - `/api/v1/analyze` — cache full analysis results
  - Embeddings — cache frequently queried embeddings
- [ ] Add graceful fallback: cache miss → normal pipeline
- [ ] Track cache hit rates in Langfuse

### 6.3 Production Health Dashboard

**Tasks:**
- [ ] Enhance `/api/v1/health` to check all services:
  - PostgreSQL, OpenSearch, Redis, Ollama, Langfuse, Airflow
- [ ] Add `/api/v1/metrics` endpoint for operational metrics
- [ ] Create Langfuse dashboard for:
  - Average response time, cache hit rate, error rate, token costs
  - Per-agent execution times, search relevance scores

---

## Phase 7: Agentic RAG & Messaging Bot (Week 7 Equivalent)

> **Goal**: Wrap your multi-agent pipeline in a LangGraph agentic workflow with guardrails, document grading, and query rewriting. Add Telegram bot for mobile access.

### 7.1 Agentic RAG Wrapper

This is the most impactful upgrade — it adds **intelligence around your existing agents**:

```
User Query
    ↓
[GUARDRAIL] ──── Is this a medical/biomarker question? ────→ [OUT OF SCOPE]
    ↓ yes
[RETRIEVE] ──── Hybrid search for medical documents ────→ [TOOL: search]
    ↓
[GRADE DOCUMENTS] ──── Are results relevant? ────→ [REWRITE QUERY] ──→ loop
    ↓ yes
[CLINICAL ANALYSIS] ──── Your 6 medical agents ────→ structured analysis
    ↓
[GENERATE RESPONSE] ──── Synthesize with citations ────→ final answer
```

**Tasks:**
- [ ] Create `src/services/agents/agentic_rag.py` — `AgenticRAGService` class
- [ ] Create `src/services/agents/nodes/`:
  - `guardrail_node.py` — Medical domain validation (score 0-100)
    - In-scope: biomarker questions, disease queries, clinical guidelines
    - Out-of-scope: non-medical, general knowledge, harmful content
  - `retrieve_node.py` — Creates tool call with `max_retrieval_attempts`
  - `grade_documents_node.py` — LLM evaluates medical relevance
  - `rewrite_query_node.py` — LLM rewrites for better medical retrieval
  - `generate_answer_node.py` — Uses your existing agent pipeline OR direct LLM
  - `out_of_scope_node.py` — Polite medical-domain rejection
- [ ] Create `src/services/agents/state.py` — Enhanced state with guardrail_result, routing_decision, grading_results
- [ ] Create `src/services/agents/context.py` — Runtime context for dependency injection
- [ ] Create `src/services/agents/prompts.py` — Medical-specific prompts:
  - Guardrail: "Is this about health/biomarkers/medical conditions?"
  - Grading: "Does this medical document answer the clinical question?"
  - Rewriting: "Improve this medical query for better document retrieval"
  - Generation: "Synthesize medical findings with citations and safety caveats"
- [ ] Create `src/services/agents/tools.py` — Medical retriever tool wrapping OpenSearch
- [ ] Create `POST /api/v1/ask-agentic` endpoint
- [ ] Add Langfuse tracing to every node

### 7.2 Medical Guardrails (Critical for MedTech)

Beyond the course's simple domain check, add medical-specific safety:

**Tasks:**
- [ ] **Input guardrails**:
  - Detect harmful queries (self-harm, drug abuse guidance)
  - Detect attempts to get diagnosis without proper data
  - Validate biomarker values are physiologically plausible
- [ ] **Output guardrails**:
  - Always include "consult your healthcare provider" disclaimer
  - Never provide definitive diagnosis (always "suggests" / "may indicate")
  - Flag critical biomarker values with immediate action advice
  - Ensure safety_alerts are present for out-of-range values
- [ ] **Citation guardrails**:
  - Ensure all medical claims have document citations
  - Flag unsupported claims

### 7.3 Telegram Bot Integration

**Tasks:**
- [ ] Create `src/services/telegram/` package (adapt course pattern)
- [ ] Implement bot commands:
  - `/start` — Welcome with medical assistant introduction
  - `/help` — Show capabilities and input format
  - `/analyze <biomarker values>` — Quick biomarker analysis
  - `/search <medical query>` — Search medical documents
  - `/report` — Get last analysis as formatted report
  - Free text — Full RAG Q&A about medical topics
- [ ] Add typing indicators and progress messages
- [ ] Integrate caching for repeated queries
- [ ] Add rate limiting (medical queries shouldn't be spammed)
- [ ] Create `TelegramFactory` gated by `TELEGRAM__ENABLED=true`

### 7.4 Feedback Loop

**Tasks:**
- [ ] Create `POST /api/v1/feedback` endpoint (adapt from course)
- [ ] Integrate with Langfuse scoring
- [ ] Use feedback data to identify weak prompts → feed into SOP evolution engine

---

## Phase 8: MedTech-Specific Additions (Beyond Course)

> **Goal**: Things the course doesn't cover but your medical domain demands.

### 8.1 HIPAA-Awareness Patterns

**Tasks:**
- [ ] Never log patient biomarker values in plain text
- [ ] Add request ID tracking without PII
- [ ] Create data retention policy (auto-delete analysis data after configurable period)
- [ ] Add audit logging for all analysis requests
- [ ] Document HIPAA compliance approach (even if not yet certified)

### 8.2 Medical Safety Testing

**Tasks:**
- [ ] Create medical-specific test suite:
  - Critical value detection tests (every critical biomarker)
  - Guardrail rejection tests (non-medical queries)
  - Citation completeness tests
  - Safety disclaimer presence tests
  - Biomarker normalization tests (already have some)
- [ ] Integrate 5D evaluation into CI pipeline
- [ ] Create test fixtures with realistic medical scenarios

### 8.3 Evolution Engine Integration

**Tasks:**
- [ ] Wire SOP evolution engine to production metrics (Langfuse data)
- [ ] Create Airflow DAG for scheduled evolution cycles
- [ ] Store evolved SOPs in PostgreSQL with version tracking
- [ ] A/B test SOP variants using Langfuse trace comparison

### 8.4 Multi-condition Support

**Tasks:**
- [ ] Extend condition coverage beyond current 5 diseases
- [ ] Add condition-specific retrieval strategies
- [ ] Create condition-specific chunking filters
- [ ] Support multi-condition analysis (comorbidities)

---

## Implementation Priority Matrix

| Priority | Phase | Effort | Impact | Dependencies |
|----------|-------|--------|--------|--------------|
| 🔴 P0 | 1.1 Docker Compose | 2 days | Critical | None |
| 🔴 P0 | 1.2 Pydantic Settings | 1 day | Critical | None |
| 🔴 P0 | 1.4 Project Restructure | 2 days | Critical | None |
| 🔴 P0 | 1.5 Dev Tooling | 0.5 day | Critical | 1.4 |
| 🔴 P0 | 1.3 PostgreSQL + Models | 2 days | Critical | 1.1, 1.4 |
| 🟡 P1 | 3.1 OpenSearch Client | 2 days | High | 1.1, 1.4 |
| 🟡 P1 | 3.2 Medical Index Mapping | 1 day | High | 3.1 |
| 🟡 P1 | 4.1 Medical Text Chunker | 2 days | High | 3.1 |
| 🟡 P1 | 4.2 Production Embeddings | 1 day | High | 4.1 |
| 🟡 P1 | 4.3 Hybrid Search + RRF | 1 day | High | 3.1, 4.2 |
| 🟡 P1 | 5.1 Ollama Client | 1 day | High | 1.4 |
| 🟡 P1 | 5.2 Streaming Endpoints | 1 day | High | 5.1, 4.3 |
| 🟡 P1 | 2.1 PDF Parser (Docling) | 1 day | High | 1.4 |
| 🟡 P1 | 7.1 Agentic RAG Wrapper | 3 days | High | 5.2, 4.3 |
| 🟡 P1 | 7.2 Medical Guardrails | 2 days | High | 7.1 |
| 🟢 P2 | 2.3 Airflow Pipeline | 2 days | Medium | 1.1, 2.1, 4.1 |
| 🟢 P2 | 5.3 Gradio Interface | 1 day | Medium | 5.2 |
| 🟢 P2 | 6.1 Langfuse Tracing | 2 days | Medium | 1.1, 5.2 |
| 🟢 P2 | 6.2 Redis Caching | 1 day | Medium | 1.1, 5.2 |
| 🟢 P2 | 6.3 Health Dashboard | 0.5 day | Medium | 6.1 |
| 🟢 P2 | 7.3 Telegram Bot | 2 days | Medium | 7.1, 6.2 |
| 🟢 P2 | 7.4 Feedback Loop | 0.5 day | Medium | 6.1 |
| 🔵 P3 | 2.2 Medical Sources | 2 days | Low | 2.1 |
| 🔵 P3 | 8.1 HIPAA Patterns | 1 day | Low | 1.3 |
| 🔵 P3 | 8.2 Safety Testing | 2 days | Low | 7.2 |
| 🔵 P3 | 8.3 Evolution Integration | 2 days | Low | 6.1, 2.3 |
| 🔵 P3 | 8.4 Multi-condition | 3 days | Low | 4.1 |

**Estimated Total: ~40 days of focused work**

---

## Migration Strategy

### Step 1: Foundation (Week 1-2 of work)
1. Restructure project layout → Phase 1.4
2. Create Pydantic Settings → Phase 1.2
3. Set up Docker Compose → Phase 1.1
4. Add PostgreSQL with models → Phase 1.3
5. Add dev tooling → Phase 1.5

### Step 2: Search Engine (Week 2-3)
6. Create OpenSearch client + medical mapping → Phase 3.1, 3.2
7. Build medical text chunker → Phase 4.1
8. Add production embeddings (Jina) → Phase 4.2
9. Implement hybrid search + RRF → Phase 4.3
10. Upgrade PDF parser to Docling → Phase 2.1

### Step 3: RAG Pipeline (Week 3-4)
11. Create Ollama client → Phase 5.1
12. Add streaming endpoints → Phase 5.2
13. Build agentic RAG wrapper → Phase 7.1
14. Add medical guardrails → Phase 7.2
15. Create Gradio interface → Phase 5.3

### Step 4: Production Hardening (Week 4-5)
16. Add Langfuse observability → Phase 6.1
17. Add Redis caching → Phase 6.2
18. Set up Airflow pipeline → Phase 2.3
19. Build Telegram bot → Phase 7.3
20. Add feedback loop → Phase 7.4

### Step 5: Polish (Week 5-6)
21. Health dashboard → Phase 6.3
22. Medical safety testing → Phase 8.2
23. HIPAA patterns → Phase 8.1
24. Evolution engine integration → Phase 8.3

### Key Migration Rules
- **Never break what works**: Keep all existing agents functional throughout
- **Test at every step**: Run existing tests after each phase
- **Incremental Docker**: Start with API + PostgreSQL, add services one at a time
- **Feature flags**: Gate new features (Telegram, Langfuse, Redis) behind settings
- **Backward compatibility**: Keep CLI chatbot working alongside new API

---

## Architecture Target State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Docker Compose Orchestration                         │
│                                                                          │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌────────┐  ┌─────────┐  │
│  │ FastAPI   │  │PostgreSQL │  │ OpenSearch │  │ Ollama │  │ Airflow │  │
│  │ + Gradio  │  │ (reports, │  │ (hybrid   │  │ (local │  │ (daily  │  │
│  │ (8000,    │  │  docs,    │  │  medical  │  │  LLM)  │  │ ingest) │  │
│  │  7861)    │  │  history) │  │  search)  │  │        │  │         │  │
│  └────┬─────┘  └─────┬─────┘  └─────┬─────┘  └───┬────┘  └────┬────┘  │
│       │              │              │             │            │        │
│  ┌────┴─────┐  ┌─────┴─────┐  ┌────┴────────────┴────────────┴──┐    │
│  │  Redis   │  │ Langfuse  │  │        mediguard-network         │    │
│  │ (cache)  │  │ (observe) │  └──────────────────────────────────┘    │
│  └──────────┘  └───────────┘                                          │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Agentic RAG Pipeline                            │  │
│  │                                                                    │  │
│  │  Query → [Guardrail] → [Retrieve] → [Grade] → [6 Medical Agents] │  │
│  │              ↓              ↑          ↓              ↓            │  │
│  │        [Out of Scope]  [Rewrite]  [Generate]  → Final Response    │  │
│  │                                                                    │  │
│  │  Agents: Biomarker Analyzer │ Disease Explainer │ Linker          │  │
│  │          Clinical Guidelines │ Confidence │ Synthesizer           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ Telegram Bot │  │  Gradio UI   │  │  5D Eval + SOP Evolution     │  │
│  │ (mobile)     │  │  (desktop)   │  │  (self-improvement loop)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files to Create (Summary)

| New File | Source of Inspiration |
|----------|----------------------|
| `docker-compose.yml` | Course `compose.yml` (adapted) |
| `Dockerfile` | Course `Dockerfile` (multi-stage UV) |
| `Makefile` | Course `Makefile` |
| `pyproject.toml` | Course `pyproject.toml` |
| `.pre-commit-config.yaml` | Course `.pre-commit-config.yaml` |
| `.env.example` | Course `.env.example` |
| `src/main.py` | Course `src/main.py` (lifespan pattern) |
| `src/config.py` | Course `src/config.py` + existing SOP config |
| `src/dependencies.py` | Course `src/dependencies.py` |
| `src/exceptions.py` | Course `src/exceptions.py` (medical exceptions) |
| `src/database.py` | Course `src/database.py` |
| `src/db/*` | Course `src/db/*` |
| `src/models/analysis.py` | New (medical domain) |
| `src/models/document.py` | Course `src/models/paper.py` (adapted) |
| `src/repositories/*` | Course `src/repositories/*` (adapted) |
| `src/routers/ask.py` | Course `src/routers/ask.py` |
| `src/routers/search.py` | Course `src/routers/hybrid_search.py` |
| `src/routers/health.py` | Course `src/routers/ping.py` (enhanced) |
| `src/schemas/*` | Course `src/schemas/*` (medical schemas) |
| `src/services/opensearch/*` | Course `src/services/opensearch/*` |
| `src/services/embeddings/*` | Course `src/services/embeddings/*` |
| `src/services/ollama/*` | Course `src/services/ollama/*` |
| `src/services/cache/*` | Course `src/services/cache/*` |
| `src/services/langfuse/*` | Course `src/services/langfuse/*` |
| `src/services/indexing/*` | Course `src/services/indexing/*` (medical chunks) |
| `src/services/pdf_parser/*` | Course `src/services/pdf_parser/*` |
| `src/services/telegram/*` | Course `src/services/telegram/*` |
| `src/services/agents/agentic_rag.py` | Course (adapted for medical agents) |
| `src/services/agents/nodes/*` | Course (medical guardrails) |
| `src/services/agents/context.py` | Course |
| `src/services/agents/prompts.py` | Course (medical prompts) |
| `src/gradio_app.py` | Course `src/gradio_app.py` (medical UI) |
| `airflow/dags/medical_ingestion.py` | Course `airflow/dags/arxiv_paper_ingestion.py` |

## Files to Keep & Enhance

| Existing File | Action |
|---------------|--------|
| `src/agents/biomarker_analyzer.py` | Keep, move to `src/services/agents/medical/` |
| `src/agents/disease_explainer.py` | Keep, move, add OpenSearch retriever |
| `src/agents/biomarker_linker.py` | Keep, move, add OpenSearch retriever |
| `src/agents/clinical_guidelines.py` | Keep, move, add OpenSearch retriever |
| `src/agents/confidence_assessor.py` | Keep, move |
| `src/agents/response_synthesizer.py` | Keep, move |
| `src/biomarker_validator.py` | Keep, move to `src/services/biomarker/` |
| `src/biomarker_normalization.py` | Keep, move to `src/services/biomarker/` |
| `src/evaluation/` | Keep, enhance with Langfuse integration |
| `src/evolution/` | Keep, wire to production metrics |
| `config/biomarker_references.json` | Keep as seed data, migrate to DB |
| `scripts/chat.py` | Keep, update imports |
| `tests/*` | Keep, add production test fixtures |

---

*This plan transforms MediGuard AI from a working prototype into a production-grade medical RAG system, applying every infrastructure lesson from the arXiv Paper Curator course while preserving and enhancing your unique medical domain logic.*
