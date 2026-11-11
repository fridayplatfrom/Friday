@echo off
setlocal
set "DSH_BIN=%LOCALAPPDATA%\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd"
if not exist "%DSH_BIN%" (
    echo DeepSeek Harness is not installed in the expected location.
    exit /b 1
)
if not exist "%USERPROFILE%\.dsh\browser-connector\connection.json" (
    echo Run setup.ps1 first.
    exit /b 1
)
call "%DSH_BIN%" --profile web --port 3030 --host 127.0.0.1
