# RagBot API

**REST API for Medical Biomarker Analysis**

Exposes the RagBot multi-agent RAG system as a FastAPI REST service for web integration.

---

## 🎯 Overview

This API wraps the RagBot clinical analysis system, providing:
- **Natural language input** - Extract biomarkers from conversational text
- **Structured JSON input** - Direct biomarker analysis
- **Full detailed responses** - All agent outputs, citations, recommendations
- **Example endpoint** - Pre-run diabetes case for testing

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Endpoints](#endpoints)
- [Request/Response Examples](#requestresponse-examples)
- [Deployment](#deployment)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

1. **Ollama running locally**:
   ```bash
   ollama serve
   ```

2. **Required models**:
   ```bash
   ollama pull llama3.1:8b-instruct
   ollama pull qwen2:7b
   ollama pull nomic-embed-text
   ```

### Option 1: Run Locally (Development)

```bash
# From RagBot root directory
cd api

# Install dependencies
pip install -r ../requirements.txt
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run server
python -m uvicorn app.main:app --reload --port 8000
```

### Option 2: Run with Docker

```bash
# From api directory
docker-compose up --build
```

Server will start on `http://localhost:8000`

---

## 📡 Endpoints

### 1. Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T10:30:00Z",
  "ollama_status": "connected",
  "vector_store_loaded": true,
  "available_models": ["llama3.1:8b-instruct", "qwen2:7b"],
  "uptime_seconds": 3600.0,
  "version": "1.0.0"
}
```

---

### 2. List Biomarkers
```http
GET /api/v1/biomarkers
```

**Returns:** All 24 supported biomarkers with reference ranges, units, and clinical significance.

---

### 3. Natural Language Analysis
```http
POST /api/v1/analyze/natural
Content-Type: application/json
```

**Request:**
```json
{
  "message": "My glucose is 185, HbA1c is 8.2 and cholesterol is 210",
  "patient_context": {
    "age": 52,
    "gender": "male",
    "bmi": 31.2
  }
}
```

**Response:** Full detailed analysis (see [Response Structure](#response-structure))

---

### 4. Structured Analysis
```http
POST /api/v1/analyze/structured
Content-Type: application/json
```

**Request:**
```json
{
  "biomarkers": {
    "Glucose": 185.0,
    "HbA1c": 8.2,
    "Cholesterol": 210.0,
    "Triglycerides": 210.0,
    "HDL": 38.0
  },
  "patient_context": {
    "age": 52,
    "gender": "male",
    "bmi": 31.2
  }
}
```

**Response:** Same as natural language analysis

---

### 5. Example Case
```http
GET /api/v1/example
```

**Returns:** Pre-run diabetes case (52-year-old male with elevated glucose/HbA1c)

---

## 📝 Request/Response Examples

### Response Structure

```json
{
  "status": "success",
  "request_id": "req_abc123xyz",
  "timestamp": "2025-11-23T10:30:00.000Z",
  
  "extracted_biomarkers": {
    "Glucose": 185.0,
    "HbA1c": 8.2
  },
  
  "input_biomarkers": {
    "Glucose": 185.0,
    "HbA1c": 8.2
  },
  
  "patient_context": {
    "age": 52,
    "gender": "male",
    "bmi": 31.2
  },
  
  "prediction": {
    "disease": "Diabetes",
    "confidence": 0.87,
    "probabilities": {
      "Diabetes": 0.87,
      "Heart Disease": 0.08,
      "Anemia": 0.03,
      "Thalassemia": 0.01,
      "Thrombocytopenia": 0.01
    }
  },
  
  "analysis": {
    "biomarker_flags": [
      {
        "name": "Glucose",
        "value": 185.0,
        "unit": "mg/dL",
        "status": "CRITICAL_HIGH",
        "reference_range": "70-100 mg/dL",
        "warning": "Hyperglycemia"
      }
    ],
    
    "safety_alerts": [
      {
        "severity": "CRITICAL",
        "biomarker": "Glucose",
        "message": "Glucose is 185.0 mg/dL, above critical threshold",
        "action": "SEEK IMMEDIATE MEDICAL ATTENTION"
      }
    ],
    
    "key_drivers": [
      {
        "biomarker": "Glucose",
        "value": 185.0,
        "explanation": "Glucose at 185.0 mg/dL is CRITICAL_HIGH...",
        "evidence": "Retrieved from medical literature..."
      }
    ],
    
    "disease_explanation": {
      "pathophysiology": "Detailed disease mechanism...",
      "citations": ["Source 1", "Source 2"],
      "retrieved_chunks": [...]
    },
    
    "recommendations": {
      "immediate_actions": [
        "Consult healthcare provider immediately..."
      ],
      "lifestyle_changes": [
        "Follow a balanced, nutrient-rich diet..."
      ],
      "monitoring": [
        "Monitor glucose levels daily..."
      ]
    },
    
    "confidence_assessment": {
      "prediction_reliability": "MODERATE",
      "evidence_strength": "STRONG",
      "limitations": ["Limited biomarkers provided"],
      "reasoning": "High confidence based on glucose and HbA1c..."
    }
  },
  
  "agent_outputs": [
    {
      "agent_name": "Biomarker Analyzer",
      "findings": {...},
      "metadata": {...}
    }
  ],
  
  "workflow_metadata": {
    "sop_version": "Baseline",
    "processing_timestamp": "2025-11-23T10:30:00Z",
    "agents_executed": 5,
    "workflow_success": true
  },
  
  "conversational_summary": "Hi there! 👋\n\nBased on your biomarkers...",
  
  "processing_time_ms": 3542.0,
  "sop_version": "Baseline"
}
```

### cURL Examples

**Health Check:**
```bash
curl http://localhost:8000/api/v1/health
```

**Natural Language Analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/natural \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My glucose is 185 and HbA1c is 8.2",
    "patient_context": {
      "age": 52,
      "gender": "male"
    }
  }'
```

**Structured Analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "biomarkers": {
      "Glucose": 185.0,
      "HbA1c": 8.2
    },
    "patient_context": {
      "age": 52,
      "gender": "male"
    }
  }'
```

**Get Example:**
```bash
curl http://localhost:8000/api/v1/example
```

---

## 🐳 Deployment

### Docker Deployment

1. **Build and run:**
   ```bash
   cd api
   docker-compose up --build
   ```

2. **Check health:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f ragbot-api
   ```

4. **Stop:**
   ```bash
   docker-compose down
   ```

### Production Deployment

For production:

1. **Update `.env`:**
   ```bash
   CORS_ORIGINS=https://your-frontend-domain.com
   API_RELOAD=false
   LOG_LEVEL=WARNING
   ```

2. **Use production WSGI server:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Add reverse proxy (nginx):**
   ```nginx
   location /api {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

---

## 💻 Development

### Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── analyze.py       # Analysis endpoints
│   │   ├── biomarkers.py    # Biomarkers list
│   │   └── health.py        # Health check
│   └── services/
│       ├── __init__.py
│       ├── extraction.py    # Natural language extraction
│       └── ragbot.py        # Workflow wrapper
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### Running Tests

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test example case (doesn't require Ollama extraction)
curl http://localhost:8000/api/v1/example

# Test natural language (requires Ollama)
curl -X POST http://localhost:8000/api/v1/analyze/natural \
  -H "Content-Type: application/json" \
  -d '{"message": "glucose 140, HbA1c 7.5"}'
```

### Hot Reload

For development with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000
```

---

## 🔧 Troubleshooting

### Issue: "Ollama connection failed"

**Symptom:** Health check shows `ollama_status: "disconnected"`

**Solutions:**
1. Start Ollama: `ollama serve`
2. Check Ollama is running: `curl http://localhost:11434/api/version`
3. Verify models are pulled:
   ```bash
   ollama list
   ```

---

### Issue: "Vector store not loaded"

**Symptom:** Health check shows `vector_store_loaded: false`

**Solutions:**
1. Run vector store setup from RagBot root:
   ```bash
   python scripts/setup_embeddings.py
   ```
2. Check `data/vector_stores/medical_knowledge.faiss` exists
3. Restart API server

---

### Issue: "No biomarkers found"

**Symptom:** Natural language endpoint returns error

**Solutions:**
1. Be explicit: "My glucose is 140" (not "blood sugar is high")
2. Include numbers: "glucose 140" works better than "elevated glucose"
3. Use structured endpoint if you have exact values

---

### Issue: Docker container can't reach Ollama

**Symptom:** Container health check fails

**Solutions:**

**Windows/Mac (Docker Desktop):**
```yaml
# In docker-compose.yml
environment:
  - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Linux:**
```yaml
# In docker-compose.yml
network_mode: "host"
environment:
  - OLLAMA_BASE_URL=http://localhost:11434
```

---

## 📚 Integration Examples

### JavaScript/TypeScript

```typescript
// Analyze biomarkers from natural language
async function analyzeBiomarkers(userInput: string) {
  const response = await fetch('http://localhost:8000/api/v1/analyze/natural', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: userInput,
      patient_context: {
        age: 52,
        gender: "male"
      }
    })
  });
  
  const result = await response.json();
  return result;
}

