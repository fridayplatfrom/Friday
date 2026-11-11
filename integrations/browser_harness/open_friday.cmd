@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0open_friday.ps1"
exit /b %errorlevel%
