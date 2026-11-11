$ErrorActionPreference='Stop'
$taskProfile=Join-Path $env:USERPROFILE '.dsh\profiles\web\cordis.patch.yml'
$taskDsh=Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
$taskOriginal=[IO.File]::ReadAllText($taskProfile)
$taskBackup=Join-Path $env:USERPROFILE ('.dsh\browser-connector\backups\before-friday-brand-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.yml')
New-Item -ItemType Directory -Force -Path (Split-Path $taskBackup)|Out-Null
[IO.File]::WriteAllText($taskBackup,$taskOriginal)
$taskUpdated=[regex]::Replace($taskOriginal,'(?ms)^# BEGIN FRIDAY BRAND\r?\n.*?^# END FRIDAY BRAND\r?\n?','')
$taskUpdated=$taskUpdated.TrimEnd()+"`n# BEGIN FRIDAY BRAND`n"
# Disable the two model adapters and account/official-brand UI, not owner authorization.
foreach($taskId in @('llm-deepseek','llm-deepseek-account','ui-settings-account','ui-brand-official','ui-deepseek-model-label-1017','session-log-deepseek','ui-settings-session-log')){
 $taskUpdated+="- id: $taskId`n  disabled: true`n"
}
$taskUpdated+="# END FRIDAY BRAND`n"
try{
 [IO.File]::WriteAllText($taskProfile,$taskUpdated)
 & $taskDsh --profile web --dump-config | Out-Null
 if($LASTEXITCODE -ne 0){throw 'Friday profile validation failed.'}
 Write-Output 'Friday branding and browser-only model catalog configured.'
 Write-Output ('Backup: '+$taskBackup)
}catch{[IO.File]::WriteAllText($taskProfile,$taskOriginal);throw}
