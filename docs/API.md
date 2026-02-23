# RagBot REST API Documentation

## Overview

RagBot provides a RESTful API for integrating biomarker analysis into applications, web services, and dashboards.

## Base URL

```
http://localhost:8000
```

## Quick Start

1. **Start the API server:**
   ```powershell
   cd api
   python -m uvicorn app.main:app --reload
   ```

2. **API will be available at:**
   - Interactive docs: http://localhost:8000/docs
   - OpenAPI schema: http://localhost:8000/openapi.json

## Authentication

Currently no authentication required. For production deployment, add:
- API keys
- JWT tokens
- Rate limiting
- CORS restrictions

## Endpoints

### 1. Health Check

**Request:**
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-07T01:30:00Z",
  "llm_status": "connected",
  "vector_store_loaded": true,
  "available_models": ["llama-3.3-70b-versatile (Groq)"],
  "uptime_seconds": 3600.0,
  "version": "1.0.0"
}
```

---

### 2. Analyze Biomarkers (Natural Language)

Parse biomarkers from free-text input, predict disease, and run the full RAG workflow.

**Request:**
```http
POST /api/v1/analyze/natural
Content-Type: application/json

{
  "message": "My glucose is 185, HbA1c is 8.2 and cholesterol is 210",
  "patient_context": {
    "age": 52,
    "gender": "male",
    "bmi": 31.2
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Free-text describing biomarker values |
| `patient_context` | object | No | Age, gender, BMI for context |

---

### 3. Analyze Biomarkers (Structured)

Provide biomarkers as a dictionary (skips LLM extraction step).

**Request:**
```http
POST /api/v1/analyze/structured
Content-Type: application/json

{
  "biomarkers": {
    "Glucose": 185.0,
    "HbA1c": 8.2,
    "LDL Cholesterol": 165.0,
    "HDL Cholesterol": 38.0
  },
  "patient_context": {
    "age": 52,
    "gender": "male",
    "bmi": 31.2
  }
}
```

**Response:**
```json
{
  "prediction": {
    "disease": "Diabetes",
    "confidence": 0.85,
    "probabilities": {
      "Diabetes": 0.85,
      "Heart Disease": 0.10,
      "Other": 0.05
    }
  },
  "analysis": {
    "biomarker_analysis": {
      "Glucose": {
        "value": 140,
        "status": "critical",
        "reference_range": "70-100",
        "alert": "Hyperglycemia - diabetes risk"
      },
      "HbA1c": {
        "value": 10.0,
        "status": "critical",
        "reference_range": "4.0-6.4%",
        "alert": "Diabetes (≥6.5%)"
      }
    },
    "disease_explanation": {
      "pathophysiology": "...",
      "citations": ["source1", "source2"]
    },
    "key_drivers": [
      "Glucose levels indicate hyperglycemia",
      "HbA1c shows chronic elevated blood sugar"
    ],
    "clinical_guidelines": [
      "Consult healthcare professional for diabetes testing",
      "Consider medication if not already prescribed",
      "Implement lifestyle modifications"
    ],
    "confidence_assessment": {
      "prediction_reliability": "MODERATE",
      "evidence_strength": "MODERATE",
      "limitations": ["Limited biomarker set"]
    }
  },
  "recommendations": {
    "immediate_actions": [
      "Seek immediate medical attention for critical glucose values",
      "Schedule comprehensive diabetes screening"
    ],
    "lifestyle_changes": [
      "Increase physical activity to 150 min/week",
      "Reduce refined carbohydrate intake",
      "Achieve 5-10% weight loss if overweight"
    ],
    "monitoring": [
      "Check fasting glucose monthly",
      "Recheck HbA1c every 3 months",
      "Monitor weight weekly"
    ]
  },
  "safety_alerts": [
    {
      "biomarker": "Glucose",
      "level": "CRITICAL",
      "message": "Glucose 140 mg/dL is critical"
    },
    {
      "biomarker": "HbA1c",
      "level": "CRITICAL",
      "message": "HbA1c 10% indicates diabetes"
    }
  ],
  "timestamp": "2026-02-07T01:35:00Z",
  "processing_time_ms": 18500
}
```

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `biomarkers` | object | Yes | Key-value pairs of biomarker names and numeric values (at least 1) |
| `patient_context` | object | No | Age, gender, BMI for context |

**Biomarker Names** (canonical, with 80+ aliases auto-normalized):
Glucose, HbA1c, Triglycerides, Total Cholesterol, LDL Cholesterol, HDL Cholesterol, Hemoglobin, Platelets, White Blood Cells, Red Blood Cells, BMI, Systolic Blood Pressure, Diastolic Blood Pressure, and more.

See `config/biomarker_references.json` for the full list of 24 supported biomarkers.
```

---

### 4. Get Example Analysis

Returns a pre-built diabetes example case (useful for testing and understanding the response format).

**Request:**
```http
GET /api/v1/example
```

**Response:** Same schema as the analyze endpoints above.

---

### 5. List Biomarker Reference Ranges

**Request:**
```http
GET /api/v1/biomarkers
```

**Response:**
```json
{
  "biomarkers": {
    "Glucose": {
      "min": 70,
      "max": 100,
      "unit": "mg/dL",
      "normal_range": "70-100",
      "critical_low": 54,
      "critical_high": 400
    },
    "HbA1c": {
      "min": 4.0,
      "max": 5.6,
      "unit": "%",
      "normal_range": "4.0-5.6",
      "critical_low": -1,
      "critical_high": 14
    }
  },
  "count": 24
}
```

---

## Error Handling

### Invalid Input (Natural Language)

**Response:** `400 Bad Request`
```json
{
  "detail": {
    "error_code": "EXTRACTION_FAILED",
    "message": "Could not extract biomarkers from input",
    "input_received": "...",
    "suggestion": "Try: 'My glucose is 140 and HbA1c is 7.5'"
  }
}
```

### Missing Required Fields

**Response:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "loc": ["body", "biomarkers"],
      "msg": "Biomarkers dictionary must not be empty",
      "type": "value_error"
    }
  ]
}
```

### Server Error

**Response:** `500 Internal Server Error`
```json
{
  "error": "Internal server error",
  "detail": "Error processing analysis",
  "timestamp": "2026-02-07T01:35:00Z"
}
```

---

## Usage Examples

### Python

```python
import requests
import json

API_URL = "http://localhost:8000/api/v1"

biomarkers = {
    "Glucose": 140,
    "HbA1c": 10.0,
    "Triglycerides": 200
}

response = requests.post(
    f"{API_URL}/analyze/structured",
    json={"biomarkers": biomarkers}
)

result = response.json()
print(f"Disease: {result['prediction']['disease']}")
print(f"Confidence: {result['prediction']['confidence']}")
```

### JavaScript/Node.js

```javascript
const biomarkers = {
    Glucose: 140,
    HbA1c: 10.0,
    Triglycerides: 200
};

fetch('http://localhost:8000/api/v1/analyze/structured', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({biomarkers})
})
.then(r => r.json())
.then(data => {
    console.log(`Disease: ${data.prediction.disease}`);
    console.log(`Confidence: ${data.prediction.confidence}`);
});
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "biomarkers": {
      "Glucose": 140,
      "HbA1c": 10.0
    }
  }'
```

---

## Rate Limiting (Recommended for Production)

- **Default**: 100 requests/minute per IP
- **Burst**: 10 concurrent requests
- **Headers**: Include `X-RateLimit-Remaining` in responses

---

## CORS Configuration

For web-based integrations, configure CORS in `api/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Response Time SLA

- **95th percentile**: < 25 seconds
- **99th percentile**: < 40 seconds

(Includes all 6 agent processing steps and RAG retrieval)

---

## Deployment

### Docker

See [api/Dockerfile](../api/Dockerfile) for containerized deployment.

### Production Checklist

- [ ] Enable authentication (API keys/JWT)
- [ ] Add rate limiting
- [ ] Configure CORS for your domain
- [ ] Set up error logging
- [ ] Enable request/response logging
- [ ] Configure health check monitoring
- [ ] Use HTTP/2 or HTTP/3
- [ ] Set up API documentation access control

---

For more information, see [ARCHITECTURE.md](ARCHITECTURE.md) and [DEVELOPMENT.md](DEVELOPMENT.md).
