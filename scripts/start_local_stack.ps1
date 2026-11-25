# Start the local SASES stack: Edge CDP + local SASES backend.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start_local_stack.ps1
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "local_stack.log"

function Write-Log($message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message"
    Add-Content -Path $log -Value $line -Encoding utf8
    Write-Output $line
}

function Test-LocalPort($port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}

if (-not (Test-LocalPort 9222)) {
    Write-Log "starting Edge CDP"
    & (Join-Path $PSScriptRoot "start_edge_cdp.ps1")
} else {
    Write-Log "Edge CDP already listening on 9222"
}

if (-not (Test-LocalPort 8001)) {
    Write-Log "starting local SASES"
    $python = Join-Path $root "venv312\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = "python"
    }
    Start-Process -FilePath $python -ArgumentList "scripts/run_forever.py" `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $root "local_run.out") `
        -RedirectStandardError (Join-Path $root "local_run.err")
} else {
    Write-Log "local SASES already listening on 8001"
}

Start-Sleep -Seconds 8
$cdp = Test-LocalPort 9222
$sases = Test-LocalPort 8001
Write-Log "cdp=$cdp sases=$sases"
if (-not ($cdp -and $sases)) { exit 1 }
