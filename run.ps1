$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$logDir = Join-Path $here 'state\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
& python main.py *>> (Join-Path $logDir 'run.stdout.log')
exit $LASTEXITCODE