@echo off
cd /d %~dp0
if exist "python-embed\pythonw.exe" (
  start "" "python-embed\pythonw.exe" "launcher\launcher.py"
) else if exist "python-embed\python.exe" (
  start "" "python-embed\python.exe" "launcher\launcher.py"
) else (
  start "" python "launcher\launcher.py"
)
