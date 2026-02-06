# Start RagBot API Server
# Run from RagBot root directory

Write-Host "Starting RagBot API Server..." -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Ollama
try {
    $ollama = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -ErrorAction Stop
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama is not running!" -ForegroundColor Red
    Write-Host "  Start with: ollama serve" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to continue anyway or Ctrl+C to exit"
}

# Check vector store
if (Test-Path "data\vector_stores\medical_knowledge.faiss") {
    Write-Host "✓ Vector store found" -ForegroundColor Green
} else {
    Write-Host "✗ Vector store not found!" -ForegroundColor Red
    Write-Host "  Run: python src/pdf_processor.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Set PYTHONPATH to include current directory
$env:PYTHONPATH = "$PWD;$PWD\api"

# Change to api directory but keep PYTHONPATH
Set-Location api

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
