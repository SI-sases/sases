param(
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$InstallDir = "D:\sases",
    [string]$ZipPath = "D:\sases-portable.zip",
    [switch]$SkipAutostart,
    [switch]$SkipStart
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")
$portableUrl = "$base/static/downloads/sases-portable.zip"
$hashUrl = "$base/static/downloads/sases-portable.zip.sha256"

Write-Host "[bootstrap] downloading portable package..."
$downloaded = $false
try {
    $head = curl.exe -sI $portableUrl
    $lengthLine = ($head | Select-String -Pattern "^content-length:" -CaseSensitive:$false | Select-Object -First 1).Line
    $total = [int64](($lengthLine -split ":")[1].Trim())
    if ($total -gt 0) {
        $parts = 4
        $chunk = [math]::Ceiling($total / $parts)
        $jobs = @()
        Remove-Item "$ZipPath.part*" -Force -ErrorAction SilentlyContinue
        for ($i = 0; $i -lt $parts; $i++) {
            $start = $i * $chunk
            $end = [math]::Min($total - 1, ($i + 1) * $chunk - 1)
            $part = "$ZipPath.part$i"
            $jobs += Start-Job -ScriptBlock {
                param($url, $start, $end, $out)
                curl.exe -s --fail -r "$start-$end" -o $out $url
            } -ArgumentList $portableUrl, $start, $end, $part
        }
        $jobs | Wait-Job | Out-Null
        $jobs | Receive-Job | Out-Null
        $jobs | Remove-Job -Force
        $partFiles = @()
        for ($i = 0; $i -lt $parts; $i++) { $partFiles += "$ZipPath.part$i" }
        if (($partFiles | Where-Object { -not (Test-Path $_) }).Count -eq 0) {
            Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
            cmd.exe /c ("copy /b " + ($partFiles -join "+") + " `"$ZipPath`"") | Out-Null
            Remove-Item "$ZipPath.part*" -Force -ErrorAction SilentlyContinue
            $downloaded = ((Get-Item $ZipPath).Length -eq $total)
        }
    }
} catch {
    Write-Host "[bootstrap] parallel download failed, falling back to curl"
}
if (-not $downloaded) {
    curl.exe -L --fail --retry 5 --retry-delay 2 -C - -o $ZipPath $portableUrl
}
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
