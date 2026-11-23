param(
    [string]$Root = "D:\sases",
    [string]$TaskName = "SASES"
)

$ErrorActionPreference = "Stop"
$bat = Join-Path $Root "启动SASES.bat"
if (-not (Test-Path $bat)) {
    throw "未找到启动脚本：$bat"
}

$action = "cmd.exe /c `"$bat`""
schtasks.exe /Create /TN $TaskName /SC ONLOGON /RL LIMITED /TR $action /F | Out-Host
Write-Host "已创建登录自启动任务：$TaskName"
