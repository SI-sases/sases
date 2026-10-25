import subprocess, sys, os, time

while True:
    try:
        if os.path.exists('restart_signal.txt'):
            os.remove('restart_signal.txt')
            print('[wrapper] cleaned restart_signal.txt')
        print('[wrapper] start on :8001')
        subprocess.run([sys.executable, '-m', 'uvicorn', 'app_full:app', '--host', '0.0.0.0', '--port', '8001'])
        time.sleep(2)
    except KeyboardInterrupt:
        break
