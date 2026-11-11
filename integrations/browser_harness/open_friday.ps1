$ErrorActionPreference = 'Stop'
# Reopen the native owner's current sign-in link. Never print or persist its token.
$taskListener = Get-NetTCPConnection -LocalPort 3030 -State Listen -ErrorAction SilentlyContinue
if (-not $taskListener) { throw 'Friday is not running. Start it first.' }
$taskHost = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskListener[0].OwningProcess)"
if ($taskHost.CommandLine -notmatch 'dsh-desktop-host.+--profile web --port 3030 --host 127.0.0.1') { throw 'Port 3030 is not the expected Friday host.' }
$taskLog = Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE '.dsh\logs') -Filter 'browser-*.out.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $taskLog) { throw 'The current Friday launch log was not found.' }
$taskText = Get-Content -LiteralPath $taskLog.FullName -Raw
$taskMatch = [regex]::Match($taskText, 'http://127\.0\.0\.1:3030/\?token=[^\s&#]+')
if (-not $taskMatch.Success) { throw 'The current native sign-in link was not found.' }
$taskUri = [Uri]$taskMatch.Value
if ($taskUri.Scheme -ne 'http' -or $taskUri.Host -ne '127.0.0.1' -or $taskUri.Port -ne 3030 -or $taskUri.AbsolutePath -ne '/' -or $taskUri.Query -notmatch '^\?token=[^&#\s]+$') { throw 'Unexpected native sign-in link.' }
$taskChrome = Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'
if (-not (Test-Path -LiteralPath $taskChrome)) { throw 'Chrome was not found in its installed location.' }
# This helper is deliberately user-invoked to open an interactive browser window.
Start-Process -FilePath $taskChrome -ArgumentList @('--new-tab', $taskUri.AbsoluteUri) -WindowStyle Normal
Write-Output 'Opened the current Friday sign-in in Chrome. Saved model chats and browser profiles remain available.'
