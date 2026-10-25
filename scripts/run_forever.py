import subprocess, sys, time
while True:
    print('[wrapper] start on :8001', flush=True)
    subprocess.run([sys.executable, '-m', 'uvicorn', 'app_full:app', '--host', '0.0.0.0', '--port', '8001'])
    time.sleep(3)