// Display results
const analysis = await analyzeBiomarkers("My glucose is 185 and HbA1c is 8.2");
console.log(`Prediction: ${analysis.prediction.disease}`);
console.log(`Confidence: ${(analysis.prediction.confidence * 100).toFixed(0)}%`);
console.log(`\n${analysis.conversational_summary}`);
```

### Python

```python
import requests

# Structured analysis
response = requests.post(
    'http://localhost:8000/api/v1/analyze/structured',
    json={
        'biomarkers': {
            'Glucose': 185.0,
            'HbA1c': 8.2
        },
        'patient_context': {
            'age': 52,
            'gender': 'male'
        }
    }
)

result = response.json()
print(f"Disease: {result['prediction']['disease']}")
print(f"Confidence: {result['prediction']['confidence']:.1%}")
```

---

## 📄 API Documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

---

## 🤝 Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review API documentation at `/docs`
3. Check RagBot main README

---

## 📊 Performance Notes

- **Initial startup:** 10-30 seconds (loads vector store)
- **Analysis time:** 3-10 seconds per request
- **Concurrent requests:** Supported (FastAPI async)
- **Memory usage:** ~2-4GB (vector store + models)

---

## 🔐 Security Notes

**For MVP/Development:**
- CORS allows all origins (`*`)
- No authentication required
- Runs on localhost

**For Production:**
- Restrict CORS to specific origins
- Add API key authentication
- Use HTTPS
- Implement rate limiting
- Add request validation

---

Built with ❤️ on top of RagBot Multi-Agent RAG System
