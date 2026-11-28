param(
  [int]$TempDays = 7,
  [string]$Root = "C:\Users\xiaomai\sases"
)

$ErrorActionPreference = "SilentlyContinue"
$removed = 0

# Remove stale files from the user temp directory. In-use files are skipped.
$temp = [System.IO.Path]::GetTempPath()
$cutoff = (Get-Date).AddDays(-$TempDays)
Get-ChildItem $temp -Recurse -File -Force |
  Where-Object { $_.LastWriteTime -lt $cutoff } |
  ForEach-Object {
    try { Remove-Item $_.FullName -Force; $removed++ } catch {}
  }

# Remove SASES browser snapshots older than the configured TTL.
$snap = Join-Path $Root "data\browser_snapshots"
if (Test-Path $snap) {
  Get-ChildItem $snap -File -Force |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$TempDays) } |
    ForEach-Object {
      try { Remove-Item $_.FullName -Force; $removed++ } catch {}
    }
}

$drive = Get-PSDrive C
[pscustomobject]@{
  RemovedFiles = $removed
  FreeGB = [math]::Round($drive.Free / 1GB, 2)
  TempDays = $TempDays
}
