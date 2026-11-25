@echo off
cd /d %~dp0
echo Starting SASES in console mode...
echo Close this window to stop SASES.
python-embed\python.exe scripts\run_forever.py
pause
