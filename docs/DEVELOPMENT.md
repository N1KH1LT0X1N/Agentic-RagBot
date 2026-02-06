# RagBot Development Guide

## For Developers & Maintainers

This guide covers extending, customizing, and contributing to RagBot.

## Project Structure

```
RagBot/
├── src/                          # Core application code
│   ├── workflow.py              # Multi-agent workflow orchestration
│   ├── state.py                 # Pydantic data models & state
│   ├── biomarker_validator.py   # Biomarker validation logic
│   ├── llm_config.py            # LLM & embedding configuration
│   ├── pdf_processor.py         # PDF loading & vector store
│   ├── config.py                # Global configuration
│   │
│   ├── agents/                  # Specialist agents
│   │   ├── biomarker_analyzer.py       # Validates biomarkers
│   │   ├── disease_explainer.py        # Explains disease (RAG)
│   │   ├── biomarker_linker.py         # Links biomarkers to disease (RAG)
│   │   ├── clinical_guidelines.py      # Provides guidelines (RAG)
│   │   ├── confidence_assessor.py      # Assesses prediction confidence
│   │   └── response_synthesizer.py     # Synthesizes findings
│   │
│   └── evolution/                # Experimental components
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

**Step 2:** Update name normalization in `scripts/chat.py`:

```python
def normalize_biomarker_name(name: str) -> str:
    mapping = {
        "your alias": "New Biomarker",
        "other name": "New Biomarker",
    }
    return mapping.get(name.lower(), name)
```

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
from langchain.agents import Tool
from langchain.llms import Groq
from src.state import PatientInput, DiseasePrediction

class MedicationChecker:
    def __init__(self):
        self.llm = Groq(model="llama-3.3-70b")
    
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

**Current:** Groq LLaMA 3.3-70B (free, fast)

**To use OpenAI GPT-4:**

1. Update `src/llm_config.py`:
```python
from langchain_openai import ChatOpenAI

def create_llm():
    return ChatOpenAI(
        model="gpt-4",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.1
    )
```

2. Update `requirements.txt`:
```
langchain-openai>=0.1.0
```

3. Test:
```bash
python scripts/chat.py
```

### Modifying Embedding Model

**Current:** HuggingFace sentence-transformers (free, local)

**To use OpenAI Embeddings:**

1. Update `src/pdf_processor.py`:
```python
from langchain_openai import OpenAIEmbeddings

def get_embedding_model():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY")
    )
```

2. Rebuild vector store:
```bash
python scripts/setup_embeddings.py --force-rebuild
```

⚠️ **Note:** Changing embeddings requires rebuilding the vector store (dimensions must match).

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_diabetes_patient.py -v
```

### Test Coverage

```bash
pytest --cov=src tests/
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
from src.workflow import create_workflow
from src.state import PatientInput

# Create test input
input_data = PatientInput(...)

# Run workflow
workflow = create_workflow()
result = workflow.invoke(input_data)

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

### Issue: "ModuleNotFoundError: No module named 'torch'"

```bash
pip install torch torchvision
```

### Issue: "CUDA out of memory"

```bash
export CUDA_VISIBLE_DEVICES=-1  # Use CPU
python scripts/chat.py
```

### Issue: Vector store not found

```bash
python scripts/setup_embeddings.py
```

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
