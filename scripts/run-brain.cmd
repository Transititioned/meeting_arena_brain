@echo off
setlocal

cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

"%PYTHON%" -c "import fastapi, uvicorn, httpx, pydantic" >nul 2>nul
if errorlevel 1 (
  echo Dependencies are not installed. Run:
  echo python -m venv .venv
  echo .venv\Scripts\activate
  echo pip install -r requirements.txt
  exit /b 1
)

"%PYTHON%" -m uvicorn arena_brain.server:app --host 127.0.0.1 --port 8765

