import subprocess, sys, os, time

while True:
    try:
        # 强制清理重启信号，保证每次拉起都是干净的
        if os.path.exists('restart_signal.txt'):
            os.remove('restart_signal.txt')
            print('[wrapper] cleaned restart_signal.txt')

        print("[wrapper] start on :8001")
        subprocess.run([sys.executable, '-m', 'uvicorn', 'app_full:app', '--host', '0.0.0.0', '--port', '8001'])

        # 如果退出，可能是有信号或者崩溃，等 1 秒再拉起
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n[wrapper] stopped by user")
        break
