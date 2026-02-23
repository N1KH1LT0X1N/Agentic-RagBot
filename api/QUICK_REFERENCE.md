# RagBot API - Quick Reference

## 🚀 Quick Start Commands

### Start API (Local)
```powershell
# From api/ directory
cd C:\Users\admin\OneDrive\Documents\GitHub\RagBot\api
..\.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Start API (Docker)
```powershell
# From api/ directory
docker-compose up --build
```

### Test API
```powershell
# Run test suite
.\test_api.ps1

# Or manual test
curl http://localhost:8000/api/v1/health
```

---

## 📡 Endpoints Cheat Sheet

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/health` | Check API status |
| GET | `/api/v1/biomarkers` | List all 24 biomarkers |
| POST | `/api/v1/analyze/natural` | Natural language analysis |
| POST | `/api/v1/analyze/structured` | Structured JSON analysis |
| GET | `/api/v1/example` | Pre-run diabetes example |
| GET | `/docs` | Swagger UI documentation |

---

## 💻 Integration Snippets

### JavaScript/Fetch
```javascript
const response = await fetch('http://localhost:8000/api/v1/analyze/natural', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: "My glucose is 185 and HbA1c is 8.2",
    patient_context: {age: 52, gender: "male"}
  })
});
const result = await response.json();
console.log(result.prediction.disease); // "Diabetes"
```

### PowerShell
```powershell
$body = @{
    biomarkers = @{Glucose = 185; HbA1c = 8.2}
    patient_context = @{age = 52; gender = "male"}
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/analyze/structured" `
    -Method Post -Body $body -ContentType "application/json"

Write-Host $result.prediction.disease
```

### Python
```python
import requests

response = requests.post('http://localhost:8000/api/v1/analyze/structured', json={
    'biomarkers': {'Glucose': 185.0, 'HbA1c': 8.2},
    'patient_context': {'age': 52, 'gender': 'male'}
})
result = response.json()
print(result['prediction']['disease'])  # Diabetes
```

---

## 🔧 Troubleshooting Quick Fixes

### API won't start
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <PID> /F
```

### LLM provider errors
```powershell
# Check your .env has the right keys
# Default provider is Groq (GROQ_API_KEY required)
# Alternative: Google Gemini (GOOGLE_API_KEY)
# Optional: Ollama (local, no key needed)
```

### Vector store not loading
```powershell
# From RagBot root
.\.venv\Scripts\python.exe scripts/setup_embeddings.py
```

---

## 📊 Response Fields Overview

**Key Fields You'll Use:**
- `prediction.disease` - Predicted disease name
- `prediction.confidence` - Confidence score (0-1)
- `analysis.safety_alerts` - Critical warnings
- `analysis.biomarker_flags` - All biomarker statuses
- `analysis.recommendations.immediate_actions` - What to do
- `conversational_summary` - Human-friendly text for display

**Full Data Access:**
- `agent_outputs` - Raw agent execution data
- `analysis.disease_explanation.citations` - Medical literature sources
- `workflow_metadata` - Execution details

---

## 🎯 Common Use Cases

### 1. Chatbot Integration
```javascript
// User types: "my glucose is 140"
const response = await analyzeNatural(userMessage);
displayResult(response.conversational_summary);
```

### 2. Form-Based Input
```javascript
// User fills form with biomarker values
const response = await analyzeStructured({
  biomarkers: formData,
  patient_context: patientInfo
});
showAnalysis(response.analysis);
```

### 3. Dashboard Display
```javascript
// Fetch and display example
const example = await fetch('/api/v1/example').then(r => r.json());
renderDashboard(example);
```

---

## 🔐 Production Checklist

Before deploying to production:

- [ ] Update CORS in `.env` (restrict to your domain)
- [ ] Add API key authentication
- [ ] Enable HTTPS
- [ ] Set up rate limiting
- [ ] Configure logging (rotate logs)
- [ ] Add monitoring/alerts
- [ ] Test error handling
- [ ] Document API for your team

---

## 📞 Support

- **API Docs:** http://localhost:8000/docs
- **Main README:** [api/README.md](README.md)
- **RagBot Docs:** [../docs/](../docs/)

---

## 🎓 Example Requests

### Simple Test
```bash
curl http://localhost:8000/api/v1/health
```

### Full Analysis
```bash
curl -X POST http://localhost:8000/api/v1/analyze/natural \
  -H "Content-Type: application/json" \
  -d '{"message": "glucose 185, HbA1c 8.2", "patient_context": {"age": 52, "gender": "male"}}'
```

### Get Example
```bash
curl http://localhost:8000/api/v1/example
```

---

**Last Updated:** February 2026  
**API Version:** 1.0.0
