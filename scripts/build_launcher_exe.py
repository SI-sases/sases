import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

print("正在打包启动器为 EXE，请稍候...")

# 使用绝对路径，彻底避免 PyInstaller 相对路径解析带来的二次拼接 bug
ui_src = os.path.join(ROOT, "launcher", "ui")
cfg_src = os.path.join(ROOT, "launcher", "launcher_config.py")
icon_path = os.path.join(ROOT, "launcher", "icon.ico")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--onefile",
    "--icon", icon_path,
    "--name", "SASES启动器",
    "--distpath", os.path.join(ROOT, "launcher", "dist"),
    "--workpath", os.path.join(ROOT, "launcher", "build"),
    "--hidden-import", "urllib.request",
    "--hidden-import", "urllib.error",
    "--hidden-import", "urllib.parse",
    "--hidden-import", "http.client",
    "--hidden-import", "ui.main_window",
    "--hidden-import", "launcher_config",
    # 一定要放在前面的源脚本
    os.path.join(ROOT, "launcher", "launcher.py"),
    # 绝对路径注入依赖
    "--add-data", f"{ui_src}{os.pathsep}ui",
    "--add-data", f"{cfg_src}{os.pathsep}."
]

subprocess.run(cmd, check=True)
print("✅ 打包成功！EXE 位于 launcher/dist/SASES启动器.exe")
