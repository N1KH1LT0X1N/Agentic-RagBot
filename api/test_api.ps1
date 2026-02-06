# RagBot API - Quick Start Script (PowerShell)
# Tests all API endpoints

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RagBot API - Quick Test Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$BASE_URL = "http://localhost:8000"

# Check if API is running
Write-Host "1. Checking if API is running..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/" -Method Get
    Write-Host "   ✓ API is online" -ForegroundColor Green
    Write-Host "   Version: $($response.version)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ API is not running!" -ForegroundColor Red
    Write-Host "   Start with: python -m uvicorn app.main:app --port 8000" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Health Check
Write-Host "2. Health Check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BASE_URL/api/v1/health" -Method Get
    Write-Host "   Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Ollama: $($health.ollama_status)" -ForegroundColor Gray
    Write-Host "   Vector Store: $($health.vector_store_loaded)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Health check failed: $_" -ForegroundColor Red
}

Write-Host ""

# List Biomarkers
Write-Host "3. Fetching Biomarkers List..." -ForegroundColor Yellow
try {
    $biomarkers = Invoke-RestMethod -Uri "$BASE_URL/api/v1/biomarkers" -Method Get
    Write-Host "   ✓ Found $($biomarkers.total_count) biomarkers" -ForegroundColor Green
    Write-Host "   Examples: Glucose, HbA1c, Cholesterol, Hemoglobin..." -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Failed to fetch biomarkers: $_" -ForegroundColor Red
}

Write-Host ""

# Test Example Endpoint
Write-Host "4. Testing Example Endpoint..." -ForegroundColor Yellow
try {
    $example = Invoke-RestMethod -Uri "$BASE_URL/api/v1/example" -Method Get
    Write-Host "   ✓ Example analysis completed" -ForegroundColor Green
    Write-Host "   Request ID: $($example.request_id)" -ForegroundColor Gray
    Write-Host "   Prediction: $($example.prediction.disease) ($([math]::Round($example.prediction.confidence * 100))% confidence)" -ForegroundColor Gray
    Write-Host "   Processing Time: $([math]::Round($example.processing_time_ms))ms" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Example analysis failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test Structured Analysis
Write-Host "5. Testing Structured Analysis..." -ForegroundColor Yellow
$structuredRequest = @{
    biomarkers = @{
        Glucose = 140
        HbA1c = 7.5
    }
    patient_context = @{
        age = 45
        gender = "female"
    }
} | ConvertTo-Json

try {
    $structured = Invoke-RestMethod -Uri "$BASE_URL/api/v1/analyze/structured" -Method Post -Body $structuredRequest -ContentType "application/json"
    Write-Host "   ✓ Structured analysis completed" -ForegroundColor Green
    Write-Host "   Request ID: $($structured.request_id)" -ForegroundColor Gray
    Write-Host "   Prediction: $($structured.prediction.disease) ($([math]::Round($structured.prediction.confidence * 100))% confidence)" -ForegroundColor Gray
    Write-Host "   Biomarker Flags: $($structured.analysis.biomarker_flags.Count)" -ForegroundColor Gray
    Write-Host "   Safety Alerts: $($structured.analysis.safety_alerts.Count)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Structured analysis failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test Natural Language Analysis (requires Ollama)
Write-Host "6. Testing Natural Language Analysis..." -ForegroundColor Yellow
$naturalRequest = @{
    message = "My glucose is 165 and HbA1c is 7.8"
    patient_context = @{
        age = 50
        gender = "male"
    }
} | ConvertTo-Json

try {
    $natural = Invoke-RestMethod -Uri "$BASE_URL/api/v1/analyze/natural" -Method Post -Body $naturalRequest -ContentType "application/json"
    Write-Host "   ✓ Natural language analysis completed" -ForegroundColor Green
    Write-Host "   Request ID: $($natural.request_id)" -ForegroundColor Gray
    Write-Host "   Extracted: $($natural.extracted_biomarkers.Keys -join ', ')" -ForegroundColor Gray
    Write-Host "   Prediction: $($natural.prediction.disease) ($([math]::Round($natural.prediction.confidence * 100))% confidence)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Natural language analysis failed: $_" -ForegroundColor Red
    Write-Host "   Make sure Ollama is running: ollama serve" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✓ Test Suite Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Documentation: $BASE_URL/docs" -ForegroundColor Cyan
Write-Host "ReDoc: $BASE_URL/redoc" -ForegroundColor Cyan
Write-Host ""
