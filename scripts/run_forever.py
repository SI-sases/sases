import subprocess
import sys
import os
import time

while True:
    try:
        for f in ["restart_signal.txt"]:
            if os.path.exists(f):
                os.remove(f)
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["LANG"] = "en_US.UTF-8"
        for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            env.pop(k, None)

        print("[wrapper] start on :8001", flush=True)
        ret = subprocess.run([sys.executable, "-X", "utf8", "-m", "uvicorn", "app_full:app", "--host", "0.0.0.0", "--port", "8001"], env=env)
        time.sleep(2)
    except KeyboardInterrupt:
        break
