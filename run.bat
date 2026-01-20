@echo on
setlocal EnableExtensions

cd /d "%~dp0"
echo Running from: %cd%

REM --- Sanity checks ---
if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found in %cd%
  pause
  exit /b 1
)

if not exist "src" (
  echo ERROR: src folder not found in %cd%
  pause
  exit /b 1
)

REM --- Python check ---
where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python launcher 'py' not found.
  echo Install Python from python.org and ensure "Python launcher" is enabled.
  pause
  exit /b 1
)

py --version

REM --- venv ---
if not exist ".venv" (
  echo Creating virtual environment...
  py -m venv .venv
)

REM --- install deps ---
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

REM --- run app (module form avoids 'No module named src') ---
".venv\Scripts\python.exe" -m src.main

echo Done.
pause
endlocal