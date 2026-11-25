# Start Microsoft Edge with a local CDP endpoint for SASES browser tasks.
# Uses a dedicated profile so the user's normal Edge tabs are never closed.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start_edge_cdp.ps1 [-Force]
param([switch]$Force)
$ErrorActionPreference = "Stop"

$port = 9222
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$profile = "C:\edge_sases_profile"

if (-not (Test-Path $edge)) {
    throw "Microsoft Edge not found: $edge"
}

$listening = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
if ($listening -and -not $Force) {
    Write-Output "CDP already listening on $port"
    exit 0
}

if ($listening) {
    # Stop only the process holding the CDP port; leave normal Edge tabs alone.
    $ownerPid = ($listening | Select-Object -First 1).OwningProcess
    if ($ownerPid) {
        Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

Start-Process -FilePath $edge -ArgumentList @(
    "--remote-debugging-port=$port",
    "--user-data-dir=$profile",
    "--profile-directory=Default",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
)

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/json/version" -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Output "CDP ready on $port"
            exit 0
        }
    } catch {
        # keep waiting
    }
}

throw "Edge CDP did not start on $port"
