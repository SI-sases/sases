param(
    [string]$BaseUrl = "http://120.77.136.90:8001",
    [string]$InstallDir = "D:\sases",
    [string]$ZipPath = "D:\sases-portable.zip"
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")
$portableUrl = "$base/static/downloads/sases-portable.zip"
$hashUrl = "$base/static/downloads/sases-portable.sha256"

Write-Host "[bootstrap] 下载完整包..."
curl.exe -L --fail -o $ZipPath $portableUrl
$actual = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
try {
    $expected = (curl.exe -s $hashUrl).Trim().Split(" ")[0].ToLower()
} catch { $expected = "" }
if ($expected -and $actual -ne $expected) {
    throw "SHA256 校验失败: $actual != $expected"
}
Write-Host "[bootstrap] SHA256 OK: $actual"

if (Test-Path $InstallDir) {
    $backup = "$InstallDir.old." + (Get-Date -Format "yyyyMMddHHmmss")
    Write-Host "[bootstrap] 备份旧目录到 $backup"
    Move-Item $InstallDir $backup
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Write-Host "[bootstrap] 解压..."
tar.exe -xf $ZipPath -C $InstallDir

$autostart = Join-Path $InstallDir "scripts\install_autostart.ps1"
if (Test-Path $autostart) {
    Write-Host "[bootstrap] 安装登录自启动..."
    powershell -ExecutionPolicy Bypass -File $autostart -Root $InstallDir | Out-Host
}

Write-Host "[bootstrap] 启动 SASES..."
Start-Process -FilePath (Join-Path $InstallDir "启动SASES.bat") -WorkingDirectory $InstallDir

$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $version = curl.exe -s -m 3 "http://127.0.0.1:8001/version"
        if ($version -match "schema_version") { Write-Host $version; $ok = $true; break }
    } catch {}
}
if (-not $ok) {
    Write-Host "[bootstrap] 8001 未就绪，尝试 8012..."
    try { curl.exe -s -m 3 "http://127.0.0.1:8012/version" } catch {}
}
Write-Host "[bootstrap] 完成。后续由服务器 /client/ops 下发命令。"
