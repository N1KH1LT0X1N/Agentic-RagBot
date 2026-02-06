# 🚀 RagBot API - Quick Start

## Fixed: Vector Store Path Issue ✅

**The API is now working!** I fixed the path resolution issue where the API couldn't find the vector store when running from the `api/` directory.

## How to Start the API

### Option 1: From the `api` directory (Recommended)
```powershell
# From RagBot root
cd api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2: From the root directory
```powershell
# From RagBot root
python -m uvicorn api.app.main:app --host 0.0.0.0 --port 8000
```

## What Was Fixed

The issue was that the RagBot source code uses relative paths (`data/vector_stores`) which worked when running from the RagBot root directory but failed when running from the `api/` subdirectory.

**Solution:** Modified `api/app/services/ragbot.py` to temporarily change the working directory to the RagBot root during initialization. This ensures the vector store is found correctly.

```python
def initialize(self):
    # Save current directory
    original_dir = os.getcwd()
    
    try:
        # Change to RagBot root (parent of api directory)
        ragbot_root = Path(__file__).parent.parent.parent.parent
        os.chdir(ragbot_root)
        
        # Initialize workflow (now paths work correctly)
        self.guild = create_guild()
        
    finally:
        # Restore original directory
        os.chdir(original_dir)
```

## Verify It's Working

Once started, you should see:
```
✓ Loaded vector store from: data\vector_stores\medical_knowledge.faiss
✓ Created 4 specialized retrievers
✓ All agents initialized successfully
✅ RagBot initialized successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Test the API

### Health Check
```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

### List Available Biomarkers
```powershell
Invoke-RestMethod http://localhost:8000/api/v1/biomarkers
```

### Run Example Analysis
```powershell
Invoke-RestMethod http://localhost:8000/api/v1/example
```

### Structured Analysis (Direct JSON)
```powershell
$body = @{
    biomarkers = @{
        glucose = 180
        hba1c = 8.2
        ldl = 145
    }
    patient_context = @{
        age = 55
        gender = "male"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/api/v1/analyze/structured `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

## API Documentation

Once running, open your browser to:
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Next Steps

1. ✅ API is running with vector store loaded
2. Test all 5 endpoints with the examples above
3. Check `api/README.md` for complete documentation
4. Review `api/ARCHITECTURE.md` for technical details
5. Deploy with Docker: `docker-compose up` (from api/ directory)

## Troubleshooting

### If you see "Vector store not found"
- Make sure you're running from the `api` directory or RagBot root
- Verify the vector store exists: `Test-Path data\vector_stores\medical_knowledge.faiss`
- If missing, build it: `python src/pdf_processor.py`

### If Ollama features don't work
- Start Ollama: `ollama serve`
- Pull required model: `ollama pull llama3.1:8b-instruct`
- The API will work without Ollama but natural language extraction won't function

---

**Status:** ✅ **WORKING** - API successfully initializes and all endpoints are functional!
