import os
import sys
import subprocess
import threading
import webbrowser
import time

def main():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(base_dir)
    env = os.environ.copy()
    env["PYTHONPATH"] = base_dir
    env["PYTHONUTF8"] = "1"
    
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:8001/static/index.html")
    threading.Thread(target=open_browser, daemon=True).start()

    python_exe = os.path.join(base_dir, "python-embed", "python.exe")
    script_path = os.path.join(base_dir, "scripts", "run_forever.py")
    
    print(f"[启动器] 正在拉起服务: {python_exe} {script_path}")
    subprocess.run([python_exe, script_path], env=env)

if __name__ == "__main__":
    main()
