param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$guardian = Join-Path $Root "scripts\guardian.ps1"
if (-not (Test-Path $guardian)) { throw "guardian.ps1 not found: $guardian" }

$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$guardian`" -Root `"$Root`""
schtasks.exe /Create /TN "SASESGuardian" /SC ONLOGON /RL HIGHEST /TR $action /F
schtasks.exe /Run /TN "SASESGuardian"

# Remove the old HKCU Run entry; the scheduled task is the single autostart path.
reg.exe delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v SASES /f 2>$null

Write-Host "SASESGuardian installed"
Write-Host "Log: $Root\logs\guardian.log"
