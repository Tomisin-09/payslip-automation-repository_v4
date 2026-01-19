@echo off
setlocal enableextensions
cd /d %~dp0

REM --- Check Python launcher ---
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher (py) not found. Install Python 3.10+ from python.org and re-run.
  exit /b 1
)

REM --- Create venv if missing ---
if not exist ".venv" (
  py -3 -m venv .venv
)

REM --- Activate venv ---
call .\.venv\Scripts\activate.bat

REM --- Install deps ---
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

REM --- Run ---
py -m src.main
endlocal
