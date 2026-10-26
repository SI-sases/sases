import subprocess
import sys
import os
import time

while True:
    try:
        for f in ["restart_signal.txt"]:
            if os.path.exists(f):
                os.remove(f)
        
        print("[wrapper] start on :8001", flush=True)
        subprocess.run([sys.executable, "-m", "uvicorn", "app_full:app", "--host", "0.0.0.0", "--port", "8001"])
        time.sleep(2)
    except KeyboardInterrupt:
        break
