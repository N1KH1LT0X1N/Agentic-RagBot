#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start MediGuard AI FastAPI server for local development.

.DESCRIPTION
    This script starts the FastAPI server with proper configuration
    for local development. It handles:
    - Environment variable loading from .env
    - Virtual environment activation
    - Server startup with uvicorn

.PARAMETER Port
    The port to run the server on (default: 8000)

.PARAMETER Host
    The host to bind to (default: 127.0.0.1)

.PARAMETER Reload
    Enable auto-reload on file changes (default: true)

.EXAMPLE
    .\scripts\start_server.ps1
    
.EXAMPLE
    .\scripts\start_server.ps1 -Port 8080 -Host 0.0.0.0
#>

param(
    [int]$Port = 8000,
    [string]$Host = "127.0.0.1",
    [bool]$Reload = $true
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediGuard AI - Starting Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (Test-Path (Join-Path $PSScriptRoot "..")) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
Set-Location $ProjectRoot
Write-Host "[INFO] Project root: $ProjectRoot" -ForegroundColor Gray

# Check for virtual environment
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvActivate = Join-Path $VenvPath "Scripts\Activate.ps1"

if (Test-Path $VenvActivate) {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Gray
    & $VenvActivate
} else {
    Write-Host "[WARN] No virtual environment found at .venv" -ForegroundColor Yellow
    Write-Host "[WARN] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    & $VenvActivate
    pip install -r requirements.txt
}

# Load .env file if present
$EnvFile = Join-Path $ProjectRoot ".env"
if (Test-Path $EnvFile) {
    Write-Host "[INFO] Loading environment from .env..." -ForegroundColor Gray
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$'
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Check for required API keys
$HasGroq = $env:GROQ_API_KEY
$HasGoogle = $env:GOOGLE_API_KEY

if (-not $HasGroq -and -not $HasGoogle) {
    Write-Host ""
    Write-Host "[WARN] No LLM API key found!" -ForegroundColor Yellow
    Write-Host "  Set GROQ_API_KEY or GOOGLE_API_KEY in .env file" -ForegroundColor Yellow
    Write-Host "  Get a free Groq key: https://console.groq.com/keys" -ForegroundColor Yellow
    Write-Host ""
}

# Check for FAISS index
$FaissIndex = Join-Path $ProjectRoot "data\vector_stores\medical_knowledge.faiss"
if (-not (Test-Path $FaissIndex)) {
    Write-Host ""
    Write-Host "[WARN] FAISS index not found!" -ForegroundColor Yellow
    Write-Host "  Run: python -m src.pdf_processor" -ForegroundColor Yellow
    Write-Host "  to create the vector store from PDFs" -ForegroundColor Yellow
    Write-Host ""
}

# Build uvicorn command
$ReloadFlag = if ($Reload) { "--reload" } else { "" }

Write-Host ""
Write-Host "[INFO] Starting server at http://${Host}:${Port}" -ForegroundColor Green
Write-Host "[INFO] API docs available at http://${Host}:${Port}/docs" -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Start the server
$UvicornArgs = @(
    "-m", "uvicorn",
    "src.main:app",
    "--host", $Host,
    "--port", $Port
)
if ($Reload) {
    $UvicornArgs += "--reload"
}

python @UvicornArgs
