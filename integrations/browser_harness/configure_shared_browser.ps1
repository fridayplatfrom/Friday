$ErrorActionPreference='Stop'
$taskProfile=Join-Path $env:USERPROFILE '.dsh\profiles\web\cordis.patch.yml'
$taskRoot=Join-Path $env:USERPROFILE '.dsh\browser-connector'
$taskDsh=Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
$taskOriginal=[IO.File]::ReadAllText($taskProfile)
$taskBackup=Join-Path $taskRoot ('backups\before-shared-browser-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.yml')
New-Item -ItemType Directory -Force -Path (Split-Path $taskBackup)|Out-Null
[IO.File]::WriteAllText($taskBackup,$taskOriginal)
$taskSuccess=$false
try {
 $taskBefore=(& $taskDsh --profile web --dump-config|Out-String);if($LASTEXITCODE -ne 0){throw 'Existing native profile is invalid.'}
 $taskUpdated=($taskOriginal|& node (Join-Path $PSScriptRoot 'shared-browser-config.mjs') ((Join-Path $PSScriptRoot 'shared-browser-mcp.mjs').Replace('\','/')) ((Join-Path $taskRoot 'friday-browser-profile').Replace('\','/'))|Out-String)
 if($LASTEXITCODE -ne 0){throw 'Shared browser migration failed; existing profile preserved.'}
 [IO.File]::WriteAllText($taskProfile,$taskUpdated)
 $taskAfter=(& $taskDsh --profile web --dump-config|Out-String);if($LASTEXITCODE -ne 0){throw 'Native profile validation failed.'}
 $taskBeforeIds=([regex]::Matches($taskBefore,'(?m)^\s*- id:.*$')|ForEach-Object {$_.Value.Trim()})-join "`n"
 $taskAfterIds=([regex]::Matches($taskAfter,'(?m)^\s*- id:.*$')|ForEach-Object {$_.Value.Trim()})-join "`n"
 if($taskBeforeIds -ne $taskAfterIds){throw 'Native plugin preservation failed.'}
 $taskSuccess=$true
 Write-Output 'Prepared shared native Harness browser. Restart Harness to activate.'
 Write-Output ('Rollback profile backup: '+$taskBackup)
}finally{if(-not $taskSuccess){[IO.File]::WriteAllText($taskProfile,$taskOriginal)}}
