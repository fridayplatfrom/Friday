@echo off
setlocal
set "HARNESS_TEST_CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "HARNESS_TEST_PROFILE=%USERPROFILE%\.dsh\browser-connector\chrome-debug-profile"
if not exist "%HARNESS_TEST_CHROME%" (
    echo Google Chrome was not found at the expected installation path.
    pause
    exit /b 1
)
echo Opening Chrome with a separate Harness test profile.
echo Debugging endpoint: http://127.0.0.1:9222
echo This does not close or reuse your normal Chrome profile.
start "" "%HARNESS_TEST_CHROME%" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="%HARNESS_TEST_PROFILE%" --no-first-run --no-default-browser-check http://127.0.0.1:3030/
endlocal
