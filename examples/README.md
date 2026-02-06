# Examples Directory

Integration examples for RagBot in different environments.

## Contents

### `test_website.html`
HTML example for integrating RagBot biomarker analysis into a web application.

**Features:**
- Form-based biomarker input
- JavaScript/fetch POST requests to RagBot API
- Real-time result display
- Responsive design

**Usage:**
```bash
1. Start API: python -m uvicorn api.app.main:app
2. Open: examples/test_website.html in browser
3. Enter biomarkers and submit
```

**Integration Points:**
- POST to `http://localhost:8000/api/v1/analyze`
- Handles JSON responses
- Displays analysis results

---

### `website_integration.js`
JavaScript utility library for integrating RagBot into web applications.

**Features:**
- Biomarker validation
- API request handling
- Response parsing
- Error handling

**Usage:**
```html
<script src="examples/website_integration.js"></script>

<script>
  const ragbot = new RagBotClient('http://localhost:8000');
  
  ragbot.analyze({
    biomarkers: {
      'Glucose': 140,
      'HbA1c': 10.0
    }
  }).then(result => {
    console.log('Analysis:', result);
  });
</script>
```

---

## Creating Your Own Integration

### For Web Applications

```javascript
// 1. Initialize client
const client = new RagBotClient('http://localhost:8000');

// 2. Get biomarkers from user form
const biomarkers = {
  'Glucose': parseFloat(document.getElementById('glucose').value),
  'HbA1c': parseFloat(document.getElementById('hba1c').value)
};

// 3. Call analysis endpoint
client.analyze({ biomarkers })
  .then(result => {
    // Display prediction
    console.log(`Disease: ${result.prediction.disease}`);
    console.log(`Confidence: ${result.prediction.confidence}`);
    
    // Show recommendations
    result.recommendations.immediate_actions.forEach(action => {
      console.log(`Action: ${action}`);
    });
  })
  .catch(error => console.error('Analysis failed:', error));
```

### For Mobile Apps (React Native)

```javascript
import fetch from 'react-native-fetch';

const analyzeBiomarkers = async (biomarkers) => {
  const response = await fetch(
    'http://ragbot-api.yourserver.com/api/v1/analyze',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ biomarkers })
    }
  );
  return response.json();
};

// Usage in component
const [result, setResult] = useState(null);
analyzeBiomarkers(userBiomarkers).then(setResult);
```

### For Python Applications

```python
import requests

API_URL = 'http://localhost:8000/api/v1'

biomarkers = {
    'Glucose': 140,
    'HbA1c': 10.0,
    'LDL Cholesterol': 150
}

response = requests.post(
    f'{API_URL}/analyze',
    json={'biomarkers': biomarkers}
)

result = response.json()
print(f"Disease: {result['prediction']['disease']}")
print(f"Confidence: {result['prediction']['confidence']}")
```

### For Server-Side (Node.js)

```javascript
const axios = require('axios');

async function analyzePatient(biomarkers) {
  try {
    const response = await axios.post(
      'http://localhost:8000/api/v1/analyze',
      { biomarkers }
    );
    return response.data;
  } catch (error) {
    console.error('API Error:', error.response.data);
  }
}

// Usage
const result = await analyzePatient({
  'Glucose': 140,
  'HbA1c': 10.0
});
```

---

## Deployment Scenarios

### Scenario 1: Web Dashboard

```
Healthcare Portal (React/Vue)
         ↓
   RagBot API (FastAPI)
         ↓
   Multi-Agent Workflow
         ↓
   FAISS Vector Store + Groq LLM
```

### Scenario 2: Mobile App

```
Mobile App (React Native/Flutter)
         ↓
   RagBot API (Cloud Deployment)
         ↓
   Multi-Agent Workflow
         ↓
   FAISS Vector Store + Groq LLM
```

### Scenario 3: EHR Integration

```
Electronic Health Record System
         ↓
   RagBot Embedded Library
         ↓
   Multi-Agent Workflow (in-process)
         ↓
   FAISS Vector Store + Groq/OpenAI LLM
```

---

## Configuration for Production

### CORS Setup

```python
# api/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

### Authentication

```javascript
// Add API key to requests
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${API_KEY}`
};

fetch('http://api.ragbot.com/api/v1/analyze', {
  method: 'POST',
  headers,
  body: JSON.stringify({ biomarkers })
});
```

### Rate Limiting

Configure in `api/app/main.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/analyze")
@limiter.limit("100/minute")
async def analyze(request: Request, ...):
    ...
```

---

## Testing Your Integration

### Basic Test

```bash
# 1. Start API
python -m uvicorn api.app.main:app

# 2. In another terminal, test endpoint
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "biomarkers": {
      "Glucose": 140,
      "HbA1c": 10.0
    }
  }'
```

### Load Testing

```bash
# Install Apache Bench
ab -n 100 -c 10 -p data.json \
   http://localhost:8000/api/v1/analyze
```

---

## Troubleshooting Integration Issues

### CORS Errors

**Problem:** "No 'Access-Control-Allow-Origin' header"

**Solution:** Configure CORS in API settings

### Connection Timeouts

**Problem:** Request hangs after 30 seconds

**Solution:** 
- Increase timeout
- Check API server logs
- Verify network connectivity

### Invalid Biomarker Names

**Problem:** "Invalid biomarker" error

**Solution:**
- Check `config/biomarker_references.json`
- Normalize names properly (case-sensitive)

---

For more information:
- [API Documentation](../docs/API.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Development Guide](../docs/DEVELOPMENT.md)
