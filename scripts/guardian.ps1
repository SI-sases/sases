param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [int]$IntervalSeconds = 60,
    [string]$LogPath = ""
)

$ErrorActionPreference = "Continue"
if (-not $LogPath) { $LogPath = Join-Path $Root "logs\guardian.log" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null

function Write-GuardianLog([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

$launcher = Join-Path $Root "SASES启动器.exe"
$console = Join-Path $Root "启动控制台.bat"

Write-GuardianLog "guardian start root=$Root interval=$IntervalSeconds"
$failures = 0

while ($true) {
    $healthy = $false
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8001/version" -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $healthy = $true }
    } catch {
        $healthy = $false
    }

    if ($healthy) {
        $failures = 0
    } else {
        $failures++
        $running = Get-Process -Name "SASES启动器" -ErrorAction SilentlyContinue
        if ($running -and $failures -ge 2) {
            Write-GuardianLog "sases down $failures times, restarting launcher"
            $running | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            $running = $null
        }
        if (-not $running) {
            if (Test-Path $launcher) {
                Write-GuardianLog "sases down, starting launcher"
                Start-Process -FilePath $launcher -WorkingDirectory $Root
                $failures = 0
            } elseif (Test-Path $console) {
                Write-GuardianLog "sases down, starting console"
                Start-Process -FilePath $console -WorkingDirectory $Root
                $failures = 0
            } else {
                Write-GuardianLog "sases down, no launcher/console found"
            }
        } elseif ($failures -lt 2) {
            Write-GuardianLog "sases down, launcher exists; failure $failures/2"
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
