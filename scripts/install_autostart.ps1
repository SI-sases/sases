param(
    [string]$Root = "D:\sases",
    [string]$TaskName = "SASES"
)

$ErrorActionPreference = "Stop"
$bat = Join-Path $Root "SASES-start.bat"
if (-not (Test-Path $bat)) {
    $candidate = Join-Path $Root "启动SASES.bat"
    if (Test-Path $candidate) { $bat = $candidate } else { throw "start script not found in $Root" }
}

$action = "cmd.exe /c `"$bat`""
schtasks.exe /Create /TN $TaskName /SC ONLOGON /RL LIMITED /TR $action /F | Out-Host
Write-Host "autostart task created: $TaskName"
