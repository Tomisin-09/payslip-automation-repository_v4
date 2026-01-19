$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- Check Python ---
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "Python launcher (py) not found. Install Python 3.10+ from python.org and re-run." -ForegroundColor Red
  Exit 1
}

# --- Create venv if missing ---
if (!(Test-Path ".venv")) {
  py -3 -m venv .venv
}

# --- Activate venv ---
& .\.venv\Scripts\Activate.ps1

# --- Install deps ---
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# --- Run ---
py -m src.main
