# Start Microsoft Edge with a local CDP endpoint for SASES browser tasks.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start_edge_cdp.ps1
$ErrorActionPreference = "Stop"

$port = 9222
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$profile = Join-Path $env:LOCALAPPDATA "Microsoft\Edge\User Data"

if (-not (Test-Path $edge)) {
    throw "Microsoft Edge not found: $edge"
}

$listening = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
if ($listening) {
    Write-Output "CDP already listening on $port"
    exit 0
}

Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
Start-Process -FilePath $edge -ArgumentList @(
    "--remote-debugging-port=$port",
    "--user-data-dir=$profile",
    "--restore-last-session",
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
