---
title: Agentic RagBot
emoji: 🏥
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: true
license: mit
app_port: 7860
tags:
  - medical
  - biomarker
  - rag
  - healthcare
  - langgraph
  - agents
short_description: Multi-Agent RAG System for Medical Biomarker Analysis
---

# RagBot: Multi-Agent RAG System for Medical Biomarker Analysis

A production-ready biomarker analysis system combining 6 specialized AI agents with medical knowledge retrieval to provide evidence-based insights on blood test results in **15-25 seconds**.

## Key Features

- **6 Specialist Agents** - Biomarker validation, disease prediction, RAG-powered analysis, confidence assessment
- **Medical Knowledge Base** - 750+ pages of clinical guidelines (FAISS vector store)
- **Multiple Interfaces** - Interactive CLI chat, REST API, ready for web/mobile integration
- **Evidence-Based** - All recommendations backed by retrieved medical literature
- **Free Cloud LLMs** - Uses Groq (LLaMA 3.3-70B) or Google Gemini - no cost
- **Biomarker Normalization** - 80+ aliases mapped to 24 canonical biomarker names
- **Production-Ready** - Full error handling, safety alerts, confidence scoring, 30 unit tests

## Quick Start

**Installation (5 minutes):**

```bash
# Clone & setup
git clone https://github.com/yourusername/ragbot.git
cd ragbot
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Get free API key
# 1. Sign up: https://console.groq.com/keys
# 2. Copy API key to .env

# Run setup
python scripts/setup_embeddings.py

# Start chatting
python scripts/chat.py
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed setup instructions.

## Documentation

| Document | Purpose |
|----------|---------|
| [**QUICKSTART.md**](QUICKSTART.md) | 5-minute setup guide |
| [**CONTRIBUTING.md**](CONTRIBUTING.md) | How to contribute |
| [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) | System design & components |
| [**docs/API.md**](docs/API.md) | REST API reference |
| [**docs/DEVELOPMENT.md**](docs/DEVELOPMENT.md) | Development & extension guide |
| [**scripts/README.md**](scripts/README.md) | Utility scripts reference |
| [**examples/README.md**](examples/) | Web/mobile integration examples |

## Usage

### Interactive CLI

```bash
python scripts/chat.py

You: My glucose is 140 and HbA1c is 10

Primary Finding: Diabetes (100% confidence)
Critical Alerts: Hyperglycemia, elevated HbA1c
Recommendations: Seek medical attention, lifestyle changes
Actions: Physical activity, reduce carbs, weight loss
```

### REST API

```bash
# Start server
cd api
python -m uvicorn app.main:app

# Analyze biomarkers (structured input)
curl -X POST http://localhost:8000/api/v1/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "biomarkers": {"Glucose": 140, "HbA1c": 10.0}
  }'

# Analyze biomarkers (natural language)
curl -X POST http://localhost:8000/api/v1/analyze/natural \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My glucose is 140 and HbA1c is 10"
  }'
```

See **[docs/API.md](docs/API.md)** for full API reference.

## Project Structure

```
RagBot/
├── src/                           # Core application
│   ├── __init__.py
│   ├── workflow.py               # Multi-agent orchestration (LangGraph)
│   ├── state.py                  # Pydantic state models
│   ├── biomarker_validator.py    # Validation logic
│   ├── biomarker_normalization.py # Name normalization (80+ aliases)
│   ├── llm_config.py             # LLM/embedding provider config
│   ├── pdf_processor.py          # Vector store management
│   ├── config.py                 # Global configuration
│   └── agents/                   # 6 specialist agents
│       ├── __init__.py
│       ├── biomarker_analyzer.py
│       ├── disease_explainer.py
│       ├── biomarker_linker.py
│       ├── clinical_guidelines.py
│       ├── confidence_assessor.py
│       └── response_synthesizer.py
│
├── api/                          # REST API (FastAPI)
│   ├── app/main.py              # FastAPI server
│   ├── app/routes/              # API endpoints
│   ├── app/models/schemas.py    # Pydantic request/response schemas
│   └── app/services/            # Business logic
│
├── scripts/                      # Utilities
│   ├── chat.py                  # Interactive CLI chatbot
│   └── setup_embeddings.py      # Vector store builder
│
├── config/                       # Configuration
│   └── biomarker_references.json # 24 biomarker reference ranges
│
├── data/                         # Data storage
│   ├── medical_pdfs/            # Source documents
│   └── vector_stores/           # FAISS database
│
├── tests/                        # Test suite (30 tests)
├── examples/                     # Integration examples
├── docs/                         # Documentation
│
├── QUICKSTART.md               # Setup guide
├── CONTRIBUTING.md             # Contribution guidelines
├── requirements.txt            # Python dependencies
└── LICENSE
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | **LangGraph** | Multi-agent workflow control |
| LLM | **Groq (LLaMA 3.3-70B)** | Fast, free inference |
| LLM (Alt) | **Google Gemini 2.0 Flash** | Free alternative |
| Embeddings | **Google Gemini / HuggingFace** | Vector representations |
| Vector DB | **FAISS** | Efficient similarity search |
| API | **FastAPI** | REST endpoints |
| Validation | **Pydantic V2** | Type safety & schemas |

