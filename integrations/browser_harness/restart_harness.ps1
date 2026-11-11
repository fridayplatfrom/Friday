$ErrorActionPreference = 'Stop'
$taskDsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
if (-not (Test-Path -LiteralPath $taskDsh)) { throw 'Installed Harness CLI was not found.' }
$taskConnection = Get-Content (Join-Path $env:USERPROFILE '.dsh\browser-connector\connection.json') -Raw | ConvertFrom-Json
$taskListener = Get-NetTCPConnection -LocalPort 3030 -State Listen -ErrorAction SilentlyContinue
if ($taskListener) {
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskListener[0].OwningProcess)"
    if ($taskProcess.CommandLine -notmatch 'dsh-desktop-host.+--profile web --port 3030 --host 127.0.0.1') { throw 'Port 3030 belongs to another application; nothing was stopped.' }
    $taskStatus = Invoke-RestMethod "http://127.0.0.1:$($taskConnection.port)/status" -TimeoutSec 4 -Headers @{ Authorization = ('Bearer ' + $taskConnection.token) }
    if ($taskStatus.pending -ne 0) { throw 'A website request is active. Finish or cancel it before restarting.' }
    $taskBrowserControl = Join-Path $env:USERPROFILE '.dsh\browser-connector\workspace-browser-control.json'
    if (Test-Path -LiteralPath $taskBrowserControl) {
        $taskBrowser = Get-Content -LiteralPath $taskBrowserControl -Raw | ConvertFrom-Json
        if (-not ($taskBrowser.port -is [long] -or $taskBrowser.port -is [int]) -or $taskBrowser.port -lt 1 -or $taskBrowser.port -gt 65535) { throw 'Invalid workspace browser control port.' }
        if ($taskBrowser.protocolVersion -ge 1) {
            $null = Invoke-RestMethod "http://127.0.0.1:$($taskBrowser.port)/checkpoint" -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 30 -Headers @{ Authorization = ('Bearer ' + $taskBrowser.token) }
        }
    }
    Stop-Process -Id $taskProcess.ProcessId
    Wait-Process -Id $taskProcess.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
}
$taskLogs = Join-Path $env:USERPROFILE '.dsh\logs'
New-Item -ItemType Directory -Force -Path $taskLogs | Out-Null
$taskStamp = Get-Date -Format yyyyMMdd-HHmmss
Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', ('""' + $taskDsh + '" --profile web --port 3030 --host 127.0.0.1 --no-open"')) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogs "browser-$taskStamp.out.log") -RedirectStandardError (Join-Path $taskLogs "browser-$taskStamp.err.log")
Write-Host 'Harness is starting. Refresh its existing browser tab in a few seconds.'
Write-Host 'If owner authentication is required, run open_friday.cmd to reopen the current native sign-in link.'
