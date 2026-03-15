# MediGuard AI REST API Documentation

## Overview

MediGuard AI provides a comprehensive RESTful API for integrating biomarker analysis and medical Q&A into applications, web services, and dashboards.

## Base URL

```
Development: http://localhost:8000
Production: https://api.mediguard-ai.com
```

## Quick Start

1. **Start the API server:**
   ```bash
   uvicorn src.main:app --reload
   ```

2. **API will be available at:**
   - Interactive docs: http://localhost:8000/docs
   - OpenAPI schema: http://localhost:8000/openapi.json
   - ReDoc: http://localhost:8000/redoc

## Authentication

Currently no authentication required for development. Production will include:
- API keys
- JWT tokens
- Rate limiting

```http
Authorization: Bearer YOUR_API_KEY
```

## API Endpoints

### Health Check

Check if the API is running and healthy.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-03-15T10:30:00Z"
}
```

### Detailed Health Check

Get detailed health status of all services.

```http
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "opensearch": "connected",
    "redis": "connected",
    "llm": "connected"
  }
}
```

## Biomarker Analysis

### Structured Analysis

Analyze biomarkers using structured input.

```http
POST /analyze/structured
```

**Request Body:**
```json
{
  "biomarkers": {
    "Glucose": 140,
    "HbA1c": 10.0,
    "Hemoglobin": 11.5,
    "MCV": 75
  },
  "patient_context": {
    "age": 45,
    "gender": "male",
    "symptoms": ["fatigue", "thirst"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "analysis": {
    "primary_findings": [
      {
        "condition": "Diabetes",
        "confidence": 0.95,
        "evidence": {
          "glucose": 140,
          "hba1c": 10.0
        }
      }
    ],
    "critical_alerts": [
      {
        "type": "hyperglycemia",
        "severity": "high",
        "message": "Very high glucose levels detected"
      }
    ],
    "recommendations": [
      {
        "action": "Seek immediate medical attention",
        "priority": "urgent"
      }
    ],
    "biomarker_flags": [
      {
        "name": "Glucose",
        "value": 140,
        "status": "high",
        "reference_range": "70-100 mg/dL"
      }
    ]
  },
  "metadata": {
    "timestamp": "2024-03-15T10:30:00Z",
    "model_version": "2.0.0",
    "processing_time": 1.2
  }
}
```

### Natural Language Analysis

Analyze biomarkers from natural language input.

```http
POST /analyze/natural
```

**Request Body:**
```json
{
  "text": "My recent blood test shows glucose of 140 and HbA1c of 10. I'm a 45-year-old male feeling very tired lately.",
  "extract_biomarkers": true
}
```

**Response:**
```json
{
  "status": "success",
  "extracted_data": {
    "biomarkers": {
      "Glucose": 140,
      "HbA1c": 10.0
    },
    "patient_context": {
      "age": 45,
      "gender": "male",
      "symptoms": ["tired"]
    }
  },
  "analysis": {
    // Same structure as structured analysis
  }
}
```

## Medical Q&A

### Ask Question

Ask medical questions with RAG-powered answers.

```http
POST /ask
```

**Request Body:**
```json
{
  "question": "What are the symptoms of diabetes?",
  "context": {
    "patient_age": 45,
    "gender": "male"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "answer": {
    "content": "Common symptoms of diabetes include increased thirst, frequent urination, fatigue, and blurred vision...",
    "sources": [
      {
        "title": "Diabetes Mellitus - Clinical Guidelines",
        "snippet": "Patients often present with polyuria, polydipsia, and unexplained weight loss...",
        "confidence": 0.92
      }
    ],
    "related_questions": [
      "How is diabetes diagnosed?",
      "What are the treatment options for diabetes?"
    ]
  },
  "metadata": {
    "timestamp": "2024-03-15T10:30:00Z",
    "model": "llama-3.3-70b",
    "retrieval_count": 5
  }
}
```

### Streaming Ask

Get streaming responses for real-time chat.

```http
POST /ask/stream
```

**Request Body:**
```json
{
  "question": "Explain what HbA1c means",
  "stream": true
}
```

**Response (Server-Sent Events):**
```
data: {"type": "start", "id": "msg_123"}

data: {"type": "token", "content": "HbA1c is a "}

data: {"type": "token", "content": "blood test that "}

data: {"type": "token", "content": "measures your "}

...

data: {"type": "end", "id": "msg_123"}
```

## Knowledge Base Search

### Search Documents

Search the medical knowledge base.

```http
POST /search
```

**Request Body:**
```json
{
  "query": "diabetes management guidelines",
  "top_k": 5,
  "filters": {
    "document_type": ["guideline", "research"],
    "date_range": {
      "start": "2020-01-01",
      "end": "2024-12-31"
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "results": [
    {
      "id": "doc_123",
      "title": "ADA Standards of Medical Care in Diabetes",
      "snippet": "The ADA recommends HbA1c testing every 3 months for patients with diabetes...",
      "score": 0.95,
      "metadata": {
        "document_type": "guideline",
        "publication_date": "2024-01-15",
        "authors": ["American Diabetes Association"]
      }
    }
  ],
  "total_found": 1247,
  "search_time": 0.15
}
```

## Error Handling

### Error Response Format

All errors return a consistent format:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid biomarker values",
    "details": [
      {
        "field": "biomarkers.Glucose",
        "issue": "Value must be between 0 and 1000"
      }
    ]
  },
  "request_id": "req_789"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| VALIDATION_ERROR | Invalid input data |
| PROCESSING_ERROR | Error during analysis |
| RATE_LIMIT_EXCEEDED | Too many requests |
| SERVICE_UNAVAILABLE | Required service is down |
| AUTHENTICATION_ERROR | Invalid API key |

## SDK Examples

### Python

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# Analyze biomarkers
response = client.post("/analyze/structured", json={
    "biomarkers": {"Glucose": 140, "HbA1c": 10.0}
})
analysis = response.json()

# Ask question
response = client.post("/ask", json={
    "question": "What causes diabetes?"
})
answer = response.json()
```

### JavaScript

```javascript
const client = http.createClient({
  baseURL: 'http://localhost:8000'
});

// Analyze biomarkers
const analysis = await client.post('/analyze/structured', {
  biomarkers: { Glucose: 140, HbA1c: 10.0 }
});

// Stream response
const stream = await client.post('/ask/stream', {
  question: 'Explain diabetes',
  stream: true
});

for await (const chunk of stream) {
  if (chunk.type === 'token') {
    process.stdout.write(chunk.content);
  }
}
```

### cURL

```bash
# Analyze biomarkers
curl -X POST http://localhost:8000/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "biomarkers": {"Glucose": 140, "HbA1c": 10.0}
  }'

# Ask question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the symptoms of diabetes?"
  }'
```

## Rate Limiting

- **Development**: No limits
- **Production**: 1000 requests per hour per API key

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642790400
```

## Data Models

### Biomarker Analysis Request

```typescript
interface BiomarkerAnalysisRequest {
  biomarkers: Record<string, number>;
  patient_context?: {
    age?: number;
    gender?: "male" | "female" | "other";
    symptoms?: string[];
    medications?: string[];
    medical_history?: string[];
  };
}
```

### Biomarker Analysis Response

```typescript
interface BiomarkerAnalysisResponse {
  status: "success" | "error";
  analysis?: {
    primary_findings: Finding[];
    critical_alerts: Alert[];
    recommendations: Recommendation[];
    biomarker_flags: BiomarkerFlag[];
  };
  metadata?: {
    timestamp: string;
    model_version: string;
    processing_time: number;
  };
}
```

## API Changelog

### v2.0.0 (Current)
- Added multi-agent workflow
- Improved confidence scoring
- Added streaming responses
- Enhanced error handling

### v1.5.0
- Added natural language analysis
- Improved biomarker normalization
- Added batch processing

### v1.0.0
- Initial release
- Basic biomarker analysis
- Medical Q&A

## Support

For API support:
- Documentation: https://docs.mediguard-ai.com
- Email: api-support@mediguard-ai.com
- GitHub Issues: https://github.com/yourusername/Agentic-RagBot/issues