## How It Works

```
User Input ("My glucose is 140...")
    |
[Biomarker Extraction] -> Parse & normalize (80+ aliases)
    |
[Disease Prediction] -> Rule-based + LLM hypothesis
    |
[RAG Retrieval] -> Get medical docs from FAISS vector store
    |
[6 Agent Pipeline via LangGraph]
    |-- Biomarker Analyzer (validation + safety alerts)
    |-- Disease Explainer (RAG pathophysiology)
    |-- Biomarker-Disease Linker (RAG key drivers)
    |-- Clinical Guidelines (RAG recommendations)
    |-- Confidence Assessor (reliability scoring)
    +-- Response Synthesizer (final structured report)
    |
[Output] -> Comprehensive report with safety alerts
```

## Supported Biomarkers (24)

- **Glucose Control**: Glucose, HbA1c, Insulin
- **Lipids**: Cholesterol, LDL Cholesterol, HDL Cholesterol, Triglycerides
- **Body Metrics**: BMI
- **Blood Cells**: Hemoglobin, Platelets, White Blood Cells, Red Blood Cells, Hematocrit
- **RBC Indices**: Mean Corpuscular Volume, Mean Corpuscular Hemoglobin, MCHC
- **Cardiovascular**: Heart Rate, Systolic Blood Pressure, Diastolic Blood Pressure, Troponin
- **Inflammation**: C-reactive Protein
- **Liver**: ALT, AST
- **Kidney**: Creatinine

See [config/biomarker_references.json](config/biomarker_references.json) for full reference ranges.

## Disease Coverage

- Diabetes
- Anemia
- Heart Disease
- Thrombocytopenia
- Thalassemia
- (Extensible - add custom domains)

## Privacy & Security

- All processing runs **locally** after setup
- No personal health data stored
- Embeddings computed locally or cached
- Vector store derived from public medical literature
- Can operate completely offline with Ollama provider

## Performance

- **Response Time**: 15-25 seconds (6 agents + RAG retrieval)
- **Knowledge Base**: 750 pages, 2,609 document chunks
- **Cost**: Free (Groq/Gemini API + local/cloud embeddings)
- **Hardware**: CPU-only (no GPU needed)

## Testing

```bash
# Run unit tests (30 tests)
.venv\Scripts\python.exe -m pytest tests/ -q \
  --ignore=tests/test_basic.py \
  --ignore=tests/test_diabetes_patient.py \
  --ignore=tests/test_evolution_loop.py \
  --ignore=tests/test_evolution_quick.py \
  --ignore=tests/test_evaluation_system.py

# Run specific test file
.venv\Scripts\python.exe -m pytest tests/test_codebase_fixes.py -v

# Run all tests (includes integration tests requiring LLM API keys)
.venv\Scripts\python.exe -m pytest tests/ -v
```

## Contributing

Contributions welcome! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:
- Code style guidelines
- Pull request process
- Testing requirements
- Development setup

## Development

Want to extend RagBot?

- **Add custom biomarkers**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#adding-a-new-biomarker)
- **Add medical domains**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#adding-a-new-medical-domain)
- **Create custom agents**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#creating-a-custom-analysis-agent)
- **Switch LLM providers**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#switching-llm-providers)

## License

MIT License - See [LICENSE](LICENSE)

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Groq API Docs](https://console.groq.com)
- [FAISS GitHub](https://github.com/facebookresearch/faiss)
- [FastAPI Guide](https://fastapi.tiangolo.com/)

---

**Ready to get started?** -> [QUICKSTART.md](QUICKSTART.md)

**Want to understand the architecture?** -> [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Looking to integrate with your app?** -> [examples/README.md](examples/)
