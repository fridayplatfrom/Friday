@echo off
setlocal

echo ========================================================
echo   DEEPSEEK HARNESS - STANDARD BROWSER PROFILE
echo ========================================================

set "DSH_BIN=%LOCALAPPDATA%\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd"
if not exist "%DSH_BIN%" (
    echo Error: DeepSeek Harness CLI not found at "%DSH_BIN%"
    exit /b 1
)

rem Preserve the user's profile. Do not reinstall the Tiny Expert adapter.
echo Starting DeepSeek Harness Web Profile on port 3030...
call "%DSH_BIN%" --profile web --port 3030 --host 127.0.0.1
