# RagBot: Multi-Agent RAG System for Medical Biomarker Analysis

A production-ready biomarker analysis system combining 6 specialized AI agents with medical knowledge retrieval to provide evidence-based insights on blood test results in **15-25 seconds**.

## ✨ Key Features

- **6 Specialist Agents** - Biomarker validation, disease prediction, RAG-powered analysis, confidence assessment
- **Medical Knowledge Base** - 750+ pages of clinical guidelines (FAISS vector store, local embeddings)
- **Multiple Interfaces** - Interactive CLI chat, REST API, ready for web/mobile integration
- **Evidence-Based** - All recommendations backed by retrieved medical literature
- **Free & Offline** - Uses free Groq API + local embeddings (no embedding API costs)
- **Production-Ready** - Full error handling, safety alerts, confidence scoring

## 🚀 Quick Start

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

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [**QUICKSTART.md**](QUICKSTART.md) | 5-minute setup guide |
| [**CONTRIBUTING.md**](CONTRIBUTING.md) | How to contribute |
| [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) | System design & components |
| [**docs/API.md**](docs/API.md) | REST API reference |
| [**docs/DEVELOPMENT.md**](docs/DEVELOPMENT.md) | Development & extension guide |
| [**scripts/README.md**](scripts/README.md) | Utility scripts reference |
| [**examples/README.md**](examples/) | Web/mobile integration examples |

## 💻 Usage

### Interactive CLI

```bash
python scripts/chat.py

You: My glucose is 140 and HbA1c is 10

🔴 Primary Finding: Diabetes (85% confidence)
⚠️ Critical Alerts: Hyperglycemia, elevated HbA1c
✅ Recommendations: Seek medical attention, lifestyle changes
🌱 Actions: Physical activity, reduce carbs, weight loss
```

### REST API

```bash
# Start server
python -m uvicorn api.app.main:app

# POST /api/v1/analyze
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "biomarkers": {"Glucose": 140, "HbA1c": 10.0}
  }'
```

See **[docs/API.md](docs/API.md)** for full API reference.

## 🏗️ Project Structure

```
RagBot/
├── src/                           # Core application
│   ├── workflow.py               # Multi-agent orchestration (LangGraph)
│   ├── biomarker_validator.py    # Validation logic
│   ├── pdf_processor.py          # Vector store management
│   └── agents/                   # 6 specialist agents
│
├── api/                          # REST API (optional)
│   ├── app/main.py              # FastAPI server
│   └── app/routes/              # API endpoints
│
├── scripts/                      # Utilities
│   ├── chat.py                  # Interactive CLI
│   └── setup_embeddings.py      # Vector store builder
│
├── config/                       # Configuration
│   └── biomarker_references.json # Reference ranges
│
├── data/                         # Data storage
│   ├── medical_pdfs/            # Source documents
│   └── vector_stores/           # FAISS database
│
├── tests/                        # Test suite
├── examples/                     # Integration examples
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md          # System design
│   ├── API.md                   # API reference
│   ├── DEVELOPMENT.md           # Development guide
│   ├── archive/                 # Old docs
│   └── plans/                   # Planning docs
│
├── QUICKSTART.md               # Setup guide
├── CONTRIBUTING.md             # Contribution guidelines
├── requirements.txt            # Python dependencies
├── .env.template              # Configuration template
└── LICENSE
```

## 🔧 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | **LangGraph** | Multi-agent workflow control |
| LLM | **Groq (LLaMA 3.3-70B)** | Fast, free inference |
| Embeddings | **HuggingFace (sentence-transformers)** | Local, offline embeddings |
| Vector DB | **FAISS** | Efficient similarity search |
| API | **FastAPI** | REST endpoints |
| Data | **Pydantic V2** | Type validation |

## 🔍 How It Works

```
User Input ("My glucose is 140...")
    ↓
[Biomarker Extraction] → Parse & normalize
    ↓
[Prediction Agent] → Disease hypothesis
    ↓
[RAG Retrieval] → Get medical docs from vector store
    ↓
[6 Parallel Agents] → Analyze from different angles
    ├─ Biomarker Analyzer (validation)
    ├─ Disease Explainer (RAG)
    ├─ Biomarker-Disease Linker (RAG)
    ├─ Clinical Guidelines (RAG)
    ├─ Confidence Assessor (scoring)
    └─ Response Synthesizer (summary)
    ↓
[Output] → Comprehensive report with safety alerts
```

## 📊 Supported Biomarkers

24+ biomarkers including:
- **Glucose Control**: Glucose, HbA1c, Fasting Glucose
- **Lipids**: Total Cholesterol, LDL, HDL, Triglycerides
- **Cardiac**: Troponin, BNP, CK-MB
- **Blood Cells**: WBC, RBC, Hemoglobin, Hematocrit, Platelets
- **Liver**: ALT, AST, Albumin, Bilirubin
- **Kidney**: Creatinine, BUN, eGFR
- And more...

See `config/biomarker_references.json` for complete list.

## 🎯 Disease Coverage

- Diabetes
- Anemia
- Heart Disease
- Thrombocytopenia
- Thalassemia
- (Extensible - add custom domains)

## 🔒 Privacy & Security

- All processing runs **locally** after setup
- No personal health data sent to APIs (except LLM inference)
- Embeddings computed locally or cached
- Fully **HIPAA-compliant** architecture ready
- Vector store derived from public medical literature
- Can operate completely offline after initial setup

## 📈 Performance

- **Response Time**: 15-25 seconds (8 agents + RAG retrieval)
- **Knowledge Base**: 750 pages → 2,609 document chunks
- **Embedding Dimensions**: 384
- **Cost**: Free (Groq API + local embeddings)
- **Hardware**: CPU-only (no GPU needed)

## 🚀 Deployment Options

1. **CLI** - Interactive chatbot (development/testing)
2. **REST API** - FastAPI server (production)
3. **Docker** - Containerized deployment
4. **Embedded** - Direct Python library import
5. **Web** - JavaScript/React integration
6. **Mobile** - React Native / Flutter

See **[examples/README.md](examples/)** for integration patterns.

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific module
pytest tests/test_diabetes_patient.py -v

# Coverage report
pytest --cov=src tests/
```

## 🤝 Contributing

Contributions welcome! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:
- Code style guidelines
- Pull request process
- Testing requirements
- Development setup

## 📖 Development

Want to extend RagBot?

- **Add custom biomarkers**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#adding-a-new-biomarker)
- **Add medical domains**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#adding-a-new-medical-domain)
- **Create custom agents**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#creating-a-custom-analysis-agent)
- **Switch LLM providers**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#switching-llm-providers)

## 📋 License

MIT License - See [LICENSE](LICENSE)

## 🙋 Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Discussion**: GitHub Discussions for questions
- **Docs**: Full documentation in `/docs` folder

## 🔗 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Groq API Docs](https://console.groq.com)
- [FAISS GitHub](https://github.com/facebookresearch/faiss)
- [FastAPI Guide](https://fastapi.tiangolo.com/)

---

**Ready to get started?** → [QUICKSTART.md](QUICKSTART.md)

**Want to understand the architecture?** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Looking to integrate with your app?** → [examples/README.md](examples/)
