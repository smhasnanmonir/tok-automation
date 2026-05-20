# TOK Product Automation Runner Script
# Usage: .\run_automation.ps1
#
# Prerequisites:
# 1. Python 3.11+ installed
# 2. Backend running at http://localhost:8787
# 3. Admin token configured in .env
# 4. OpenRouter API key configured in .env
#
# Steps:
# 1. Copy .env.example to .env
# 2. Edit .env with your configuration
# 3. Run: pip install -r requirements.txt
# 4. Run this script

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "TOK Product Automation" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check for Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green

# Check for .env file
Write-Host "Checking .env configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it" -ForegroundColor Red
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Please edit it with your settings." -ForegroundColor Yellow
} else {
    Write-Host "✓ .env found" -ForegroundColor Green
}

# Check for Excel file
Write-Host "Checking Excel file..." -ForegroundColor Yellow
if (-not (Test-Path "products.xlsx")) {
    $excelPath = (Get-Content .env).Where({$_ -match 'EXCEL_FILE='}).Split('=')[1].Trim()
    $absPath = Join-Path $PSScriptRoot $excelPath
    if (-not (Test-Path $absPath)) {
        Write-Host "ERROR: Excel file not found" -ForegroundColor Red
        Write-Host "  Expected: $excelPath" -ForegroundColor Yellow
        Write-Host "  Please set the correct EXCEL_FILE path in .env" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✓ products.xlsx found" -ForegroundColor Green
}

# Check for python and pip
Write-Host "Checking Python dependencies..." -ForegroundColor Yellow
if (-not (python -m pip --version 2>&1)) {
    Write-Host "ERROR: pip is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ pip found" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting Product Automation..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location -LiteralPath $PSScriptRoot

# Run the automation
python product_automation.py
