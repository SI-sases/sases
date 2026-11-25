# Register the local SASES stack at user logon.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install_local_stack.ps1
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $PSScriptRoot "start_local_stack.ps1"
$task = "SASESLocalStack"
$command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""

schtasks /Create /TN $task /SC ONLOGON /TR $command /F /RL LIMITED | Out-Host
if ($LASTEXITCODE -eq 0) {
    schtasks /Query /TN $task /FO LIST | Out-Host
    exit 0
}

Write-Output "scheduled task unavailable; installing Startup shortcut"
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "SASESLocalStack.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$shortcut.WorkingDirectory = $root
$shortcut.WindowStyle = 7
$shortcut.Save()
Write-Output "startup shortcut: $shortcutPath"
