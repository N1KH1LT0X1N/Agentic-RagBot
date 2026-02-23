<#
.SYNOPSIS
    Deploy MediGuard AI to Hugging Face Spaces
.DESCRIPTION
    This script automates the deployment of MediGuard AI to Hugging Face Spaces.
    It handles copying files, setting up the Dockerfile, and pushing to the Space.
.PARAMETER SpaceName
    Name of your Hugging Face Space (e.g., "mediguard-ai")
.PARAMETER Username
    Your Hugging Face username
.PARAMETER SkipClone
    Skip cloning if you've already cloned the Space
.EXAMPLE
    .\deploy_huggingface.ps1 -Username "your-username" -SpaceName "mediguard-ai"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$false)]
    [string]$SpaceName = "mediguard-ai",
    
    [switch]$SkipClone
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " MediGuard AI - Hugging Face Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DeployDir = Join-Path $ProjectRoot "hf-deploy"
$SpaceUrl = "https://huggingface.co/spaces/$Username/$SpaceName"

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host "Deploy Dir: $DeployDir" -ForegroundColor Gray
Write-Host "Space URL: $SpaceUrl" -ForegroundColor Gray
Write-Host ""

# Step 1: Clone or use existing Space
if (-not $SkipClone) {
    Write-Host "[1/6] Cloning Hugging Face Space..." -ForegroundColor Yellow
    
    if (Test-Path $DeployDir) {
        Write-Host "  Removing existing deploy directory..." -ForegroundColor Gray
        Remove-Item -Recurse -Force $DeployDir
    }
    
    git clone "https://huggingface.co/spaces/$Username/$SpaceName" $DeployDir
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to clone Space. Make sure it exists!" -ForegroundColor Red
        Write-Host "Create it at: https://huggingface.co/new-space" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[1/6] Using existing deploy directory..." -ForegroundColor Yellow
}

# Step 2: Copy project files
Write-Host "[2/6] Copying project files..." -ForegroundColor Yellow

# Core directories
$CoreDirs = @("src", "config", "data", "huggingface")
foreach ($dir in $CoreDirs) {
    $source = Join-Path $ProjectRoot $dir
    $dest = Join-Path $DeployDir $dir
    if (Test-Path $source) {
        Write-Host "  Copying $dir..." -ForegroundColor Gray
        Copy-Item -Path $source -Destination $dest -Recurse -Force
    }
}

# Copy specific files
$CoreFiles = @("pyproject.toml", ".dockerignore")
foreach ($file in $CoreFiles) {
    $source = Join-Path $ProjectRoot $file
    if (Test-Path $source) {
        Write-Host "  Copying $file..." -ForegroundColor Gray
        Copy-Item -Path $source -Destination (Join-Path $DeployDir $file) -Force
    }
}

# Step 3: Set up Dockerfile (HF Spaces expects it in root)
Write-Host "[3/6] Setting up Dockerfile..." -ForegroundColor Yellow
$HfDockerfile = Join-Path $DeployDir "huggingface/Dockerfile"
$RootDockerfile = Join-Path $DeployDir "Dockerfile"
Copy-Item -Path $HfDockerfile -Destination $RootDockerfile -Force
Write-Host "  Copied huggingface/Dockerfile to Dockerfile" -ForegroundColor Gray

# Step 4: Set up README with HF metadata
Write-Host "[4/6] Setting up README.md..." -ForegroundColor Yellow
$HfReadme = Join-Path $DeployDir "huggingface/README.md"
$RootReadme = Join-Path $DeployDir "README.md"
Copy-Item -Path $HfReadme -Destination $RootReadme -Force
Write-Host "  Copied huggingface/README.md to README.md" -ForegroundColor Gray

# Step 5: Verify vector store exists
Write-Host "[5/6] Verifying vector store..." -ForegroundColor Yellow
$VectorStore = Join-Path $DeployDir "data/vector_stores/medical_knowledge.faiss"
if (Test-Path $VectorStore) {
    $size = (Get-Item $VectorStore).Length / 1MB
    Write-Host "  Vector store found: $([math]::Round($size, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Vector store not found!" -ForegroundColor Red
    Write-Host "  Run 'python scripts/setup_embeddings.py' first to create it." -ForegroundColor Yellow
}

# Step 6: Commit and push
Write-Host "[6/6] Committing and pushing to Hugging Face..." -ForegroundColor Yellow

Push-Location $DeployDir

git add .
git commit -m "Deploy MediGuard AI - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

Write-Host ""
Write-Host "Ready to push! Run the following command:" -ForegroundColor Green
Write-Host ""
Write-Host "  cd $DeployDir" -ForegroundColor Cyan
Write-Host "  git push" -ForegroundColor Cyan
Write-Host ""
Write-Host "After pushing, add your API key as a Secret in Space Settings:" -ForegroundColor Yellow
Write-Host "  Name: GROQ_API_KEY  (or GOOGLE_API_KEY)" -ForegroundColor Gray
Write-Host "  Value: your-api-key" -ForegroundColor Gray
Write-Host ""
Write-Host "Your Space will be live at:" -ForegroundColor Green
Write-Host "  $SpaceUrl" -ForegroundColor Cyan

Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Deployment prepared successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
