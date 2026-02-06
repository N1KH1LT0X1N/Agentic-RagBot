# Test RagBot API Endpoints
# Run this while the API server is running

$baseUrl = "http://localhost:8000"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RagBot API Test Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Root endpoint
Write-Host "Test 1: Root endpoint" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method GET
    Write-Host "✓ Root endpoint OK" -ForegroundColor Green
    Write-Host "  Version: $($response.version)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 2: Health check
Write-Host "Test 2: Health check" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/health" -Method GET
    Write-Host "✓ Health check OK" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    Write-Host "  RagBot: $($response.ragbot_initialized)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Biomarkers list
Write-Host "Test 3: Biomarkers list" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/biomarkers" -Method GET
    Write-Host "✓ Biomarkers endpoint OK" -ForegroundColor Green
    Write-Host "  Total biomarkers: $($response.biomarkers.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 4: Example analysis
Write-Host "Test 4: Example analysis (diabetes case)" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/example" -Method GET
    Write-Host "✓ Example endpoint OK" -ForegroundColor Green
    Write-Host "  Request ID: $($response.request_id)" -ForegroundColor Gray
    Write-Host "  Predicted disease: $($response.analysis.prediction.predicted_disease)" -ForegroundColor Gray
    Write-Host "  Confidence: $($response.analysis.prediction.confidence)" -ForegroundColor Gray
    Write-Host "  Processing time: $($response.processing_time_ms)ms" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 5: Structured analysis
Write-Host "Test 5: Structured analysis (POST)" -ForegroundColor Yellow
try {
    $body = @{
        biomarkers = @{
            glucose = 180
            hba1c = 8.2
            ldl = 145
            hdl = 35
            triglycerides = 220
        }
        patient_context = @{
            age = 55
            gender = "male"
            bmi = 28.5
        }
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/analyze/structured" `
        -Method Post `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "✓ Structured analysis OK" -ForegroundColor Green
    Write-Host "  Request ID: $($response.request_id)" -ForegroundColor Gray
    Write-Host "  Predicted disease: $($response.analysis.prediction.predicted_disease)" -ForegroundColor Gray
    Write-Host "  Confidence: $($response.analysis.prediction.confidence)" -ForegroundColor Gray
    Write-Host "  Biomarker flags: $($response.analysis.biomarker_flags.Count)" -ForegroundColor Gray
    Write-Host "  Safety alerts: $($response.analysis.safety_alerts.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Testing complete!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "For JavaScript/Fetch usage in your website:" -ForegroundColor Yellow
Write-Host ""
Write-Host @"
// Example: Fetch from your website
fetch('http://localhost:8000/api/v1/example')
  .then(response => response.json())
  .then(data => {
    console.log('Predicted disease:', data.analysis.prediction.predicted_disease);
    console.log('Confidence:', data.analysis.prediction.confidence);
    console.log('Full response:', data);
  })
  .catch(error => console.error('Error:', error));

// Example: POST structured analysis
fetch('http://localhost:8000/api/v1/analyze/structured', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    biomarkers: {
      glucose: 180,
      hba1c: 8.2,
      ldl: 145
    },
    patient_context: {
      age: 55,
      gender: 'male'
    }
  })
})
  .then(response => response.json())
  .then(data => console.log('Analysis:', data))
  .catch(error => console.error('Error:', error));
"@ -ForegroundColor Gray
