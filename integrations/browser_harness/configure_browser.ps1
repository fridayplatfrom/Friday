param([string[]]$Origins=@('http://127.0.0.1:8767','http://127.0.0.1:8010','https://images.unsplash.com','https://fonts.googleapis.com','https://fonts.gstatic.com'))
$ErrorActionPreference='Stop'
$taskDsh=Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
$taskProfile=Join-Path $env:USERPROFILE '.dsh\profiles\web\cordis.patch.yml'
$taskOriginal=[IO.File]::ReadAllText($taskProfile)
$taskBackupRoot=Join-Path $env:USERPROFILE '.dsh\browser-connector\backups'
New-Item -ItemType Directory -Force -Path $taskBackupRoot|Out-Null
$taskBackup=Join-Path $taskBackupRoot ('before-task-browser-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.yml')
[IO.File]::WriteAllText($taskBackup,$taskOriginal)
$taskSuccess=$false
try {
    $taskBefore=(& $taskDsh --profile web --dump-config|Out-String)
    if($LASTEXITCODE -ne 0){throw 'Native profile inspection failed.'}
    $taskUpdated=($taskOriginal|& node (Join-Path $PSScriptRoot 'browser-policy.mjs') @Origins|Out-String)
    if($LASTEXITCODE -ne 0){throw 'Native browser policy generation failed.'}
    [IO.File]::WriteAllText($taskProfile,$taskUpdated)
    $taskAfter=(& $taskDsh --profile web --dump-config|Out-String)
    if($LASTEXITCODE -ne 0){throw 'Native profile validation failed.'}
    $taskIdsBefore=([regex]::Matches($taskBefore,'(?m)^\s*- id:.*$')|ForEach-Object {$_.Value.Trim()})-join "`n"
    $taskIdsAfter=([regex]::Matches($taskAfter,'(?m)^\s*- id:.*$')|ForEach-Object {$_.Value.Trim()})-join "`n"
    if($taskIdsBefore -ne $taskIdsAfter){throw 'Native plugin preservation check failed.'}
    $taskSuccess=$true
    Write-Output 'Updated only the existing Harness browser origin policy. Restart Harness to activate.'
    Write-Output ('Backup: '+$taskBackup)
}finally{if(-not $taskSuccess){[IO.File]::WriteAllText($taskProfile,$taskOriginal)}}
