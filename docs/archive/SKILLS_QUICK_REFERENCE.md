╔══════════════════════════════════════════════════════════════════════════════╗
║                  30 SKILLS QUICK REFERENCE CHEAT SHEET                       ║
║               RagBot Agentic RAG System - All Skills at a Glance             ║
╚══════════════════════════════════════════════════════════════════════════════╝

SKILL FINDER - FIND THE RIGHT SKILL FOR YOUR TASK
════════════════════════════════════════════════════════════════════════════════

Need help with... ?                              → Use Skill #:

✅ Building multi-agent systems                  → #3, #4, #7
✅ LangChain/LangGraph orchestration             → #1, #2, #6
✅ Better RAG retrieval (medical PDFs)           → #8, #9, #10, #11, #12
✅ Improving LLM outputs                         → #13, #16
✅ Evaluating model performance                  → #14
✅ Reducing API costs                            → #15
✅ Securing medical endpoints                    → #17, #18, #19, #20
✅ Expanding test coverage                       → #22, #24
✅ Adding API docs                               → #29
✅ Implementing PR standards                     → #30
✅ FastAPI best practices                        → #25
✅ Code organization & patterns                  → #26
✅ Logging & monitoring                          → #27
✅ Memory & context optimization                 → #28
✅ Tool/function calling patterns                → #5

════════════════════════════════════════════════════════════════════════════════

SKILLS BY STAGE OF YOUR PRODUCT
════════════════════════════════════════════════════════════════════════════════

