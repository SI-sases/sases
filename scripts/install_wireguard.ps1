param(
    [string]$InstallerUrl = "http://127.0.0.1:8001/static/downloads/wireguard-installer.exe",
    [string]$ConfigPath = "",
    [string]$WorkDir = "D:\sases"
)

$ErrorActionPreference = "Stop"
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "需要管理员权限，请右键“以管理员身份运行”。"
    exit 2
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$installer = Join-Path $WorkDir "wireguard-installer.exe"
if (-not (Test-Path $installer)) {
    Write-Host "下载 WireGuard 安装包..."
    curl.exe -L --fail -o $installer $InstallerUrl
}

Write-Host "安装 WireGuard..."
if ($installer.ToLower().EndsWith(".msi")) {
    Start-Process msiexec.exe -ArgumentList "/i `"$installer`" /qn /norestart" -Wait
} else {
    Start-Process $installer -ArgumentList "/S" -Wait
}

$wg = Join-Path $env:ProgramFiles "WireGuard\wireguard.exe"
if (-not (Test-Path $wg)) {
    throw "WireGuard 安装失败：$wg 不存在"
}
Write-Host "WireGuard 已安装：$wg"

if ($ConfigPath -and (Test-Path $ConfigPath)) {
    Write-Host "导入隧道：$ConfigPath"
    & $wg /installtunnelservice $ConfigPath
    Start-Sleep -Seconds 3
    Write-Host "检查内网..."
    curl.exe -s -m 8 http://10.10.0.1:8001/version
} else {
    Write-Host "未提供隧道配置。可手动用 WireGuard 导入 admin_wg1.conf / pilot.conf。"
}
