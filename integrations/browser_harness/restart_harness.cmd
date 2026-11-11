@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart_harness.ps1"
if errorlevel 1 pause
