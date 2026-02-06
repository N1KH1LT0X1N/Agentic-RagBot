# 🚀 Fast Embeddings Setup Guide

## Problem
Local Ollama embeddings are VERY slow (30+ minutes for 2,861 chunks).

## Solution
Use Google's Gemini API for embeddings - **FREE and 100x faster!**

---

## Quick Setup (5 minutes)

### 1. Get Free Google API Key
1. Visit: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

### 2. Add to `.env` file
```bash
GOOGLE_API_KEY="your_actual_key_here"
```

### 3. Run PDF Processor
```powershell
python src/pdf_processor.py
```

Choose option `1` (Google Gemini) when prompted.

---

## Speed Comparison

| Method | Time | Cost |
|--------|------|------|
| **Google Gemini** | ~2-3 minutes | FREE |
| Local Ollama | 30+ minutes | FREE |

---

## Fallback Options

### Option 1: No API Key
If `GOOGLE_API_KEY` is not set, system automatically falls back to local Ollama.

### Option 2: Manual Selection
When running `python src/pdf_processor.py`, choose:
- Option `1`: Google Gemini (fast)
- Option `2`: Local Ollama (slow)

---

## Technical Details

**Google Embeddings:**
- Model: `models/embedding-001`
- Dimensions: 768
- Rate Limit: 1500 requests/minute (more than enough)
- Cost: FREE for standard usage

**Local Ollama:**
- Model: `nomic-embed-text`
- Dimensions: 768
- Speed: ~1 chunk/second
- Cost: FREE, runs offline

---

## Usage in Code

```python
from src.pdf_processor import get_embedding_model

# Use Google (recommended)
embeddings = get_embedding_model(provider="google")

# Use Ollama (backup)
embeddings = get_embedding_model(provider="ollama")

# Auto-detect with fallback
embeddings = get_embedding_model()  # defaults to Google
```

---

## Already Built Vector Store?

If you already created the vector store with Ollama, you don't need to rebuild it!

To rebuild with faster embeddings:
```python
from src.pdf_processor import setup_knowledge_base, get_embedding_model

embeddings = get_embedding_model(provider="google")
retrievers = setup_knowledge_base(embeddings, force_rebuild=True)
```

---

## Troubleshooting

### "GOOGLE_API_KEY not found"
- Check `.env` file exists in project root
- Verify key is set: `GOOGLE_API_KEY="AIza..."`
- Restart terminal/IDE after adding key

### "Google embeddings failed"
- Check internet connection
- Verify API key is valid
- System will auto-fallback to Ollama

### Ollama still slow?
- Embeddings are one-time setup
- Once built, retrieval is instant
- Consider using Google for initial build

---

## Security Note

⚠️ **Never commit `.env` file to Git!**

Your `.gitignore` should include:
```
.env
*.faiss
*.pkl
```

---

*Need help? The system has automatic fallback - it will always work!*
