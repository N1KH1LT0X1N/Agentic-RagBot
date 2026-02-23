# RagBot Development Guide

## For Developers & Maintainers

This guide covers extending, customizing, and contributing to RagBot.

## Project Structure

```
RagBot/
├── src/                          # Core application code
│   ├── __init__.py              # Package marker
│   ├── workflow.py              # Multi-agent workflow orchestration
│   ├── state.py                 # Pydantic data models & state
│   ├── biomarker_validator.py   # Biomarker validation logic
│   ├── biomarker_normalization.py # Alias-to-canonical name mapping (80+ aliases)
│   ├── llm_config.py            # LLM & embedding configuration
│   ├── pdf_processor.py         # PDF loading & vector store
│   ├── config.py                # Global configuration
│   │
│   ├── agents/                  # Specialist agents
│   │   ├── __init__.py                 # Package marker
│   │   ├── biomarker_analyzer.py       # Validates biomarkers
│   │   ├── disease_explainer.py        # Explains disease (RAG)
│   │   ├── biomarker_linker.py         # Links biomarkers to disease (RAG)
│   │   ├── clinical_guidelines.py      # Provides guidelines (RAG)
│   │   ├── confidence_assessor.py      # Assesses prediction confidence
│   │   └── response_synthesizer.py     # Synthesizes findings
│   │
│   ├── evaluation/               # Evaluation framework
│   │   ├── __init__.py
│   │   └── evaluators.py         # Quality evaluators
│   │
│   └── evolution/                # Experimental components
│       ├── __init__.py
│       ├── director.py           # Evolution orchestration
│       └── pareto.py             # Pareto optimization
│
├── api/                          # REST API application
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── routes/              # API endpoints
│   │   │   ├── analyze.py       # Main analysis endpoint
│   │   │   ├── biomarkers.py    # Biomarker endpoints
│   │   │   └── health.py        # Health check
│   │   ├── models/              # Pydantic schemas
│   │   └── services/            # Business logic
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/                      # Utility & demo scripts
│   ├── chat.py                  # Interactive CLI
│   ├── setup_embeddings.py      # Vector store builder
│   ├── run_api.ps1              # API startup script
│   └── ...
│
├── config/                       # Configuration files
│   └── biomarker_references.json # Biomarker reference ranges
│
├── data/                         # Data storage
│   ├── medical_pdfs/            # Source medical documents
│   └── vector_stores/           # FAISS vector databases
│
├── tests/                        # Test suite
│   └── test_*.py
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md          # System design
│   ├── API.md                   # API reference
│   ├── DEVELOPMENT.md           # This file
│   └── ...
│
├── examples/                     # Example integrations
│   ├── test_website.html        # Web integration example
│   └── website_integration.js   # JavaScript client
│
├── requirements.txt             # Python dependencies
├── README.md                    # Main documentation
├── QUICKSTART.md                # Setup guide
├── CONTRIBUTING.md              # Contribution guidelines
└── LICENSE
```

## Development Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/ragbot.git
cd ragbot
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.template .env
# Edit .env with your API keys (Groq, Google, etc.)
```

### 3. Rebuild Vector Store

```bash
python scripts/setup_embeddings.py
```

### 4. Run Tests

```bash
pytest tests/
```

## Key Development Tasks

### Adding a New Biomarker

**Step 1:** Update reference ranges in `config/biomarker_references.json`:

```json
{
  "biomarkers": {
    "New Biomarker": {
      "min": 0,
      "max": 100,
      "unit": "mg/dL",
      "normal_range": "0-100",
      "critical_low": -1,
      "critical_high": 150,
      "related_conditions": ["Disease1", "Disease2"]
    }
  }
}
```

**Step 2:** Add aliases in `src/biomarker_normalization.py`:

```python
NORMALIZATION_MAP = {
    # ... existing entries ...
    "your alias": "New Biomarker",
    "other name": "New Biomarker",
}
```

All consumers (CLI, API, workflow) use this shared map automatically.

**Step 3:** Add validation test in `tests/test_basic.py`:

```python
def test_new_biomarker():
    validator = BiomarkerValidator()
    result = validator.validate("New Biomarker", 50)
    assert result.is_valid
```

**Step 4:** Medical knowledge automatically updates through RAG

### Adding a New Medical Domain

**Step 1:** Collect relevant PDFs:
```
data/medical_pdfs/
  your_domain.pdf
  your_guideline.pdf
```

**Step 2:** Rebuild vector store:
```bash
python scripts/setup_embeddings.py
```

The system automatically:
- Loads all PDFs from `data/medical_pdfs/`
- Creates 2,609+ chunks with similarity search
- Makes knowledge available to all RAG agents

**Step 3:** Test with new biomarkers from that domain:
```bash
python scripts/chat.py
# Input: biomarkers related to your domain
```

### Creating a Custom Analysis Agent

**Example: Add a "Medication Interactions" Agent**

**Step 1:** Create `src/agents/medication_checker.py`:

```python
from src.llm_config import LLMConfig
from src.state import PatientInput

class MedicationChecker:
    def __init__(self):
        config = LLMConfig()
        self.llm = config.analyzer  # Uses centralized LLM config
    
    def check_interactions(self, state: PatientInput) -> dict:
        """Check medication interactions based on biomarkers."""
        # Get relevant medical knowledge
        # Use LLM to identify drug-drug interactions
        # Return structured response
        return {
            "interactions": [],
            "warnings": [],
            "recommendations": []
        }
```

**Step 2:** Register in workflow (`src/workflow.py`):

```python
from src.agents.medication_checker import MedicationChecker

