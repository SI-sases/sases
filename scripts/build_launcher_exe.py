import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

print("正在打包启动器为 EXE，请稍候...")
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--onefile",
    "--icon", os.path.join("launcher", "icon.ico"),
    "--name", "SASES启动器",
    "--distpath", os.path.join("launcher", "dist"),
    "--workpath", os.path.join("launcher", "build"),
    "--specpath", "launcher",
    "--add-data", "launcher/ui" + os.pathsep + "ui",
    "--add-data", "launcher/launcher_config.py" + os.pathsep + ".",
    "launcher/launcher.py"
]

subprocess.run(cmd, check=True)
print("打包成功！EXE 位于 launcher/dist/SASES启动器.exe")
