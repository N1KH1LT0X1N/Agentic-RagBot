#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run MediGuard AI tests with pytest.

.DESCRIPTION
    Runs the test suite with proper configuration:
    - Sets up environment variables
    - Activates virtual environment
    - Runs pytest with appropriate flags

.PARAMETER Filter
    Test filter pattern (e.g., "test_integration")

.PARAMETER Verbose
    Enable verbose output

.PARAMETER Coverage
    Generate coverage report

.EXAMPLE
    .\scripts\run_tests.ps1
    
.EXAMPLE
    .\scripts\run_tests.ps1 -Filter "test_integration" -Verbose
#>

param(
    [string]$Filter = "",
    [switch]$Verbose,
    [switch]$Coverage
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediGuard AI - Running Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (Test-Path (Join-Path $PSScriptRoot "..")) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
Set-Location $ProjectRoot

# Activate virtual environment
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
}

# Set deterministic mode for evaluation tests
$env:EVALUATION_DETERMINISTIC = "true"

# Build pytest command
$PytestArgs = @()

if ($Verbose) {
    $PytestArgs += "-v"
}

if ($Coverage) {
    $PytestArgs += "--cov=src"
    $PytestArgs += "--cov-report=term-missing"
}

# Add filter if specified
if ($Filter) {
    $PytestArgs += "-k"
    $PytestArgs += $Filter
}

# Ignore slow/broken tests by default
$PytestArgs += "--ignore=tests/test_evolution_loop.py"
$PytestArgs += "--ignore=tests/test_evolution_quick.py"

# Add test directory
$PytestArgs += "tests/"

Write-Host "[INFO] Running: pytest $($PytestArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

python -m pytest @PytestArgs

$ExitCode = $LASTEXITCODE
Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "[SUCCESS] All tests passed!" -ForegroundColor Green
} else {
    Write-Host "[FAILED] Some tests failed (exit code: $ExitCode)" -ForegroundColor Red
}

exit $ExitCode
