# ai-news-briefing skill entry: run the full briefing via Codex CLI
# Uses the native codex.exe (avoids the npm node wrapper hanging).
# Start-Process without output redirection: codex's own children inherit the
# handles, so redirecting would lock log files / block pipe EOF. Instead we
# rely on codex -o to capture the final report and on the project's own logs.
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$proj = 'D:\hermes_agent\workspace\hermes-ai-news'
$logDir = Join-Path $proj 'state\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdoutLog = Join-Path $logDir 'skill-run.stdout.log'
$reportFile = Join-Path $logDir 'skill-run.report.txt'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

function Append-Log([string]$path, [string]$text) {
    try {
        [System.IO.File]::AppendAllText($path, $text + [Environment]::NewLine, [System.Text.Encoding]::UTF8)
    } catch { }
}

Append-Log $stdoutLog ("==== skill run start " + $stamp + " ====")

# Locate the newest native codex.exe; fall back to codex.cmd on PATH
$codexBin = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin') -Filter codex.exe -Recurse -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($codexBin) {
    $codex = $codexBin.FullName
}
else {
    $cmd = Get-Command codex.cmd -ErrorAction SilentlyContinue
    if (-not $cmd) { throw 'codex CLI not found' }
    $codex = $cmd.Source
}
Append-Log $stdoutLog ("codex: " + $codex)

$prompt = 'Run the ai-news-briefing skill and execute the full daily AI news briefing in D:\hermes_agent\workspace\hermes-ai-news: fetch all sources, dedupe, translate to Chinese, render HTML, deploy to GitHub Pages, send the Feishu message. Execute directly without asking the user, then briefly report the result.'

$argStr = 'exec --ephemeral --skip-git-repo-check -C "' + $proj + '" --sandbox danger-full-access --dangerously-bypass-approvals-and-sandbox -o "' + $reportFile + '" "' + $prompt + '"'

# 40-minute watchdog; the native exe exits on its own, this only guards against hangs
$timeoutMs = 2400000
$p = Start-Process -FilePath $codex -ArgumentList $argStr -NoNewWindow -PassThru
if (-not $p.WaitForExit($timeoutMs)) {
    try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch { }
    Append-Log $stdoutLog ("==== skill run TIMEOUT killed at " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + " ====")
    exit 124
}
$code = 0
try { $code = $p.ExitCode } catch { }
if ($null -eq $code) { $code = 0 }

if (Test-Path $reportFile) {
    try {
        [System.IO.File]::AppendAllText($stdoutLog, [System.IO.File]::ReadAllText($reportFile, [System.Text.Encoding]::UTF8) + [Environment]::NewLine, [System.Text.Encoding]::UTF8)
    } catch { }
    Remove-Item $reportFile -ErrorAction SilentlyContinue
}

Append-Log $stdoutLog ("==== skill run end " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + " exit=" + $code + " ====")
exit $code