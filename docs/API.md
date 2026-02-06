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
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-07T01:30:00Z",
  "version": "1.0.0"
}
```

---

### 2. Analyze Biomarkers

**Request:**
```http
POST /api/v1/analyze
Content-Type: application/json

{
  "biomarkers": {
    "Glucose": 140,
    "HbA1c": 10.0,
    "LDL Cholesterol": 150
  },
  "patient_context": {
    "age": 45,
    "gender": "M",
    "bmi": 28.5
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
| `biomarkers` | Object | Yes | Blood test values (key-value pairs) |
| `patient_context` | Object | No | Age, gender, BMI for context |

**Biomarker Names** (normalized):
Glucose, HbA1c, Triglycerides, Total Cholesterol, LDL Cholesterol, HDL Cholesterol, and 20+ more supported.

See `config/biomarker_references.json` for full list.

---

### 3. Biomarker Validation

**Request:**
```http
POST /api/v1/validate
Content-Type: application/json

{
  "biomarkers": {
    "Glucose": 140,
    "HbA1c": 10.0
  }
}
```

**Response:**
```json
{
  "valid_biomarkers": {
    "Glucose": {
      "value": 140,
      "reference_range": "70-100",
      "status": "out-of-range",
      "severity": "high"
    },
    "HbA1c": {
      "value": 10.0,
      "reference_range": "4.0-6.4%",
      "status": "out-of-range",
      "severity": "high"
    }
  },
  "invalid_biomarkers": [],
  "alerts": [...]
}
```

---

### 4. Get Biomarker Reference Ranges

**Request:**
```http
GET /api/v1/biomarkers/reference-ranges
```

**Response:**
```json
{
  "biomarkers": {
    "Glucose": {
      "min": 70,
      "max": 100,
      "unit": "mg/dL",
      "condition": "fasting"
    },
    "HbA1c": {
      "min": 4.0,
      "max": 6.4,
      "unit": "%",
      "condition": "normal"
    },
    ...
  },
  "last_updated": "2026-02-07"
}
```

---

### 5. Get Analysis History

**Request:**
```http
GET /api/v1/history?limit=10
```

**Response:**
```json
{
  "analyses": [
    {
      "id": "report_Diabetes_20260207_012151",
      "disease": "Diabetes",
      "confidence": 0.85,
      "timestamp": "2026-02-07T01:21:51Z",
      "biomarker_count": 2
    },
    ...
  ],
  "total": 12,
  "limit": 10
}
```

---

## Error Handling

### Invalid Biomarker Name

**Request:**
```http
POST /api/v1/analyze
{
  "biomarkers": {
    "InvalidBiomarker": 100
  }
}
```

**Response:** `400 Bad Request`
```json
{
  "error": "Invalid biomarker",
  "detail": "InvalidBiomarker is not a recognized biomarker",
  "suggestions": ["Glucose", "HbA1c", "Triglycerides"]
}
```

### Missing Required Fields

**Response:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "loc": ["body", "biomarkers"],
      "msg": "field required",
      "type": "value_error.missing"
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
    f"{API_URL}/analyze",
    json={"biomarkers": biomarkers}
)

result = response.json()
print(f"Disease: {result['prediction']['disease']}")
print(f"Confidence: {result['prediction']['confidence']}")
print(f"Recommendations: {result['recommendations']['immediate_actions']}")
```

### JavaScript/Node.js

```javascript
const biomarkers = {
    Glucose: 140,
    HbA1c: 10.0,
    Triglycerides: 200
};

fetch('http://localhost:8000/api/v1/analyze', {
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
curl -X POST http://localhost:8000/api/v1/analyze \
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

(Times include all agent processing and RAG retrieval)

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
