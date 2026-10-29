import os
import sys
import subprocess
import threading
import webbrowser
import time

def main():
    # 1. 强行锁定当前启动器所在的目录
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(base_dir)
    
    # 2. 强行把当前目录塞进环境变量，防止找不到 core 模块
    env = os.environ.copy()
    env["PYTHONPATH"] = base_dir
    env["PYTHONUTF8"] = "1"
    
    # 3. 启动浏览器
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:8001/static/index.html")
    threading.Thread(target=open_browser, daemon=True).start()

    # 4. 调起底层 python-embed 跑 uvicorn
    # 注意：如果第一版用的是 python-embed，这里就指向 python-embed
    python_exe = os.path.join(base_dir, "python-embed", "python.exe")
    script_path = os.path.join(base_dir, "scripts", "run_forever.py")
    
    print(f"[启动器] 正在拉起服务: {python_exe} {script_path}")
    
    # 使用 subprocess 启动后端
    subprocess.run([python_exe, script_path], env=env)

if __name__ == "__main__":
    main()
