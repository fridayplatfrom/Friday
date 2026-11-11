param([switch]$PrepareOnly, [switch]$WithBrowserTools, [switch]$AutoReloadDevelopment,
    [string[]]$BrowserAllowedOrigins=@('http://127.0.0.1:8767','http://127.0.0.1:8010','https://images.unsplash.com','https://fonts.googleapis.com','https://fonts.gstatic.com'),
    [ValidateSet('builtin','extension')][string]$BrowserMode = 'extension')
$ErrorActionPreference = 'Stop'
$taskSource = $PSScriptRoot
& node (Join-Path $taskSource 'build-provider-content.mjs')
if ($LASTEXITCODE -ne 0) { throw 'Provider contract build failed; extension was not copied.' }
$taskRoot = Join-Path $env:USERPROFILE '.dsh\browser-connector'
$taskExtension = Join-Path $taskRoot 'extension'
$taskConnection = Join-Path $taskRoot 'connection.json'
New-Item -ItemType Directory -Force -Path $taskExtension | Out-Null
if (-not (Test-Path -LiteralPath $taskConnection)) {
    $taskBytes = New-Object byte[] 32
    $taskRng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $taskRng.GetBytes($taskBytes) } finally { $taskRng.Dispose() }
    $taskToken = [Convert]::ToBase64String($taskBytes)
    $taskJson = @{ token = $taskToken; port = 8766 } | ConvertTo-Json
    [System.IO.File]::WriteAllText($taskConnection, $taskJson, (New-Object System.Text.UTF8Encoding($false)))
}
$taskPriorAutoReload = $false
if (Test-Path -LiteralPath (Join-Path $taskExtension 'bridge-config.json')) {
    try { $taskPriorAutoReload = (Get-Content -LiteralPath (Join-Path $taskExtension 'bridge-config.json') -Raw | ConvertFrom-Json).developmentAutoReload -eq $true } catch {}
}
Get-ChildItem -LiteralPath (Join-Path $taskSource 'extension') -File | Where-Object { $_.Name -ne 'manifest.json' } | Copy-Item -Destination $taskExtension -Force
Copy-Item -LiteralPath $taskConnection -Destination (Join-Path $taskExtension 'bridge-config.json') -Force
if ($AutoReloadDevelopment -or $taskPriorAutoReload) {
    $taskDevConfig = Get-Content -LiteralPath (Join-Path $taskExtension 'bridge-config.json') -Raw | ConvertFrom-Json
    $taskDevConfig | Add-Member -NotePropertyName developmentAutoReload -NotePropertyValue $true -Force
    [System.IO.File]::WriteAllText((Join-Path $taskExtension 'bridge-config.json'), ($taskDevConfig | ConvertTo-Json), (New-Object System.Text.UTF8Encoding($false)))
}
# Publish the version only after every extension file and local config is ready.
Copy-Item -LiteralPath (Join-Path $taskSource 'extension\manifest.json') -Destination $taskExtension -Force
if (-not $PrepareOnly) {
    $taskPatch = Join-Path $env:USERPROFILE '.dsh\profiles\web\cordis.patch.yml'
    if (-not (Test-Path -LiteralPath $taskPatch)) { throw 'Install and start the Harness web profile once before running setup.' }
    $taskBackup = Join-Path $taskRoot ('cordis-before-browser-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.yml')
    Copy-Item -LiteralPath $taskPatch -Destination $taskBackup
    $taskYaml = Get-Content -LiteralPath $taskPatch -Raw
    $taskUseBrowserTools = $WithBrowserTools -or $taskYaml -match '- id: harness-playwright'
    if ($taskYaml -match 'tiny-experts-native-llm|provider:\s*tiny-experts') {
        throw 'Remove the old Tiny Expert override before installing this provider. Existing profile was not changed.'
    }
    # Cordis stores top-level plugin entries beginning at column zero. Preserve
    # unrelated entries; replace only the default model and our previous entry.
    $taskYaml = [regex]::Replace($taskYaml, '(?ms)^# BEGIN HARNESS BROWSER CONNECTOR\r?\n.*?^# END HARNESS BROWSER CONNECTOR\r?\n?', '')
    $taskYaml = [regex]::Replace($taskYaml, '(?ms)^- id: (agent-default-model|harness-browser-provider)\r?\n.*?(?=^- |\z)', '')
    if ($taskYaml.Trim() -eq '[]') { $taskYaml = '' }
    $taskPlugin = (Join-Path $taskSource 'index.mjs').Replace('\', '/') | ConvertTo-Json -Compress
    $taskBrowserYaml = "`n      config:`n        browserMode: $BrowserMode`n"
    if ($BrowserMode -eq 'builtin' -and -not (Test-Path -LiteralPath (Join-Path $taskSource 'node_modules\playwright-core\index.mjs'))) {
        throw 'Run npm install in integrations/browser_harness before enabling the built-in browser.'
    }
    if ($taskUseBrowserTools) {
        $taskMcpCli = Join-Path $taskSource 'node_modules\@playwright\mcp\cli.js'
        if (-not (Test-Path -LiteralPath $taskMcpCli)) { throw 'Run npm install in integrations/browser_harness before enabling browser tools.' }
        $taskNode = (Get-Command node.exe -ErrorAction Stop).Source.Replace('\', '/') | ConvertTo-Json -Compress
        $taskMcpCliJson = (Join-Path $taskSource 'workspace-browser-mcp.mjs').Replace('\', '/') | ConvertTo-Json -Compress
        $taskChrome = (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe').Replace('\', '/') | ConvertTo-Json -Compress
        $taskOrigins=(& node (Join-Path $taskSource 'browser-policy.mjs') origins @BrowserAllowedOrigins|Out-String).Trim()
        if($LASTEXITCODE -ne 0){throw 'Invalid task browser origins. Profile was not changed.'}
        $taskOriginsJson=$taskOrigins|ConvertTo-Json -Compress
        $taskBrowserYaml += "        workspaceBrowser: true`n        demoForm: true`n    - id: harness-playwright`n      name: '@deepseek-ai/dsh-mcp-client'`n      config:`n        serverName: browser`n        transport: stdio`n        command: $taskNode`n        args: [$taskMcpCliJson, '--executable-path', $taskChrome, '--image-responses', 'allow', '--allowed-origins', $taskOriginsJson]`n        failOnStartupError: true`n"
    }
    $taskYaml = $taskYaml.TrimEnd() + "`n# BEGIN HARNESS BROWSER CONNECTOR`n- insert:`n    - id: harness-browser-provider`n      name: $taskPlugin$taskBrowserYaml`n- id: agent-default-model`n  name: '@deepseek-ai/dsh-agent-default-model'`n  config:`n    provider: browser-web`n    model: chatgpt-web`n# END HARNESS BROWSER CONNECTOR`n"
    [System.IO.File]::WriteAllText($taskPatch, $taskYaml, (New-Object System.Text.UTF8Encoding($false)))
    & node (Join-Path $taskSource 'native-question-config.mjs') $taskPatch
    if ($LASTEXITCODE -ne 0) { throw 'Native question configuration failed; restore the saved profile backup.' }
    Write-Output "Web profile updated. Backup: $taskBackup"
}
if ($BrowserMode -eq 'extension') {
    Write-Output "Chrome extension folder: $taskExtension"
    Write-Output 'Load that folder using chrome://extensions > Developer mode > Load unpacked.'
} else {
    Write-Output 'Built-in browser selected. No Chrome extension setup is needed.'
    Write-Output 'After starting Harness, open Settings > Models > Friday. Open a website, then Connect when its chat is ready.'
}
Write-Output 'Restart Harness with start_harness.cmd. No model API credentials are needed.'
