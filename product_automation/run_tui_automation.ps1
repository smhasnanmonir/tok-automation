# TOK Product Automation - TUI Version
# Usage: python tui_automation.py
#
# This version includes:
# - Auto-login by sending OTP to monirhasnan@gmail.com
# - Visual progress display
# - Excel file selection
# - Manual OTP entry
#
# Prerequisites:
# 1. Python 3.11+ installed
# 2. Backend running at https://backend.tokbd.com (production)
# 3. OpenRouter API key configured in .env
# 4. Email for OTP configured in .env

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "TOK Product Automation - TUI Version" -ForegroundColor Cyan
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
Write-Host "Python found: $pythonVersion" -ForegroundColor Green

# Check for .env file
Write-Host "Checking .env configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it" -ForegroundColor Red
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Please edit it with your settings." -ForegroundColor Yellow
} else {
    Write-Host "OK: .env found" -ForegroundColor Green
}

# Check for Excel file
Write-Host "Checking Excel file..." -ForegroundColor Yellow
$excelPath = (Get-Content .env).Where({$_ -match 'EXCEL_FILE='}).Split('=')[1].Trim()
$absolutePath = Join-Path $PSScriptRoot $excelPath
if (-not (Test-Path $absolutePath)) {
    Write-Host "ERROR: Excel file not found" -ForegroundColor Red
    Write-Host "  Expected: $absolutePath" -ForegroundColor Yellow
    Write-Host "  Please set the correct EXCEL_FILE path in .env" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "OK: Excel file found: $excelPath" -ForegroundColor Green
}

# Check for python and pip
Write-Host "Checking Python dependencies..." -ForegroundColor Yellow
if (-not (python -m pip --version 2>&1)) {
    Write-Host "ERROR: pip is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "OK: pip found" -ForegroundColor Green

# Install dependencies if needed
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting TUI Automation..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location -LiteralPath $PSScriptRoot

# Run the TUI automation
python tui_automation.py
