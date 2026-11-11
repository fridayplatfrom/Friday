@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create .venv and install dependencies using the README instructions first.
  exit /b 1
)
".venv\Scripts\python.exe" web_app.py
pause
