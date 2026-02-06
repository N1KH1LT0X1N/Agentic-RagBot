# RagBot API - Simple Startup Script
# Run from RagBot root directory

Write-Host "🚀 Starting RagBot API Server..." -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (!(Test-Path "api\app\main.py")) {
    Write-Host "❌ Error: Run this from RagBot root directory!" -ForegroundColor Red
    exit 1
}

# Check vector store
if (!(Test-Path "data\vector_stores\medical_knowledge.faiss")) {
    Write-Host "❌ Vector store not found!" -ForegroundColor Red
    Write-Host "   Run: python src/pdf_processor.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Vector store found" -ForegroundColor Green
Write-Host ""
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Start server
cd api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
