╔════════════════════════════════════════════════════════════════════════════╗
║    📚 SKILL-TO-CODE MAPPING: Where Each Skill Applies in RagBot          ║
║         Reference guide showing skill application locations                ║
╚════════════════════════════════════════════════════════════════════════════╝

This document maps each of the 34 skills to specific code files and critical
issues they resolve. Use this for quick lookup: "Where do I apply Skill #X?"

════════════════════════════════════════════════════════════════════════════════

CRITICAL ISSUES MAPPING TO SKILLS
════════════════════════════════════════════════════════════════════════════════

ISSUE #1: biomarker_flags & safety_alerts not propagating through workflow
──────────────────────────────────────────────────────────────────────────────
Problem Location: src/state.py, src/agents/*.py, src/workflow.py
Affected Code:
  ├─ GuildState (missing fields)
  ├─ BiomarkerAnalyzerAgent.invoke() (only returns biomarkers)
  ├─ ResponseSynthesizerAgent.invoke() (fields missing in input)
  └─ Workflow edges (state not fully passed)

Primary Skills:
  ✓ #2  Workflow Orchestration Patterns → Fix state passing
  ✓ #3  Multi-Agent Orchestration     → Ensure deterministic flow
  ✓ #16 Structured Output             → Enforce complete schema

Secondary Skills:
  • #22 Testing Patterns              → Write tests for state flow
  • #27 Observability                 → Log state changes

Action: Read src/state.py → identify missing fields → update all agents to
        return complete state → test end-to-end


ISSUE #2: Schema mismatch between workflow output & API formatter
──────────────────────────────────────────────────────────────────────────────
Problem Location: src/workflow.py, api/app/models/ (missing or inconsistent)
Affected Code:
  ├─ ResponseSynthesizerAgent output structure (varies)
  ├─ api/app/services/ragbot.py format_response() (expects different keys)
  ├─ CLI scripts/chat.py (different field names)
  └─ Tests referencing old schema

Primary Skills:
  ✓ #16 AI Wrapper/Structured Output → Create unified Pydantic model
  ✓ #22 Testing Patterns              → Write schema validation tests

Secondary Skills:
  • #27 Observability                 → Log schema mismatches (debugging)

Action: Create api/app/models/response.py with BaseAnalysisResponse →
        update all agents to return it → validate in API


ISSUE #3: Prediction confidence forced to 0.5 (dangerous for medical)
──────────────────────────────────────────────────────────────────────────────
Problem Location: src/agents/confidence_assessor.py, api/app/routes/analyze.py
Affected Code:
  ├─ ConfidenceAssessorAgent.invoke() (ignores actual assessment)
  ├─ Default response in analyze endpoint (hardcoded 0.5)
  └─ CLI logic (no failure path for low confidence)

Primary Skills:
  ✓ #13 Senior Prompt Engineer        → Better reasoning in assessor
  ✓ #14 LLM Evaluation                → Benchmark accuracy

Secondary Skills:
  • #4  Agentic Development           → Decision logic improvements
  • #22 Testing Patterns              → Test confidence boundaries
  • #27 Observability                 → Track confidence distributions

Action: Update confidence_assessor.py to use actual evidence → test with
        multiple biomarker scenarios → Add high/medium/low confidence paths


ISSUE #4: Biomarker naming inconsistency (API vs CLI)
──────────────────────────────────────────────────────────────────────────────
Problem Location: config/biomarker_references.json, src/agents/*, api/*
Affected Code:
  ├─ config/biomarker_references.json (canonical list)
  ├─ BiomarkerAnalyzerAgent (validation against reference)
  ├─ CLI scripts/chat.py (different naming)
  └─ API endpoints (naming transformation)

Primary Skills:
  ✓ #9  Chunking Strategy             → Include standard names in embedding
  ✓ #16 Structured Output             → Enforce standard field names

Secondary Skills:
  • #10 Embedding Pipeline            → Index with canonical names
  • #22 Testing Patterns              → Test name transformation
  • #27 Observability                 → Log name mismatches

Action: Create biomarker_normalizer() → apply in all code paths → add
        mapping tests


ISSUE #5: JSON parsing breaks on malformed LLM output
──────────────────────────────────────────────────────────────────────────────
Problem Location: api/app/services/extraction.py, src/agents/extraction code
Affected Code:
  ├─ LLM.predict() returns text
  ├─ json.loads() has no error handling
  ├─ Invalid JSON crashes endpoint
  └─ No fallback strategy

Primary Skills:
  ✓ #5  Tool/Function Calling         → Use function calling instead
  ✓ #21 Python Error Handling         → Graceful degradation

Secondary Skills:
  • #16 Structured Output             → Pydantic validation
  • #19 LLM Security                  → Prevent injection in JSON
  • #27 Observability                 → Log parsing failures
  • #14 LLM Evaluation                → Track failure rate

Action: Replace json.loads() with Pydantic validator → implement retry logic
        → add function calling as fallback


ISSUE #6: No citation enforcement in RAG outputs
──────────────────────────────────────────────────────────────────────────────
Problem Location: src/agents/disease_explainer.py, response synthesis
Affected Code:
  ├─ retriever.retrieve() returns docs but citations dropped
  ├─ DiseaseExplainerAgent doesn't track sources
  ├─ ResponseSynthesizerAgent loses citation info
  └─ API response has no source attribution

Primary Skills:
  ✓ #11 RAG Implementation            → Enforce citations in loop
  ✓ #8  Hybrid Search                 → Better relevance = better cites
  ✓ #12 Knowledge Graph               → Link to authoritative sources

Secondary Skills:
  • #1  LangChain Architecture        → Tool for citation tracking
  • #7  RAG Agent Builder             → Full RAG best practices
  • #14 LLM Evaluation                → Test for hallucinations
  • #27 Observability                 → Track citation frequency

Action: Modify disease_explainer.py to preserve doc metadata → add citation
        validation → return sources in API response

════════════════════════════════════════════════════════════════════════════════

SKILL-BY-SKILL APPLICATION GUIDE
════════════════════════════════════════════════════════════════════════════════

#1 LangChain Architecture
  Phase: 3, Week 7
  Apply To: src/agents/, src/services/
  Key Files:
    └─ src/agents/base_agent.py (NEW) - Create BaseAgent with LangChain patterns
    └─ src/agents/*/invoke() - Add callbacks, chains, tools
    └─ src/services/*.py - RunnableWithMessageHistory for conversation
  Integration: Advanced chain composition, callbacks for metrics
  Outcome: More sophisticated agent orchestration
  Effort: 3-4 hours

#2 Workflow Orchestration Patterns
  Phase: 1, Week 1 / Phase 4, Week 12 (final review)
  Apply To: src/workflow.py, src/state.py
  Key Files:
    └─ src/state.py - REFACTOR GuildState with all fields
    └─ src/workflow.py - REFACTOR state passing between agents
    └─ src/agents/biomarker_analyzer.py - Return complete state
    └─ src/agents/disease_explainer.py - Preserve incoming state
  Integration: Fix Issue #1 (state propagation)
  Outcome: biomarker_flags & safety_alerts flow through entire workflow
  Effort: 4-6 hours (Week 1) + 2 hours (Week 12 refine)

#3 Multi-Agent Orchestration
  Phase: 1, Week 2
  Apply To: src/workflow.py
  Key Files:
    └─ src/workflow.py - Ensure deterministic agent order
    └─ Parallel execution order documentation
  Integration: Ensure agents execute in correct order with proper state passing
  Outcome: Deterministic workflow execution
  Effort: 3-4 hours

#4 Agentic Development
  Phase: 2, Week 3
  Apply To: src/agents/biomarker_analyzer.py, confidence_assessor.py
  Key Files:
    └─ BiomarkerAnalyzerAgent.invoke() - Add confidence thresholds
    └─ ConfidenceAssessorAgent - Better decision logic
    └─ Add reasoning trace to responses
  Integration: Better medical decisions, alternatives for low confidence
  Outcome: More reliable biomarker analysis
  Effort: 3-4 hours

#5 Tool/Function Calling Patterns
  Phase: 2, Week 4
  Apply To: api/app/services/extraction.py, src/agents/extraction.py
  Key Files:
    └─ api/app/services/extraction.py - Define extraction tools/functions
    └─ src/agents/ - Use function returns instead of JSON parsing
  Integration: Fix Issue #5 (JSON parsing fragility)
  Outcome: Structured LLM outputs guaranteed valid
  Effort: 3-4 hours

#6 LLM Application Dev with LangChain
  Phase: 4, Week 11
  Apply To: src/agents/ (production patterns)
  Key Files:
    └─ src/agents/base_agent.py - Implement lifecycle (setup, execute, cleanup)
    └─ All agents - Add retry logic, graceful degradation
    └─ Agent composition patterns - Chain agents
  Integration: Production-ready agent code
  Outcome: Robust, maintainable agents with error recovery
  Effort: 4-5 hours

#7 RAG Agent Builder
  Phase: 4, Week 12
  Apply To: src/agents/ (full review)
  Key Files:
    └─ src/agents/disease_explainer.py - RAG pattern review
    └─ Ensure all responses cite sources
    └─ Verify accuracy benchmarks
  Integration: Full RAG agent validation before production
  Outcome: Production-ready RAG agents
  Effort: 4-5 hours

#8 Hybrid Search Implementation
  Phase: 3, Week 6
  Apply To: src/retrievers/ (NEW)
  Key Files:
    └─ src/retrievers/hybrid_retriever.py (NEW) - Combine BM25 + FAISS
    └─ src/agents/disease_explainer.py - Use hybrid retriever
  Integration: Better document retrieval (semantic + keyword)
  Outcome: +15% recall on rare disease queries
  Effort: 4-6 hours

#9 Chunking Strategy
  Phase: 3, Week 6
  Apply To: src/chunking_strategy.py (NEW), src/pdf_processor.py
  Key Files:
    └─ src/chunking_strategy.py (NEW) - Split by medical sections
    └─ scripts/setup_embeddings.py - Use new chunking
    └─ Re-chunk and re-embed medical_knowledge.faiss
  Integration: Fix Issue #4 (naming), improve context window usage
  Outcome: Better semantic chunks, improved retrieval quality
  Effort: 4-5 hours

#10 Embedding Pipeline Builder
  Phase: 3, Week 6
  Apply To: src/llm_config.py, scripts/setup_embeddings.py
  Key Files:
    └─ src/llm_config.py - Consider medical embedding models
    └─ scripts/setup_embeddings.py - Use new embeddings
    └─ Benchmark embedding quality
  Integration: Better semantic search for medical terminology
  Outcome: Improved document relevance ranking
  Effort: 3-4 hours

#11 RAG Implementation
  Phase: 3, Week 6
  Apply To: src/agents/disease_explainer.py
  Key Files:
    └─ src/agents/disease_explainer.py - Track and enforce citations
    └─ src/models/response.py - Add sources field
    └─ api/app/routes/analyze.py - Return sources
  Integration: Fix Issue #6 (no citations), enforce medical accuracy
  Outcome: All claims backed by sources
  Effort: 3-4 hours

#12 Knowledge Graph Builder
  Phase: 3, Week 7
  Apply To: src/knowledge_graph.py (NEW)
  Key Files:
    └─ src/knowledge_graph.py (NEW) - Disease → Biomarker → Treatment graph
    └─ Extract entities from medical PDFs
    └─ src/agents/biomarker_analyzer.py - Use knowledge graph
    └─ Create graph.html visualization
  Integration: Better disease prediction via relationships
  Outcome: Knowledge graph with 100+ nodes, 500+ edges
  Effort: 6-8 hours

#13 Senior Prompt Engineer
  Phase: 2, Week 3
  Apply To: src/agents/ (all agent prompts)
  Key Files:
    └─ src/agents/biomarker_analyzer.py - Prompt: few-shot extraction
    └─ src/agents/disease_explainer.py - Prompt: chain-of-thought reasoning
    └─ src/agents/confidence_assessor.py - Prompt: decision logic
    └─ src/agents/clinical_guidelines.py - Prompt: evidence-based
  Integration: Fix Issue #3 (confidence), improve medical reasoning
  Outcome: +15% accuracy improvement
  Effort: 5-6 hours

#14 LLM Evaluation
  Phase: 2, Week 4
  Apply To: tests/evaluation_metrics.py (NEW)
  Key Files:
    └─ tests/evaluation_metrics.py (NEW) - Benchmarking suite
    └─ tests/fixtures/evaluation_patients.py - Test scenarios
    └─ Benchmark Groq vs Gemini performance
    └─ Track before/after improvements
  Integration: Measure all improvements quantitatively
  Outcome: Clear metrics showing progress
  Effort: 4-5 hours

#15 Cost-Aware LLM Pipeline
  Phase: 3, Week 8
  Apply To: src/llm_config.py
  Key Files:
    └─ src/llm_config.py - Model routing by complexity
    └─ Implement caching (hash → result)
    └─ Cost tracking and reporting
    └─ Target: -40% cost reduction
  Integration: Optimize API costs without sacrificing accuracy
  Outcome: Lower operational costs
  Effort: 4-5 hours

#16 AI Wrapper/Structured Output
  Phase: 1, Week 1
  Apply To: api/app/models/ (NEW and REFACTORED)
  Key Files:
    └─ api/app/models/response.py (NEW) - Create unified BaseAnalysisResponse
    └─ api/app/services/ragbot.py - Use unified schema
    └─ All agents - Match unified output
    └─ API responses - Validate with Pydantic
  Integration: Fix Issues #1, #2, #4, #5 (schema consistency)
  Outcome: Single canonical response format
  Effort: 3-5 hours

#17 API Security Hardening
  Phase: 1, Week 1
  Apply To: api/app/middleware/, api/main.py
  Key Files:
    └─ api/app/middleware/auth.py (NEW) - JWT auth
    └─ api/main.py - Add security middleware chain
    └─ CORS, headers, rate limiting
  Integration: Secure REST API endpoints
  Outcome: API hardened against common attacks
  Effort: 4-6 hours

#18 OWASP Security Check
  Phase: 1, Week 1
  Apply To: docs/ (audit report)
  Key Files:
    └─ docs/SECURITY_AUDIT.md (NEW) - Security findings
    └─ Scan api/ and src/ for vulnerabilities
    └─ Create tickets for each issue
  Integration: Establish security baseline
  Outcome: All vulnerabilities documented and prioritized
  Effort: 2-3 hours

#19 LLM Security
  Phase: 1, Week 2
  Apply To: api/app/middleware/input_validation.py (NEW)
  Key Files:
    └─ api/app/middleware/input_validation.py (NEW) - Input sanitization
    └─ Detect prompt injection attempts
    └─ Validate biomarker inputs
    └─ Escape special characters
  Integration: Fix Issue #5 (JSON safety), prevent prompt injection
  Outcome: Inputs validated before LLM processing
  Effort: 3-4 hours

#20 API Rate Limiting
  Phase: 1, Week 1
  Apply To: api/app/middleware/rate_limiter.py (NEW)
  Key Files:
    └─ api/app/middleware/rate_limiter.py (NEW) - Token bucket limiter
    └─ api/main.py - Add to middleware chain
    └─ Tiered limits (free/pro based on API key)
  Integration: Protect API from abuse
  Outcome: Rate limiting in place
  Effort: 2-3 hours

#21 Python Error Handling
  Phase: 2, Week 2
  Apply To: src/exceptions.py (NEW), src/agents/
  Key Files:
    └─ src/exceptions.py (NEW) - Custom exception hierarchy
    └─ RagBotException, BiomarkerValidationError, LLMTimeoutError, etc.
    └─ All agents - Replace generic try-except
    └─ API - Proper error responses
  Integration: Graceful error handling throughout system
  Outcome: No uncaught exceptions, useful error messages
  Effort: 3-4 hours

#22 Python Testing Patterns
  Phase: 1, Week 1 + Phase 2, Week 3 (primary), Week 4
  Apply To: tests/ (throughout project)
  Key Files:
    └─ tests/conftest.py - Shared fixtures
    └─ tests/fixtures/ - auth, biomarkers, patients
    └─ tests/test_api_auth.py - Auth tests (Week 1)
    └─ tests/test_parametrized_*.py - 50+ parametrized tests (Week 3)
    └─ tests/test_response_schema.py - Schema validation (Week 1)
    └─ 80-90% code coverage
  Integration: Comprehensive test suite ensures reliability
  Outcome: 125+ tests, 90%+ coverage
  Effort: 10-13 hours total

#23 Code Review Excellence
  Phase: 4, Week 10
  Apply To: docs/REVIEW_GUIDELINES.md (NEW), all PRs
  Key Files:
    └─ docs/REVIEW_GUIDELINES.md (NEW) - Medical code review standards
    └─ Apply to all Phase 1-3 pull requests
    └─ Self-review checklist
  Integration: Maintain code quality
  Outcome: Clear review guidelines
  Effort: 2-3 hours

#24 GitHub Actions Templates
  Phase: 1, Week 2
  Apply To: .github/workflows/ (NEW)
  Key Files:
    └─ .github/workflows/test.yml - Run tests on PR
    └─ .github/workflows/security.yml - Security checks
    └─ .github/workflows/docker.yml - Build Docker images
  Integration: Automated CI/CD pipeline
  Outcome: Tests run automatically
  Effort: 2-3 hours

#25 FastAPI Templates
  Phase: 4, Week 9
  Apply To: api/app/main.py, api/app/dependencies.py
  Key Files:
    └─ api/app/main.py - REFACTOR with best practices
    └─ Async patterns, dependency injection
    └─ Connection pooling, caching headers
    └─ Health check endpoints
  Integration: Production-grade FastAPI configuration
  Outcome: Optimized API performance
  Effort: 3-4 hours

#26 Python Design Patterns
  Phase: 2, Week 3
  Apply To: src/agents/base_agent.py (NEW), src/agents/
  Key Files:
    └─ src/agents/base_agent.py (NEW) - Extract common pattern
    └─ Factory pattern for agent creation
    └─ Composition over inheritance
    └─ Refactor BiomarkerAnalyzerAgent, etc.
  Integration: Cleaner, more maintainable code
  Outcome: Reduced coupling, better abstractions
  Effort: 4-5 hours

#27 Python Observability
  Phase: 1, Week 2 (logging) / Phase 4, Week 10 (metrics) / Phase 2, Week 5
  Apply To: src/, api/app/
  Key Files:
    └─ src/observability.py (NEW) - Logging infrastructure (Week 2)
    └─ All agents - Add structured JSON logging
    └─ src/monitoring/ (NEW) - Prometheus metrics (Week 10)
    └─ Track latency, accuracy, costs
  Integration: Visibility into system behavior
  Outcome: JSON logs, metrics at /metrics
  Effort: 12-15 hours total

#28 Memory Management
  Phase: 3, Week 7
  Apply To: src/memory_manager.py (NEW)
  Key Files:
    └─ src/memory_manager.py (NEW) - Sliding window memory
    └─ Context compression for conversation history
    └─ Token usage optimization
  Integration: Handle long conversations without exceeding limits
  Outcome: 20-30% token savings
  Effort: 3-4 hours

#29 API Docs Generator
  Phase: 4, Week 9
  Apply To: api/app/routes/ (documentation)
  Key Files:
    └─ api/app/routes/*.py - Enhance docstrings
    └─ Add examples to endpoints
    └─ Auto-generates /docs (Swagger UI), /redoc
  Integration: API discoverable by developers
  Outcome: Interactive API documentation
  Effort: 2-3 hours

#30 GitHub PR Review Workflow
  Phase: 4, Week 9
  Apply To: .github/ (NEW)
  Key Files:
    └─ .github/CODEOWNERS - Code ownership rules
    └─ .github/pull_request_template.md - PR checklist
    └─ Branch protection rules
  Integration: Establish code review standards
  Outcome: Consistent PR quality
  Effort: 2-3 hours

#31 CI-CD Best Practices
  Phase: 4, Week 10
  Apply To: .github/workflows/deploy.yml (NEW)
  Key Files:
    └─ .github/workflows/deploy.yml (NEW) - Deployment pipeline
    └─ Build → Test → Staging → Canary → Production
    └─ Environment management (.env files)
  Integration: Automated, safe deployments
  Outcome: Confident production deployments
  Effort: 3-4 hours

#32 Frontend Accessibility (OPTIONAL)
  Phase: 4, Week 10
  Apply To: examples/web_interface/ (if building web UI)
  Key Files:
    └─ examples/web_interface/ - WCAG 2.1 AA compliance
  Integration: Accessible web interface (if needed)
  Outcome: Screen-reader friendly, keyboard navigable
  Effort: 2-3 hours (skip if CLI only)

#33 Webhook Receiver Hardener (OPTIONAL)
  Phase: 4, Week 11
  Apply To: api/app/webhooks/ (NEW, if integrations needed)
  Key Files:
    └─ api/app/webhooks/ (NEW) - Webhook handlers
    └─ Signature verification, replay protection
  Integration: Secure webhook handling for EHR integrations
  Outcome: Protected webhook endpoints
  Effort: 2-3 hours (skip if no webhooks)

════════════════════════════════════════════════════════════════════════════════

QUICK LOOKUP: BY FILE

api/app/main.py
  ├─ #17 API Security Hardening     (JWT middleware)
  ├─ #20 Rate Limiting               (rate limiter middleware)
  ├─ #25 FastAPI Templates           (async patterns)
  ├─ #24 GitHub Actions (workflow)   (CI/CD reference)
  └─ #29 API Docs Generator          (docstrings)

api/app/models/response.py (NEW)
  ├─ #16 AI Wrapper/Structured Output (unified schema)
  └─ #22 Testing Patterns            (Pydantic validation)

api/app/middleware/ (NEW)
  ├─ auth.py #17 API Security Hardening
  ├─ input_validation.py #19 LLM Security
  └─ rate_limiter.py #20 API Rate Limiting

src/state.py
  ├─ #2 Workflow Orchestration       (fix state fields)
  ├─ #16 Structured Output           (enforce schema)
  └─ #22 Testing Patterns            (state tests)

src/workflow.py
  ├─ #2 Workflow Orchestration       (state passing)
  ├─ #3 Multi-Agent Orchestration    (agent order)
  └─ #27 Observability               (logging)

src/agents/base_agent.py (NEW)
  ├─ #26 Python Design Patterns      (factory, composition)
  ├─ #6 LLM App Dev LangChain        (lifecycle)
  ├─ #21 Error Handling              (graceful degradation)
  └─ #27 Observability               (logging)

src/agents/biomarker_analyzer.py
  ├─ #4 Agentic Development          (confidence thresholds)
  ├─ #13 Senior Prompt Engineer      (prompt optimization)
  ├─ #2 Workflow Orchestration       (return complete state)
  └─ #12 Knowledge Graph             (use relationships)

src/agents/disease_explainer.py
  ├─ #8 Hybrid Search                (retriever)
  ├─ #11 RAG Implementation          (enforcement)
  ├─ #13 Senior Prompt Engineer      (chain-of-thought)
  ├─ #1 LangChain Architecture       (advanced patterns)
  └─ #7 RAG Agent Builder            (RAG best practices)

src/agents/confidence_assessor.py
  ├─ #4 Agentic Development          (decision logic)
  ├─ #13 Senior Prompt Engineer      (better reasoning)
  ├─ #14 LLM Evaluation              (benchmark)
  └─ #22 Testing Patterns            (confidence tests)

src/agents/clinical_guidelines.py
  ├─ #13 Senior Prompt Engineer      (evidence-based)
  └─ #1 LangChain Architecture       (advanced retrieval)

src/exceptions.py (NEW)
  ├─ #21 Python Error Handling       (exception hierarchy)
  └─ #27 Observability               (error logging)

src/retrievers/hybrid_retriever.py (NEW)
  ├─ #8 Hybrid Search Implementation (BM25 + FAISS)
  ├─ #9 Chunking Strategy            (better chunks)
  ├─ #10 Embedding Pipeline          (semantic search)
  └─ #27 Observability               (retrieval metrics)

src/chunking_strategy.py (NEW)
  ├─ #9 Chunking Strategy            (medical section splitting)
  ├─ #10 Embedding Pipeline          (prepare for embedding)
  └─ #4 Agentic Development          (standardization)

src/knowledge_graph.py (NEW)
  ├─ #12 Knowledge Graph Builder     (extract relationships)
  ├─ #13 Senior Prompt Engineer      (entity extraction prompt)
  └─ #1 LangChain Architecture       (graph traversal)

src/memory_manager.py (NEW)
  ├─ #28 Memory Management           (sliding window, compression)
  └─ #15 Cost-Aware Pipeline         (token optimization)

src/llm_config.py
  ├─ #15 Cost-Aware LLM Pipeline     (model routing, caching)
  ├─ #10 Embedding Pipeline          (embedding model config)
  └─ #27 Observability               (cost tracking)

src/observability.py (NEW)
  ├─ #27 Python Observability        (logging, metrics)
  ├─ #21 Error Handling              (error tracking)
  └─ #14 LLM Evaluation              (metric collection)

src/monitoring/ (NEW)
  └─ #27 Python Observability        (metrics, dashboards)

tests/conftest.py
  └─ #22 Python Testing Patterns     (shared fixtures)

tests/fixtures/
  ├─ auth.py #22 Testing Patterns
  ├─ biomarkers.py #22 Testing Patterns
  └─ evaluation_patients.py #14 LLM Evaluation

tests/test_api_auth.py (NEW)
  ├─ #22 Python Testing Patterns
  ├─ #17 API Security Hardening
  └─ #25 FastAPI Templates

tests/test_parametrized_*.py (NEW)
  └─ #22 Python Testing Patterns

tests/evaluation_metrics.py (NEW)
  └─ #14 LLM Evaluation

.github/workflows/
  ├─ test.yml #24 GitHub Actions Templates
  ├─ security.yml #18 OWASP Check + #24 Actions
  ├─ docker.yml #24 Actions
  └─ deploy.yml #31 CI-CD Best Practices

.github/
  ├─ CODEOWNERS #30 GitHub PR Review Workflow
  ├─ pull_request_template.md #30 Workflow
  └─ branch protection rules

docs/
  ├─ SECURITY_AUDIT.md #18 OWASP Check
  ├─ REVIEW_GUIDELINES.md #23 Code Review Excellence
  └─ API.md (updated by #29 API Docs Generator)

════════════════════════════════════════════════════════════════════════════════

SKILL DEPENDENCY GRAPH
════════════════════════════════════════════════════════════════════════════════

Phase 1 must finish before Phase 2:
  #18, #17, #22, #2, #16, #20, #3, #19, #21, #27, #24
    ↓
Phase 2 requires Phase 1:
  #22, #26, #4, #13, #14, #5
    ↓
Phase 3 requires Phases 1-2:
  #8, #9, #10, #11, #12, #1, #28, #15
    ↓
Phase 4 requires Phases 1-3:
  #25, #29, #30, #27, #23, #31, #32*, #6, #33*, #7

Within phases, some order dependencies:
  - #16 should complete before other Phase 1 work finalizes
  - #13 should complete before #14 evaluation
  - #8, #9, #10 should coordinate (hybrid search → chunking → embeddings)
  - #11 depends on #8 (retriever first)
  - #12 depends on #13 (prompt engineering for entity extraction)
  - #27 used 3 times (Week 2, Week 5, Week 10)
  - #22 used 2 times (Week 1, Weeks 3-4)

════════════════════════════════════════════════════════════════════════════════

DAILY WORKFLOW
════════════════════════════════════════════════════════════════════════════════

1. Open the skill SKILL.md documented in ~/.agents/skills/<skill-name>/
2. Read the relevant section for your task
3. Apply to specific code files listed above
4. Write tests immediately (use #22 Testing Patterns)
5. Commit with clear message: "feat: [Skill #X] [Description]"
6. Track in IMPLEMENTATION_STATUS_TRACKER.md

════════════════════════════════════════════════════════════════════════════════
