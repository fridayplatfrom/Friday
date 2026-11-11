$ErrorActionPreference = 'Stop'
$taskDsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
$taskProfile = Join-Path $env:USERPROFILE '.dsh\profiles\web\cordis.patch.yml'
$taskOriginal = [IO.File]::ReadAllText($taskProfile)
$taskBase = [regex]::Replace($taskOriginal, '(?ms)^# BEGIN FRIDAY NATIVE COMPACTION\r?\n.*?^# END FRIDAY NATIVE COMPACTION\r?\n?', '')
$taskBackupRoot = Join-Path $env:USERPROFILE '.dsh\browser-connector\backups'
New-Item -ItemType Directory -Force -Path $taskBackupRoot | Out-Null
$taskBackup = Join-Path $taskBackupRoot ('before-native-compaction-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.yml')
[IO.File]::WriteAllText($taskBackup, $taskOriginal)
$taskSuccess = $false
try {
    [IO.File]::WriteAllText($taskProfile, $taskBase)
    $taskBefore = (& $taskDsh --profile web --dump-config | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the current Harness profile.' }
    $taskGenerated = ($taskBefore | & node (Join-Path $PSScriptRoot 'native-compaction-patch.mjs') | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Native compaction policy generation failed; original profile restored.' }
    [IO.File]::WriteAllText($taskProfile, $taskBase.TrimEnd() + "`n" + $taskGenerated)
    $taskAfter = (& $taskDsh --profile web --dump-config | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Native Harness configuration validation failed.' }
    foreach ($taskId in @('preset-standard','preset-ptc','preset-minimal','preset-cordis')) {
        $taskPattern = '(?ms)^- id: ' + $taskId + '\r?\n.*?(?=^- |\z)'
        $taskBeforeBlock = [regex]::Match($taskBefore,$taskPattern).Value
        if (-not $taskBeforeBlock) { continue }
        $taskAfterBlock = [regex]::Match($taskAfter,$taskPattern).Value
        $taskIdsBefore = ([regex]::Matches($taskBeforeBlock,'(?m)^\s+- id:.*$') | ForEach-Object {$_.Value.Trim()}) -join "`n"
        $taskIdsAfter = ([regex]::Matches($taskAfterBlock,'(?m)^\s+- id:.*$') | ForEach-Object {$_.Value.Trim()}) -join "`n"
        if ($taskIdsBefore -ne $taskIdsAfter -or -not $taskAfterBlock.Contains('headroomTokens: 4096')) {
            throw "Native plugin preservation check failed for $taskId."
        }
    }
    $taskSuccess = $true
    Write-Output 'Configured native Harness auto-compaction for Friday. Existing preset plugins were preserved. Restart Harness to activate.'
} finally {
    if (-not $taskSuccess) { [IO.File]::WriteAllText($taskProfile,$taskOriginal) }
}
