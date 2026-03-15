# Start Here — RagBot

Welcome to **RagBot**, a multi-agent RAG system for medical biomarker analysis.

## 5-Minute Setup

```bash
# 1. Clone and install
git clone https://github.com/yourusername/ragbot.git
cd ragbot
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. Add your free API key to .env
#    Get one at https://console.groq.com/keys (Groq, recommended)
#    or https://aistudio.google.com/app/apikey (Google Gemini)
cp .env.template .env
#    Edit .env with your key

# 3. Start chatting
python scripts/chat.py
```

For the full walkthrough, see [QUICKSTART.md](QUICKSTART.md).

---

## Key Documentation

| Document | What it covers |
|----------|----------------|
| [QUICKSTART.md](QUICKSTART.md) | Detailed setup, configuration, troubleshooting |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, agent pipeline, data flow |
| [docs/API.md](docs/API.md) | REST API endpoints and usage examples |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Extending the system — new biomarkers, agents, domains |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code style, PR process, testing guidelines |
| [scripts/README.md](scripts/README.md) | CLI scripts and utilities |
| [examples/README.md](examples/) | Web/mobile integration examples |

---

## Project at a Glance

- **6 specialist AI agents** orchestrated via LangGraph
- **24 supported biomarkers** with 80+ name aliases
- **FAISS vector store** over 750 pages of medical literature
- **Free LLM inference** via Groq (LLaMA 3.3-70B) or Google Gemini
- **Two interfaces**: interactive CLI chat + REST API (FastAPI)
- **30 unit tests** passing, Pydantic V2 throughout

---

## Quick Commands

```bash
# Interactive chat
python scripts/chat.py

# Run unit tests
.venv\Scripts\python.exe -m pytest tests/ -q ^
  --ignore=tests/test_basic.py ^
  --ignore=tests/test_diabetes_patient.py ^
  --ignore=tests/test_evolution_loop.py ^
  --ignore=tests/test_evolution_quick.py ^
  --ignore=tests/test_evaluation_system.py

# Start REST API
cd api && python -m uvicorn app.main:app --reload

# Rebuild vector store (after adding new PDFs)
python scripts/setup_embeddings.py
```

---

## Need Help?

- Check [QUICKSTART.md — Troubleshooting](QUICKSTART.md#troubleshooting)
- Open a [GitHub Issue](https://github.com/yourusername/RagBot/issues)
