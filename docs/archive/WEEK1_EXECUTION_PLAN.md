╔════════════════════════════════════════════════════════════════════════════╗
║         🎯 QUICK START: THIS WEEK'S TASKS (12-Week Plan)                  ║
║              Use this for daily execution and progress tracking             ║
╚════════════════════════════════════════════════════════════════════════════╝

PHASE 1 - WEEK 1 ([CURRENT]) - Security + State Propagation
════════════════════════════════════════════════════════════════════════════════

MONDAY-TUESDAY: OWASP Audit + API Security
┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.1: Run OWASP Security Check (Skill #18)                          │
│ Time: 2-3 hours                                                          │
│ Actions:                                                                 │
│  □ npx skills unlock owasp-security-check                               │
│  □ Read ~/.agents/skills/owasp-security-check/SKILL.md                  │
│  □ Run security scan on /api and /src                                   │
│  □ Document findings in docs/SECURITY_AUDIT.md                          │
│  □ Create GitHub issues for each finding                                │
│ Deliverable: SECURITY_AUDIT.md with prioritized issues                 │
│ Success: Report shows all vulnerabilities categorized                   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.2: Implement JWT Authentication (Skill #17)                      │
│ Time: 4-6 hours                                                          │
│ Actions:                                                                 │
│  □ npx skills unlock api-security-hardening                             │
│  □ Read ~/.agents/skills/api-security-hardening/SKILL.md                │
│  □ Create api/app/middleware/auth.py (JWT generation + validation)      │
│  □ Add @require_auth decorator to api/app/routes/analyze.py             │
│  □ Update api/main.py to include auth middleware                        │
│  □ Test: curl -H "Authorization: Bearer <token>" /api/v1/analyze       │
│ Deliverable: JWT auth working on all endpoints                          │
│ Success: Unauthorized requests return 401                               │
└──────────────────────────────────────────────────────────────────────────┘

WEDNESDAY-THURSDAY: Test Infrastructure + State Fixing
┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.3: Create Testing Infrastructure (Skill #22)                     │
│ Time: 2-3 hours                                                          │
│ Actions:                                                                 │
│  □ npx skills unlock python-testing-patterns                            │
│  □ Create tests/conftest.py with fixtures                               │
│  □  Create tests/fixtures/auth.py (JWT token generator)                 │
│  □  Create tests/fixtures/biomarkers.py (test data)                     │
│  □ Create tests/test_api_auth.py with 10+ auth tests                    │
│  □ Run: pytest tests/test_api_auth.py -v                                │
│ Deliverable: Auth tests with 80%+ coverage                              │
│ Success: All auth tests passing                                         │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.4: Fix State Propagation in Workflow (Skill #2)                  │
│ Time: 4-6 hours                                                          │
│ Actions:                                                                 │
│  □ npx skills unlock workflow-orchestration-patterns                    │
│  □ Read ~/.agents/skills/workflow-orchestration-patterns/SKILL.md        │
│  □ Review src/state.py - identify missing fields                        │
│  □ Add to GuildState: biomarker_flags, safety_alerts                    │
│  □ Update each agent to return complete state:                          │
│    - BiomarkerAnalyzerAgent: add flags                                  │
│    - DiseaseExplainerAgent: preserve incoming flags                      │
│    - ConfidenceAssessorAgent: preserve all state                        │
│  □ Test: python scripts/test_chat_demo.py                               │
│  □ Verify state carries through entire workflow                         │
│ Deliverable: State propagates end-to-end                                │
│ Success: All fields present in final response                           │
└──────────────────────────────────────────────────────────────────────────┘

FRIDAY: Schema Unification + Rate Limiting
┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.5: Unify Response Schema (Skill #16)                             │
│ Time: 3-5 hours                                                          │
│ Actions:                                                                 │
│  □ npx skills unlock ai-wrapper-product                                 │
│  □ Create api/app/models/response.py (unified schema)                   │
│  □ Define BaseAnalysisResponse with all fields:                         │
│    - biomarkers: dict                                                   │
│    - disease: str                                                       │
│    - confidence: float                                                  │
│    - biomarker_flags: list                                              │
│    - safety_alerts: list (NEW)                                          │
│  □ Update api/app/services/ragbot.py to use unified schema              │
│  □ Test all endpoints return correct schema                             │
│  □ Run: pytest tests/test_response_schema.py -v                         │
│ Deliverable: Unified schema in place                                    │
│ Success: Pydantic validation passes                                     │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.6: Add Rate Limiting (Skill #20)                                 │
│ Time: 2-3 hours                                                          │
│ Actions:                                                                 │
│  □ npx skills unlock api-rate-limiting                                  │
│  □ Create api/app/middleware/rate_limiter.py                            │
│  □ Add rate limiting to api/main.py:                                    │
│    - 10 requests/minute (free tier)                                     │
│    - 100 requests/minute (pro tier)                                     │
│  □ Return 429 Too Many Requests with retry-after header                 │
│  □ Test rate limiting behavior                                          │
│ Deliverable: Rate limiting active                                       │
│ Success: 11th request returns 429                                       │
└──────────────────────────────────────────────────────────────────────────┘

FRIDAY (EVENING): Code Review + Commit

┌──────────────────────────────────────────────────────────────────────────┐
│ Task 1.7: Code Review & Commit Week 1 Work                              │
│ Actions:                                                                 │
│  □ Review all changes for:                                              │
│    - No hardcoded secrets                                               │
│    - Proper error handling                                              │
│    - Consistent code style                                              │
│    - Docstrings added                                                   │
│  □ Run full test suite: pytest tests/ -v --cov src                      │
│  □ Ensure coverage >75%                                                 │
│  □ Create PR titled: "Phase 1 Week 1: Security + State Propagation"     │
│  □ Update IMPLEMENTATION_ROADMAP.md with actual times                   │
│ Success: PR ready for review                                            │
└──────────────────────────────────────────────────────────────────────────┘

WEEK 1 SUMMARY
════════════════════════════════════════════════════════════════════════════════

✓ Security audit completed
✓ JWT authentication implemented
✓ Testing infrastructure created
✓ State propagation fixed
✓ Response schema unified
✓ Rate limiting added
✓ Tests written & passing

Metrics to Track:
  - Lines of code added: ____
  - Tests added: ____
  - Coverage improvement: __% → __%
  - Issues found (OWASP): ____
  - Issues resolved: ____

════════════════════════════════════════════════════════════════════════════════

AFTER WEEK 1: Next Steps

Move to Phase 1 Week 2:
  Task 2.1: Multi-Agent Orchestration fixes
  Task 2.2: LLM Security (prompt injection)
  Task 2.3: Error handling framework

Then Phase 2 begins immediately with testing expansion.

════════════════════════════════════════════════════════════════════════════════

USEFUL COMMANDS FOR THIS WEEK:

# Check skill is installed:
Test-Path "$env:USERPROFILE\.agents\skills\owasp-security-check\SKILL.md"

# Run tests with coverage:
python -m pytest tests/ -v --cov src --cov-report=html

# Check code style:
pip install black pylint; black src/ --check

# Run security scan locally:
pip install bandit; bandit -r api/app src/

# Start API for manual testing:
cd api && python -m uvicorn app.main:app --reload

# View auto-generated API docs:
Open browser to http://localhost:8000/docs

════════════════════════════════════════════════════════════════════════════════

DAILY STANDUP TEMPLATE (Use this each day):

Date: _______________
Standup Lead: _______

What did you complete yesterday?
[ ] _____________________________________

What are you doing today?
[ ] _____________________________________

What blockers do you have?
[ ] _____________________________________

Metrics:
  Coverage: __%
  Tests passing: __
  Errors: __

Status: 🟢 On Track / 🟡 At Risk / 🔴 Blocked
════════════════════════════════════════════════════════════════════════════════
