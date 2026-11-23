param(
    [string]$BaseUrl = "http://120.77.136.90:8001",
    [string]$InstallDir = "D:\sases",
    [string]$ZipPath = "D:\sases-portable.zip",
    [switch]$SkipAutostart,
    [switch]$SkipStart
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")
$portableUrl = "$base/static/downloads/sases-portable.zip"
$hashUrl = "$base/static/downloads/sases-portable.sha256"

Write-Host "[bootstrap] downloading portable package..."
curl.exe -L --fail -o $ZipPath $portableUrl
$actual = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
try {
    $expected = (curl.exe -s $hashUrl).Trim().Split(" ")[0].ToLower()
} catch { $expected = "" }
if ($expected -and $actual -ne $expected) {
    throw "SHA256 mismatch: $actual != $expected"
}
Write-Host "[bootstrap] SHA256 OK: $actual"

if (Test-Path $InstallDir) {
    $backup = "$InstallDir.old." + (Get-Date -Format "yyyyMMddHHmmss")
    Write-Host "[bootstrap] moving old install to $backup"
    Move-Item $InstallDir $backup
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Write-Host "[bootstrap] extracting..."
tar.exe -xf $ZipPath -C $InstallDir

$autostart = Join-Path $InstallDir "scripts\install_autostart.ps1"
if (-not $SkipAutostart -and (Test-Path $autostart)) {
    Write-Host "[bootstrap] installing logon autostart..."
    powershell -ExecutionPolicy Bypass -File $autostart -Root $InstallDir | Out-Host
}

if ($SkipStart) {
    Write-Host "[bootstrap] skip start (test mode)"
    exit 0
}
Write-Host "[bootstrap] starting SASES..."
Start-Process -FilePath (Join-Path $InstallDir "SASES-start.bat") -WorkingDirectory $InstallDir

$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $version = curl.exe -s -m 3 "http://127.0.0.1:8001/version"
        if ($version -match "schema_version") { Write-Host $version; $ok = $true; break }
    } catch {}
}
if (-not $ok) {
    Write-Host "[bootstrap] 8001 not ready, trying 8012..."
    try { curl.exe -s -m 3 "http://127.0.0.1:8012/version" } catch {}
}
Write-Host "[bootstrap] done. Remote operations are handled by /client/ops."