medication_agent = MedicationChecker()

def check_medications(state):
    return medication_agent.check_interactions(state)

# Add to graph
graph.add_node("MedicationChecker", check_medications)
graph.add_edge("ClinicalGuidelines", "MedicationChecker")
graph.add_edge("MedicationChecker", "ResponseSynthesizer")
```

**Step 3:** Update synthesizer to include medication info:

```python
# In response_synthesizer.py
medication_info = state.get("medication_interactions", {})
```

### Switching LLM Providers

RagBot supports three LLM providers out of the box. Set via `LLM_PROVIDER` in `.env`:

| Provider | Model | Cost | Speed |
|----------|-------|------|-------|
| `groq` (default) | llama-3.3-70b-versatile | Free | Fast |
| `gemini` | gemini-2.0-flash | Free | Medium |
| `ollama` | configurable | Free (local) | Varies |

```bash
# .env
LLM_PROVIDER="groq"
GROQ_API_KEY="gsk_..."

# Or
LLM_PROVIDER="gemini"
GOOGLE_API_KEY="..."
```

No code changes needed — `src/llm_config.py` handles provider selection automatically.

### Modifying Embedding Provider

**Current default:** Google Gemini (`models/embedding-001`, free)  
**Fallback:** HuggingFace sentence-transformers (local, no API key needed)  
**Optional:** Ollama (local)

Set via `EMBEDDING_PROVIDER` in `.env`:
```bash
EMBEDDING_PROVIDER="google"    # Default - Google Gemini
EMBEDDING_PROVIDER="huggingface"  # Fallback - local
EMBEDDING_PROVIDER="ollama"    # Local Ollama
```

After changing, rebuild the vector store:
```bash
python scripts/setup_embeddings.py
```

⚠️ **Note:** Changing embeddings requires rebuilding the vector store (dimensions must match).

## Testing

### Run All Tests

```bash
.venv\Scripts\python.exe -m pytest tests/ -q --ignore=tests/test_basic.py --ignore=tests/test_diabetes_patient.py --ignore=tests/test_evolution_loop.py --ignore=tests/test_evolution_quick.py --ignore=tests/test_evaluation_system.py
```

### Run Specific Test

```bash
.venv\Scripts\python.exe -m pytest tests/test_normalization.py -v
```

### Test Coverage

```bash
.venv\Scripts\python.exe -m pytest --cov=src tests/
```

### Add New Tests

Create `tests/test_myfeature.py`:

```python
import pytest
from src.biomarker_validator import BiomarkerValidator

class TestMyFeature:
    def setup_method(self):
        self.validator = BiomarkerValidator()
    
    def test_validation(self):
        result = self.validator.validate("Glucose", 140)
        assert result.is_valid == False
        assert result.status == "out-of-range"
```

## Debugging

### Enable Debug Logging

Set in `.env`:
```
LOG_LEVEL=DEBUG
```

### Interactive Debugging

```bash
python -c "
from src.workflow import create_guild

# Create the guild
guild = create_guild()

# Run workflow
result = guild.run({
    'biomarkers': {'Glucose': 185, 'HbA1c': 8.2},
    'model_prediction': {'disease': 'Diabetes', 'confidence': 0.87}
})

# Inspect result
print(result)
"
```

### Profile Performance

```bash
python -m cProfile -s cumtime scripts/chat.py
```

## Code Quality

### Format Code

```bash
black src/ api/ scripts/
```

### Check Types

```bash
mypy src/ --ignore-missing-imports
```

### Lint

```bash
pylint src/ api/ scripts/
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
black src/ api/ scripts/
pytest tests/
```

## Documentation

- Update `docs/` when adding features
- Keep README.md in sync with changes
- Document all new functions with docstrings:

```python
def analyze_biomarker(name: str, value: float) -> dict:
    """
    Analyze a single biomarker value.
    
    Args:
        name: Biomarker name (e.g., "Glucose")
        value: Measured value
    
    Returns:
        dict: Analysis result with status, alerts, recommendations
    
    Raises:
        ValueError: If biomarker name is invalid
    """
```

## Performance Optimization

### Profile Agent Execution

```python
import time

start = time.time()
result = agent.run(state)
elapsed = time.time() - start
print(f"Agent took {elapsed:.2f}s")
```

### Parallel Agent Execution

Agents already run in parallel via LangGraph:
- Agent 1: Biomarker Analyzer
- Agents 2-4: RAG agents (parallel)
- Agent 5: Confidence Assessor
- Agent 6: Synthesizer

Modify in `src/workflow.py` if needed.

### Cache Embeddings

FAISS vector store is already loaded once at startup.

### Reduce Processing Time

- Fewer RAG docs: Modify `k=5` in agent prompts
- Simpler LLM: Use smaller model or quantized version
- Batch requests: Process multiple patients at once

## Troubleshooting

### Issue: Vector store not found

```bash
.venv\Scripts\python.exe scripts/setup_embeddings.py
```

### Issue: LLM provider not responding

- Check your `.env` has valid API keys (`GROQ_API_KEY` or `GOOGLE_API_KEY`)
- Verify internet connection
- Check provider status pages (Groq Console, Google AI Studio)

### Issue: Slow inference

- Check Groq API status
- Verify internet connection
- Try smaller model or batch requests

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Code style guidelines
- Pull request process
- Issue reporting
- Testing requirements

## Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Documentation: See `/docs`

## Resources

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [Groq API Docs](https://console.groq.com)
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [FastAPI Guide](https://fastapi.tiangolo.com/)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
