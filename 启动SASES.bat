@echo off
cd /d %~dp0
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v SASES >nul 2>&1
if errorlevel 1 reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v SASES /t REG_SZ /d "\"%~dp0SASES-start.bat\"" /f >nul 2>&1

cd /d %~dp0
if exist "python-embed\pythonw.exe" (
  start "" /min "python-embed\pythonw.exe" "scripts\run_forever.py"
) else (
  start "" /min "python-embed\python.exe" "scripts\run_forever.py"
)
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:8001"
