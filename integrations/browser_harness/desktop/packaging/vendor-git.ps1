param([string]$Stage=(Join-Path $PSScriptRoot '..\.packaging'))
$ErrorActionPreference='Stop'
$Stage=[IO.Path]::GetFullPath($Stage)
if(-not(Test-Path -LiteralPath (Join-Path $Stage 'build-context.json'))){throw 'Prepare the standalone stage first.'}
$gitVersion='2.56.1'
$gitHash='4a92850b6e917da4fd010669b614b55dccf5b0ec333a534cc4be4700dfefdafd'
$gitUrl="https://github.com/git-for-windows/git/releases/download/v$gitVersion.windows.1/MinGit-$gitVersion-64-bit.zip"
$gitZip=Join-Path $Stage "MinGit-$gitVersion-64-bit.zip"
$gitTarget=Join-Path $Stage 'resources\harness\runtime\git'
if(Test-Path -LiteralPath $gitTarget){throw 'Git payload already exists; inspect it before replacing it.'}
if(-not(Test-Path -LiteralPath $gitZip)){Invoke-WebRequest -Uri $gitUrl -OutFile $gitZip -UseBasicParsing}
if((Get-FileHash -LiteralPath $gitZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $gitHash){throw 'Git archive checksum mismatch. Nothing was extracted.'}
Expand-Archive -LiteralPath $gitZip -DestinationPath $gitTarget
$gitSource="Git for Windows MinGit $gitVersion`nBinary: $gitUrl`nSHA256: $gitHash`nSource and build instructions: https://github.com/git-for-windows/git/tree/v$gitVersion.windows.1`nhttps://github.com/git-for-windows/build-extra`nThe bundled distribution retains its license and third-party notices.`n"
[IO.File]::WriteAllText((Join-Path $gitTarget 'FRIDAY-SOURCE-NOTICE.txt'),$gitSource)
& (Join-Path $gitTarget 'cmd\git.exe') --version
if($LASTEXITCODE -ne 0){throw 'Bundled Git smoke test failed.'}
