# Scripts Directory

Utility scripts for setup, testing, and interaction with RagBot.

## Core Scripts

### `chat.py` - Interactive CLI Interface
Interactive command-line chatbot for analyzing blood test results.

**Usage:**
```bash
python scripts/chat.py
```

**Features:**
- Interactive prompt for biomarker input
- Example case loading (`example` command)
- Biomarker help reference (`help` command)
- Report saving (automatic JSON export)
- Real-time analysis with all 6 agents

**Example input:**
```
You: My glucose is 140 and HbA1c is 10
```

---

### `setup_embeddings.py` - Vector Store Builder
Builds or rebuilds the FAISS vector store from medical PDFs.

**Usage:**
```bash
# Build/update vector store
python scripts/setup_embeddings.py

# Force complete rebuild
python scripts/setup_embeddings.py --force-rebuild
```

**What it does:**
- Loads all PDFs from `data/medical_pdfs/`
- Chunks documents (1000 char with 200 overlap)
- Generates embeddings (HuggingFace, local)
- Creates FAISS vector database
- Saves to `data/vector_stores/medical_knowledge.faiss`

**When to run:**
- After adding new PDF documents
- After changing embedding model
- If vector store corrupts

---

## Testing Scripts

### `test_extraction.py` - Biomarker Extraction Tests
Tests the extraction and validation of biomarkers from user input.

**Usage:**
```bash
python scripts/test_extraction.py
```

---

### `test_chat_demo.py` - Chat Functionality Tests
Runs predefined test cases through the chat system.

**Usage:**
```bash
python scripts/test_chat_demo.py
```

---

### `monitor_test.py` - System Monitoring
Monitors system performance and vector store status.

**Usage:**
```bash
python scripts/monitor_test.py
```

---

## Startup Scripts (PowerShell for Windows)

### `run_api.ps1` - Run REST API Server
Starts the FastAPI server for REST endpoints.

**Usage:**
```powershell
.\scripts\run_api.ps1
```

**Starts:**
- FastAPI server on `http://localhost:8000`
- Interactive docs on `http://localhost:8000/docs`

---

### `start_api.ps1` - Alternative API Starter
Alternative API startup script with additional logging.

**Usage:**
```powershell
.\scripts\start_api.ps1
```

---

### `test_api_simple.ps1` - Simple API Tests
Tests basic API endpoints.

**Usage:**
```powershell
.\scripts\test_api_simple.ps1
```

---

## Quick Reference

| Script | Purpose | Command |
|--------|---------|---------|
| `chat.py` | Interactive biomarker analysis | `python scripts/chat.py` |
| `setup_embeddings.py` | Build vector store | `python scripts/setup_embeddings.py` |
| `test_extraction.py` | Test biomarker extraction | `python scripts/test_extraction.py` |
| `test_chat_demo.py` | Test chat system | `python scripts/test_chat_demo.py` |
| `monitor_test.py` | Monitor system performance | `python scripts/monitor_test.py` |
| `run_api.ps1` | Start REST API | `.\scripts\run_api.ps1` |
| `start_api.ps1` | Start API (alt) | `.\scripts\start_api.ps1` |
| `test_api_simple.ps1` | Test API | `.\scripts\test_api_simple.ps1` |

---

## Development Scripts (Useful for Developers)

To create new development utilities:

```bash
touch scripts/my_script.py
# Add your code following the pattern of existing scripts
```

---

For more information, see:
- [QUICKSTART.md](../QUICKSTART.md) - Setup guide
- [DEVELOPMENT.md](../docs/DEVELOPMENT.md) - Development guide
- [API.md](../docs/API.md) - REST API documentation
