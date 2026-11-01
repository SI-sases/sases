@echo off
cd /d %~dp0
call venv312\Scripts\activate.bat
echo ========================================
echo  SASES 服务启动器
echo ========================================

:loop
echo.
echo [start.bat] 启动服务...
python scripts/run_forever.py
set EC=%errorlevel%
echo [start.bat] 服务退出，退出码: %EC%

if %EC%==0 (
    echo [start.bat] 正常退出，2 秒后重启...
    timeout /t 2 /nobreak >nul
    goto loop
) else (
    echo [start.bat] 异常退出，按任意键关闭。
    pause
)