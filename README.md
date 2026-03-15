# MediGuard AI: Multi-Agent RAG System for Medical Biomarker Analysis

[![Tests](https://img.shields.io/badge/tests-148%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-58%25-yellow)](tests/)
[![Security](https://img.shields.io/badge/security-passing-brightgreen)](src/)
[![Code Quality](https://img.shields.io/badge/code%20quality-passing-brightgreen)](src/)

> **⚠️ Disclaimer:** This is an AI-assisted analysis tool, NOT a medical device. Always consult healthcare professionals for medical decisions.

A production-ready biomarker analysis system combining 6 specialized AI agents with medical knowledge retrieval (RAG) to provide evidence-based insights on blood test results.

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- 8GB+ RAM
- Ollama (for local LLM) or Groq API key

### Installation (5 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/Agentic-RagBot.git
cd Agentic-RagBot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy .env.example to .env)
cp .env.example .env
# Edit .env with your API keys

# Initialize embeddings
python scripts/setup_embeddings.py

# Start the application
python -m src.main
```

### Docker Alternative

```bash
# Build and run with Docker
docker build -t mediguard-ai .
docker run -p 8000:8000 -p 7860:7860 mediguard-ai
```

## 🏗️ Architecture

### Multi-Agent Workflow

```
Input → Validation → ┌─────────────────────────────────┐ → Output
                    │     6 Specialist Agents        │
                    ├─────────────────────────────────┤
                    │ • Biomarker Analyzer            │
                    │ • Disease Explainer            │
                    │ • Biomarker Linker             │
                    │ • Clinical Guidelines Agent    │
                    │ • Confidence Assessor          │
                    │ • Response Synthesizer         │
                    └─────────────────────────────────┘
```

### Key Components

- **Agents**: 6 specialized AI agents for different analysis aspects
- **Knowledge Base**: Medical literature in vector database (FAISS/OpenSearch)
- **State Management**: LangGraph for workflow orchestration
- **API Layer**: FastAPI with async support
- **Web UI**: Gradio interface for interactive use

## 📊 Features

- **🧬 Biomarker Analysis**: Analyzes 80+ biomarker aliases mapped to 24 canonical names
- **🎯 Disease Scoring**: Rule-based heuristics for 5 major conditions
- **📚 Evidence-Based**: All recommendations backed by medical literature
- **🔒 HIPAA Compliant**: Audit logging and security headers
- **🚀 Production Ready**: Error handling, monitoring, and scalability
- **🔧 Configurable**: Environment-based configuration
- **📖 Multiple Interfaces**: CLI, REST API, and Web UI

## 🎯 Disease Detection

The system uses rule-based heuristics to score disease likelihood:

| Disease | Key Indicators | Threshold |
|---------|----------------|-----------|
| Diabetes | Glucose, HbA1c | Glucose > 126, HbA1c ≥ 6.5 |
| Anemia | Hemoglobin, MCV | Hgb < 12, MCV < 80 |
| Heart Disease | Cholesterol, Troponin | Chol > 240, Troponin > 0.04 |
| Thrombocytopenia | Platelets | Platelets < 150,000 |
| Thalassemia | MCV + Hgb pattern | MCV < 80 + Hgb < 12 |

## 🛠️ Usage

### REST API

```bash
# Start the server
uvicorn src.main:app --reload

# Analyze biomarkers
curl -X POST http://localhost:8000/analyze/structured \\
  -H "Content-Type: application/json" \\
  -d '{"biomarkers": {"Glucose": 140, "HbA1c": 10.0}}'

# Ask medical questions
curl -X POST http://localhost:8000/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question": "What does high HbA1c mean?"}'
```

### Python SDK

```python
from src.workflow import create_guild
from src.state import PatientInput

# Create workflow
guild = create_guild()

# Analyze patient data
patient_input = PatientInput(
    biomarkers={"Glucose": 140, "HbA1c": 10.0},
    patient_context={"age": 45, "gender": "male"},
    model_prediction={"disease": "Diabetes", "confidence": 0.9}
)

result = guild.run(patient_input)
print(result["final_response"])
```

### Web Interface

```bash
# Launch Gradio UI
python -m src.gradio_app
# Visit http://localhost:7860
```

## 📁 Project Structure

```
Agentic-RagBot/
├── src/
│   ├── agents/          # Agent implementations
│   ├── services/        # Core services (retrieval, embeddings)
│   ├── routers/         # FastAPI endpoints
│   ├── models/          # Data models
│   ├── state.py         # State management
│   ├── workflow.py      # Workflow orchestration
│   └── main.py          # Application entry point
├── tests/               # Test suite (58% coverage)
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── data/                # Data files
└── docker/              # Docker configurations
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test suites
pytest tests/test_agents.py
pytest tests/test_workflow.py
```

## 🔧 Configuration

Key environment variables:

```bash
# API Configuration
API__HOST=127.0.0.1
API__PORT=8000

# LLM Configuration
GROQ_API_KEY=your_groq_key
# or
OLLAMA_BASE_URL=http://localhost:11434

# Database
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# Cache
REDIS_URL=redis://localhost:6379
```

## 📈 Performance

- **Response Time**: < 2 seconds for typical analysis
- **Throughput**: 100+ concurrent requests
- **Memory Usage**: ~2GB base + embeddings
- **Test Coverage**: 58% (148 passing tests)

## 🔒 Security

- HIPAA-compliant audit logging
- Security headers middleware
- Input validation and sanitization
- No hardcoded secrets
- Regular security scans (Bandit)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Medical literature from NIH and WHO
- LangChain and LangGraph for agent framework
- FAISS for vector similarity search
- FastAPI for web framework

## 📞 Support

- 📧 Email: support@mediguard-ai.com
- 📖 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/Agentic-RagBot/issues)

---

**⚡ Ready to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment guide.
