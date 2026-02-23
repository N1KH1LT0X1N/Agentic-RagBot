# Quick Start Guide - RagBot

Get up and running in **5 minutes**!

## Step 1: Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed ([Download](https://www.python.org/downloads/))
- **Git** installed ([Download](https://git-scm.com/downloads))
- **FREE API Key** from one of:
  - [Groq](https://console.groq.com/keys) - Recommended (Fast & Free)
  - [Google Gemini](https://aistudio.google.com/app/apikey) - Alternative

**System Requirements:**
- 4GB+ RAM
- 2GB free disk space
- No GPU required

---

## Step 2: Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/RagBot.git
cd RagBot
```

### Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

⏱️ *Takes about 2-3 minutes*

---

## Step 3: Configuration

### Copy Environment Template

```bash
cp .env.template .env
```

### Add Your API Keys

Open `.env` in your text editor and fill in:

**Option 1: Groq (Recommended)**
```bash
GROQ_API_KEY="your_groq_api_key_here"
LLM_PROVIDER="groq"
EMBEDDING_PROVIDER="google"
GOOGLE_API_KEY="your_google_api_key_here"  # For embeddings
```

**Option 2: Google Gemini Only**
```bash
GOOGLE_API_KEY="your_google_api_key_here"
LLM_PROVIDER="gemini"
EMBEDDING_PROVIDER="google"
```

**How to get API keys:**

1. **Groq API Key** (FREE):
   - Go to https://console.groq.com/keys
   - Sign up (free)
   - Click "Create API Key"
   - Copy and paste into `.env`

2. **Google Gemini Key** (FREE):
   - Go to https://aistudio.google.com/app/apikey
   - Sign in with Google account
   - Click "Create API Key"
   - Copy and paste into `.env`

---

## Step 4: Verify Installation

Quick system check:

```bash
python -c "
from src.workflow import create_guild
print('Testing system...')
guild = create_guild()
print('✅ Success! System ready to use!')
"
```

If you see "✅ Success!" you're good to go!

---

## Step 5: Run Your First Analysis

### Interactive Chat Mode

```bash
python scripts/chat.py
```

**Try the example:**
```
You: example
```

The system will analyze a sample diabetes case and show you the full capabilities.

**Try your own input:**
```
You: My glucose is 185, HbA1c is 8.2, and cholesterol is 210
```

---

## Common Commands

### Chat Interface
```bash
# Start interactive chat
python scripts/chat.py

# Commands within chat:
example    # Run demo case
help       # Show all biomarkers
quit       # Exit
```

### Python API
```python
from src.workflow import create_guild

# Create the guild
guild = create_guild()

# Analyze biomarkers
result = guild.run({
    "biomarkers": {"Glucose": 185, "HbA1c": 8.2},
    "model_prediction": {"disease": "Diabetes", "confidence": 0.87},
    "patient_context": {"age": 52, "gender": "male"}
})

print(result)
```

### REST API (Optional)
```bash
# Start API server
cd api
python -m uvicorn app.main:app --reload

# Access API docs
# Open browser: http://localhost:8000/docs
```

---

## Troubleshooting

### Import Error: "No module named 'langchain'"

**Solution:** Ensure virtual environment is activated and dependencies installed
```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Error: "GROQ_API_KEY not found"

**Solution:** Check your `.env` file exists and has the correct API key
```bash
cat .env  # macOS/Linux
type .env  # Windows

# Should show:
# GROQ_API_KEY="gsk_..."
```

### Error: "Vector store not found"

**Solution:** The vector store will auto-load from existing files. If missing:
```bash
# The system will create it automatically on first use
# Or manually by running:
python src/pdf_processor.py
```

### System is slow

**Tips:**
- Use Groq instead of Gemini (faster)
- Ensure good internet connection (API calls)
- Close unnecessary applications to free RAM

### API Key is Invalid

**Solution:**
1. Double-check you copied the full key (no extra spaces)
2. Ensure key hasn't expired
3. Try generating a new key
4. Check API provider's status page

---

## Next Steps

### Learn More

- **[Full Documentation](README.md)** - Complete system overview
- **[API Guide](docs/API.md)** - REST API documentation
- **[Contributing](CONTRIBUTING.md)** - How to contribute
- **[Architecture](docs/ARCHITECTURE.md)** - Deep dive into system design

### Customize

- **Biomarker Validation**: Edit `config/biomarker_references.json`
- **System Behavior**: Modify `src/config.py`
- **Agent Logic**: Explore `src/agents/`

### Run Tests

```bash
# Run unit tests (30 tests, no API keys needed)
.venv\Scripts\python.exe -m pytest tests/ -q \
  --ignore=tests/test_basic.py \
  --ignore=tests/test_diabetes_patient.py \
  --ignore=tests/test_evolution_loop.py \
  --ignore=tests/test_evolution_quick.py \
  --ignore=tests/test_evaluation_system.py

# Run integration tests (requires Groq/Gemini API key)
.venv\Scripts\python.exe -m pytest tests/test_diabetes_patient.py -v
```

---

## Example Session

```
$ python scripts/chat.py

======================================================================
RagBot - Interactive Chat
======================================================================

You can:
  1. Describe your biomarkers (e.g., 'My glucose is 140, HbA1c is 7.5')
  2. Type 'example' to see a sample diabetes case
  3. Type 'help' for biomarker list
  4. Type 'quit' to exit

🔧 Initializing medical knowledge system...
✓ System ready!

You: My glucose is 185 and HbA1c is 8.2

🔍 Analyzing your input...
✅ Found 2 biomarkers: Glucose, HbA1c
🧠 Predicting likely condition...
✅ Predicted: Diabetes (87% confidence)
📚 Consulting medical knowledge base...

🤖 RAG-BOT:
Hi there! 👋

Based on your biomarkers, I've analyzed your results:

🔴 PRIMARY FINDING: Type 2 Diabetes (87% confidence)

📊 YOUR BIOMARKERS:
├─ Glucose: 185 mg/dL [HIGH] (Normal: 70-100)
└─ HbA1c: 8.2% [CRITICAL HIGH] (Normal: <5.7)

🔬 WHAT THIS MEANS:
Your elevated glucose and HbA1c indicate Type 2 Diabetes...
[continues with full analysis]
```

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/RagBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/RagBot/discussions)
- **Documentation**: Check the [docs/](docs/) folder

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│               RagBot Cheat Sheet                    │
├─────────────────────────────────────────────────────────┤
│ START CHAT:  python scripts/chat.py                    │
│ START API:   cd api && uvicorn app.main:app --reload   │
│ RUN TESTS:   pytest                                     │
│ FORMAT CODE: black src/                                 │
├─────────────────────────────────────────────────────────┤
│ CHAT COMMANDS:                                          │
│   example  - Demo diabetes case                         │
│   help     - List biomarkers                            │
│   quit     - Exit                                       │
├─────────────────────────────────────────────────────────┤
│ SUPPORTED BIOMARKERS: 24 total                          │
│   Glucose, HbA1c, Cholesterol, LDL Cholesterol,    │
│   HDL Cholesterol, Triglycerides, Hemoglobin,       │
│   Platelets, White Blood Cells, Red Blood Cells,    │
│   BMI, Systolic Blood Pressure, and more...          │
├─────────────────────────────────────────────────────────┤
│ DETECTED DISEASES: 5 types                              │
│   Diabetes, Anemia, Heart Disease,                      │
│   Thalassemia, Thrombocytopenia                         │
└─────────────────────────────────────────────────────────┘
```

---

**Ready to analyze biomarkers? Let's go!**