CURRENT: Early-stage production
┌─ Security: Critical (#17, #18, #19, #20)
├─ Architecture: Foundation (#1, #2, #3)  
├─ Testing: Baseline (#22)
└─ Docs: Basic (#29)

PHASE 1 (This Month): Harden & Fix
┌─ Security audit: #18
├─ Fix state: #2, #3
├─ Unify schema: #16
├─ Expand tests: #22
├─ Setup CI/CD: #24
└─ Time: 2-4 weeks

PHASE 2 (Month 2): Advance Agents
┌─ Agent patterns: #4, #5, #6, #7
├─ Prompt engineering: #13, #14
├─ Function calling: #5
├─ Memory optimization: #28
└─ Time: 2-4 weeks

PHASE 3 (Month 3): Optimize Retrieval
┌─ Hybrid search: #8
├─ Chunking: #9
├─ Embeddings: #10
├─ Knowledge graphs: #12
├─ Citations: #11
└─ Time: 2-4 weeks

PHASE 4 (Month 4): Scale & Deploy
┌─ Cost optimization: #15
├─ Design patterns: #26
├─ Observability: #27
├─ FastAPI: #25
├─ API docs: #29
├─ PR workflow: #30
└─ Time: 2-4 weeks

════════════════════════════════════════════════════════════════════════════════

INSTALL SKILL REFERENCE
════════════════════════════════════════════════════════════════════════════════

All skills already installed globally. To reinstall or access:

# List all installed
npx skills list

# Check for updates
npx skills check

# Update all
npx skills update

# View skill documentation
cat ~/.agents/skills/[skill-name]/SKILL.md
cat ~/.agents/skills/langchain-architecture/SKILL.md
cat ~/.agents/skills/api-security-hardening/SKILL.md
# etc.

════════════════════════════════════════════════════════════════════════════════

SKILLS INSTALLATION MANIFEST
════════════════════════════════════════════════════════════════════════════════

Agent & Orchestration Stack (7):
  [✅] LangChain Architecture
  [✅] Workflow Orchestration Patterns
  [✅] Multi-Agent Orchestration
  [✅] Agentic Development
  [✅] Tool/Function Calling Patterns
  [✅] LLM Application Dev with LangChain
  [✅] RAG Agent Builder

Search & Retrieval Stack (5):
  [✅] Hybrid Search Implementation
  [✅] Chunking Strategy
  [✅] Embedding Pipeline Builder
  [✅] RAG Implementation
  [✅] Knowledge Graph Builder

LLM & Prompt Stack (4):
  [✅] Senior Prompt Engineer (320 installs!)
  [✅] LLM Evaluation
  [✅] Cost-Aware LLM Pipeline
  [✅] AI Wrapper/Structured Output (252 installs!)

Security Stack (5):
  [✅] API Security Hardening
  [✅] OWASP Security Check
  [✅] LLM Security
  [✅] API Rate Limiting
  [✅] Python Error Handling

Quality & Testing Stack (3):
  [✅] Python Testing Patterns (3.7K installs!)
  [✅] Code Review Excellence
  [✅] GitHub Actions Templates (2.8K installs!)

Infrastructure Stack (4):
  [✅] FastAPI Templates
  [✅] Python Design Patterns
  [✅] Python Observability
  [✅] Memory Management

Documentation & Collaboration (2):
  [✅] API Docs Generator
  [✅] GitHub PR Review Workflow

════════════════════════════════════════════════════════════════════════════════

YOUR CRITICAL ISSUES → SKILLS MAPPING
════════════════════════════════════════════════════════════════════════════════

Issue: biomarker_flags & safety_alerts not in workflow output
Skills: #2 (Workflow Orchestration) + #3 (Multi-Agent) + #16 (Structured Output)
Action: Refactor state.py, ensure all agents return required fields
Timeline: Week 1

Issue: Schema mismatch between workflow and API formatter  
Skills: #16 (Structured Output) + #4 (Agentic Development) + #25 (FastAPI)
Action: Unify response format, use Pydantic validation
Timeline: Week 2

Issue: Forced confidence & default disease (dangerous!)
Skills: #13 (Prompt Engineer) + #14 (LLM Evaluation) + #22 (Testing)
Action: Remove forced minimums, add confidence range handling
Timeline: Week 2

Issue: Different biomarker naming (API vs CLI)
Skills: #16 (Structured Output) + #9 (Chunking) + #22 (Testing)
Action: Centralize normalization, parametrize tests
Timeline: Week 3

Issue: JSON parsing fragility from LLMs
Skills: #16 (Structured Output) + #5 (Function Calling) + #14 (Evaluation)
Action: Use structured outputs/function calling, add repair step
Timeline: Week 3

Issue: No citation enforcement in RAG
Skills: #11 (RAG Implementation) + #12 (Knowledge Graphs) + #8 (Hybrid Search)
Action: Track sources per claim, fail without citations
Timeline: Week 4

════════════════════════════════════════════════════════════════════════════════

TOP 5 PRIORITY SKILLS TO START WITH NOW
════════════════════════════════════════════════════════════════════════════════

1️⃣ OWASP Security Check (#18)
   └─ Why: Medical data protection is non-negotiable
   └─ Time: 1-2 hours for initial scan
   └─ First action: Run the security audit today

2️⃣ Workflow Orchestration Patterns (#2)
   └─ Why: Fixes your critical state propagation issue
   └─ Time: 3-5 hours to refactor GuildState
   └─ First action: Read the skill, identify missing state fields

3️⃣ AI Wrapper/Structured Output (#16)
   └─ Why: Solves schema mismatch, enables reliable parsing
   └─ Time: 2-3 hours to implement
   └─ First action: Define unified response schema with Pydantic

4️⃣ Python Testing Patterns (#22)
   └─ Why: Go from 83 to 150+ tests, improve confidence
   └─ Time: 1-2 weeks (ongoing)
   └─ First action: Create parametrized biomarker test suite

5️⃣ Senior Prompt Engineer (#13)
   └─ Why: Improve LLM accuracy for medical domain
   └─ Time: 1-2 hours for initial optimization
   └─ First action: Audit current agent prompts, identify improvements

════════════════════════════════════════════════════════════════════════════════

POPULAR SKILLS (BY INSTALL COUNT)
════════════════════════════════════════════════════════════════════════════════

320+ installs: Senior Prompt Engineer (#13) ⭐⭐⭐
252 installs:   AI Wrapper/Structured Output (#16) ⭐⭐⭐
2.8K installs:  GitHub Actions Templates (#24) ⭐⭐⭐
3.7K installs:  Python Testing Patterns (#22) ⭐⭐⭐
2.3K installs:  LangChain Architecture (#1) ⭐⭐⭐
2K installs:    Workflow Orchestration (#2) ⭐⭐⭐
1.7K installs:  Hybrid Search (#8) ⭐⭐⭐

These are proven implementations - very likely to help!

════════════════════════════════════════════════════════════════════════════════

AVOID THESE MISTAKES
════════════════════════════════════════════════════════════════════════════════

❌ Don't skip security (#17, #18, #19, #20)
   └─ Medical data requires HIPAA compliance

❌ Don't ignore state management (#2, #3)
   └─ Your parallel agents have race conditions

❌ Don't use unstructured LLM output (#16)
   └─ JSON parsing will break in production

❌ Don't have <90% test coverage (#22) for medical app
   └─ Errors have real consequences for patients

❌ Don't force disease predictions when uncertain
   └─ Better to say "inconclusive" than wrong diagnosis

❌ Don't retrieve without citations (#11)
   └─ Hallucinations + medical = liability

════════════════════════════════════════════════════════════════════════════════

RECOMMENDED READING ORDER
════════════════════════════════════════════════════════════════════════════════

Today (30 min):
  1. OWASP Security Check - run the scan
  
This week (2-3 hours):
  2. Workflow Orchestration Patterns - understand LangGraph
  3. AI Wrapper/Structured Output - unify your response format
  
Next week (4-6 hours):
  4. Hybrid Search Implementation - improve medical retrieval
  5. Python Testing Patterns - expand test suite
  
Then ongoing:
  6. Senior Prompt Engineer - iteratively improve prompts
  7. LLM Evaluation - benchmark your improvements
  8. All others as you progress through 4-month roadmap

════════════════════════════════════════════════════════════════════════════════

ESTIMATED EFFORT & IMPACT
════════════════════════════════════════════════════════════════════════════════

Skill                          Effort    Impact      Priority
─────────────────────────────────────────────────────────────
OWASP Security Check          2-3h      Critical    🔴
Workflow Orchestration         5-8h      Critical    🔴  
AI Wrapper/Output              3-5h      Critical    🔴
Hybrid Search                  4-6h      High        🟠
Python Testing Patterns        20-30h    High        🟠
Senior Prompt Engineer         2-3h      High        🟠
LLM Evaluation                 3-4h      High        🟠
API Security Hardening         4-6h      High        🟠
LangChain Architecture         5-8h      Medium      🟡
Cost-Aware Pipeline            3-4h      Medium      🟡
Knowledge Graph Builder        6-8h      Medium      🟡
Chunking Strategy              2-3h      Medium      🟡
Embedding Pipeline             3-4h      Medium      🟡
FastAPI Templates              2-3h      Medium      🟡
Python Observability           3-4h      Medium      🟡
Others...                      1-3h      Low         ⚪

════════════════════════════════════════════════════════════════════════════════

QUICK COMMAND REFERENCE
════════════════════════════════════════════════════════════════════════════════

# View a skill documentation
cat ~/.agents/skills/api-security-hardening/SKILL.md

# List all 30 skills
ls ~/.agents/skills/

# Check skill details
head -20 ~/.agents/skills/owasp-security-check/SKILL.md

# Get skills help
npx skills --help

════════════════════════════════════════════════════════════════════════════════

FINAL NOTES
════════════════════════════════════════════════════════════════════════════════

🚀 You now have 30 world-class AI/RAG development skills
💪 Your next 4 months of work is mapped out in COMPREHENSIVE_SKILLS_GUIDE.md
🔒 Medical-grade security pathways defined
🧪 Enterprise testing frameworks ready
📊 Industry-standard patterns available

Your RagBot will transform from "working production system" to 
"industry-leading medical AI" through systematic skill application.

Start TODAY with OWASP Security Scan. Get momentum. Build iteratively.

════════════════════════════════════════════════════════════════════════════════
Master these skills. Master the medical AI space. 🏆
════════════════════════════════════════════════════════════════════════════════
