import os, sys, subprocess, webbrowser, time

base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(base_dir)

# 1. 自动修复 venv 路径，使之便携化
cfg_path = os.path.join(base_dir, "venv312", "pyvenv.cfg")
if os.path.exists(cfg_path):
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(f"home = {os.path.join(base_dir, 'python312')}\n")
        f.write("include-system-site-packages = false\n")
        f.write("version = 3.12.0\n")

# 2. 延迟打开浏览器
webbrowser.open("http://127.0.0.1:8001/static/index.html")

# 3. 启动后端
python_exe = os.path.join(base_dir, "venv312", "Scripts", "python.exe")
subprocess.run([python_exe, "scripts/run_forever.py"])
