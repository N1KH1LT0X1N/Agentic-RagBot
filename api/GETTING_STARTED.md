# RagBot API - Getting Started (5 Minutes)

Follow these steps to get your API running in 5 minutes:

---

## ✅ Prerequisites Check

Before starting, ensure you have:

1. **Ollama installed and running**
   ```powershell
   # Check if Ollama is running
   curl http://localhost:11434/api/version
   
   # If not, start it
   ollama serve
   ```

2. **Required models pulled**
   ```powershell
   ollama list
   
   # If missing, pull them
   ollama pull llama3.1:8b-instruct
   ollama pull qwen2:7b
   ```

3. **Python 3.11+**
   ```powershell
   python --version
   ```

4. **RagBot dependencies installed**
   ```powershell
   # From RagBot root directory
   pip install -r requirements.txt
   ```

---

## 🚀 Step 1: Install API Dependencies (30 seconds)

```powershell
# Navigate to api directory
cd C:\Users\admin\OneDrive\Documents\GitHub\RagBot\api

# Install FastAPI and dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi-0.109.0 uvicorn-0.27.0 ...
```

---

## 🚀 Step 2: Start the API (10 seconds)

```powershell
# Make sure you're in the api/ directory
python -m uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
🚀 Starting RagBot API Server
✅ RagBot service initialized successfully
✅ API server ready to accept requests
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**⚠️ Wait 10-30 seconds for initialization** (loading vector store)

---

## ✅ Step 3: Verify It's Working (30 seconds)

### Option A: Use the Test Script
```powershell
# In a NEW PowerShell window (keep API running)
cd C:\Users\admin\OneDrive\Documents\GitHub\RagBot\api
.\test_api.ps1
```

### Option B: Manual Test
```powershell
# Health check
curl http://localhost:8000/api/v1/health

# Get example analysis
curl http://localhost:8000/api/v1/example
```

### Option C: Browser
Open: http://localhost:8000/docs

---

## 🎉 Step 4: Test Your First Request (1 minute)

### Test Natural Language Analysis

```powershell
# PowerShell
$body = @{
    message = "My glucose is 185 and HbA1c is 8.2"
    patient_context = @{
        age = 52
        gender = "male"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/analyze/natural" `
    -Method Post -Body $body -ContentType "application/json"
```

**Expected:** JSON response with disease prediction, safety alerts, recommendations

---

## 🔗 Step 5: Integrate with Your Backend (2 minutes)

### Your Backend Code (Node.js/Express Example)

```javascript
// backend/routes/analysis.js
const axios = require('axios');

app.post('/api/analyze', async (req, res) => {
  try {
    // Get user input from your frontend
    const { biomarkerText, patientInfo } = req.body;
    
    // Call RagBot API on localhost
    const response = await axios.post('http://localhost:8000/api/v1/analyze/natural', {
      message: biomarkerText,
      patient_context: patientInfo
    });
    
    // Send results to your frontend
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### Your Frontend Code (React Example)

```javascript
// frontend/components/BiomarkerAnalysis.jsx
async function analyzeBiomarkers(userInput) {
  // Call YOUR backend (which calls RagBot API)
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      biomarkerText: userInput,
      patientInfo: { age: 52, gender: 'male' }
    })
  });
  
  const result = await response.json();
  
  // Display results
  console.log('Disease:', result.prediction.disease);
  console.log('Confidence:', result.prediction.confidence);
  console.log('Summary:', result.conversational_summary);
  
  return result;
}
```

---

## 📋 Quick Reference

### API Endpoints You'll Use Most:

1. **Natural Language (Recommended)**
   ```
   POST /api/v1/analyze/natural
   Body: {"message": "glucose 185, HbA1c 8.2"}
   ```

2. **Structured (If you have exact values)**
   ```
   POST /api/v1/analyze/structured
   Body: {"biomarkers": {"Glucose": 185, "HbA1c": 8.2}}
   ```

3. **Health Check**
   ```
   GET /api/v1/health
   ```

---

## 🐛 Troubleshooting

### Issue: "Connection refused"
**Problem:** Ollama not running  
**Fix:**
```powershell
ollama serve
```

### Issue: "Vector store not loaded"
**Problem:** Missing vector database  
**Fix:**
```powershell
cd C:\Users\admin\OneDrive\Documents\GitHub\RagBot
python scripts/setup_embeddings.py
```

### Issue: "Port 8000 in use"
**Problem:** Another app using port 8000  
**Fix:**
```powershell
# Use different port
python -m uvicorn app.main:app --reload --port 8001
```

---

## 📖 Next Steps

1. **Read the docs:** http://localhost:8000/docs
2. **Try all endpoints:** See [README.md](README.md)
3. **Integrate:** Connect your frontend to your backend
4. **Deploy:** Use Docker when ready ([docker-compose.yml](docker-compose.yml))

---

## 🎊 You're Done!

Your RagBot is now accessible via REST API at `http://localhost:8000`

**Test it right now:**
```powershell
curl http://localhost:8000/api/v1/health
```

---

**Need Help?**
- Full docs: [README.md](README.md)
- Quick reference: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- Implementation details: [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)

**Have fun! 🚀**
