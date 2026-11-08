# Starts the backend and frontend together, each in its own window.
#
#   Right-click -> "Run with PowerShell"
#   or, from this folder:  powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
#
# First run on a fresh clone installs anything missing. Close either window to
# stop that half.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

# --- backend dependencies ----------------------------------------------------
if (-not (Test-Path $python)) {
    Write-Host 'Creating backend virtual environment...' -ForegroundColor Cyan
    python -m venv (Join-Path $backend '.venv')
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $backend 'requirements.txt')
    # The headless browser the Daraz scraper falls back to.
    & $python -m playwright install chromium
}

# --- frontend dependencies ---------------------------------------------------
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host 'Installing frontend dependencies...' -ForegroundColor Cyan
    Push-Location $frontend
    npm install
    Pop-Location
}

# --- config reminder ---------------------------------------------------------
if (-not (Test-Path (Join-Path $backend '.env'))) {
    Write-Host 'No backend\.env found: the API will run in DEMO mode (no scraping, no database).' -ForegroundColor Yellow
    Write-Host 'Copy backend\.env.example to backend\.env and fill in Supabase to use it for real.' -ForegroundColor Yellow
}

# --- start both --------------------------------------------------------------
Write-Host 'Starting backend on http://127.0.0.1:8000 ...' -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$backend'; & '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Write-Host 'Starting frontend on http://localhost:5173 ...' -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$frontend'; npm run dev"
)

Write-Host ''
Write-Host 'Both are starting in their own windows. Open http://localhost:5173 in a few seconds.' -ForegroundColor Green
