# RagBot API - Start Server
# Must be run from RagBot ROOT directory (not from api/ subdirectory)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RagBot API Server Startup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check we're in the right directory
if (!(Test-Path "api\app\main.py")) {
    Write-Host "ERROR: Must run from RagBot root directory!" -ForegroundColor Red
    Write-Host "Current directory: $PWD" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Fix: cd C:\Users\admin\OneDrive\Documents\GitHub\RagBot" -ForegroundColor Yellow
    exit 1
}

# Check Ollama
Write-Host "Checking Ollama..." -ForegroundColor Yellow
$ollamaRunning = $false
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠ Ollama not running" -ForegroundColor Yellow
    Write-Host "  Some features may not work without Ollama" -ForegroundColor Gray
    Write-Host "  Start with: ollama serve" -ForegroundColor Gray
}

# Check vector store
Write-Host "Checking vector store..." -ForegroundColor Yellow
if (Test-Path "data\vector_stores\medical_knowledge.faiss") {
    Write-Host "✓ Vector store ready" -ForegroundColor Green
} else {
    Write-Host "✗ Vector store missing!" -ForegroundColor Red
    Write-Host "  Run: python src/pdf_processor.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting API server..." -ForegroundColor Cyan
Write-Host "URL: http://localhost:8000" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Set Python path to include both root and api directories
$env:PYTHONPATH = "$PWD;$PWD\api;$env:PYTHONPATH"

# Start server from root directory (so relative paths work)
python -m uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
