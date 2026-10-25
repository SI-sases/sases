import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "launcher", "ui", "main_window.py")

with open(path, "r", encoding="utf-8") as f:
    code = f.read()

pattern = re.compile(r"    def _check_update\(self\):.*?(?=\n    def )", re.DOTALL)

new_method = '''    def _check_update(self):
        self._log("[启动器] 正在检查启动器更新...")
        import urllib.request
        import urllib.error
        import ssl
        import json
        import os
        import subprocess

        urls = [
            "http://47.96.87.147:8001/static/downloads/version.json",
            "https://8.210.238.165:8443/downloads/version.json"
        ]

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

        latest_ver = None
        download_url = None

        for u in urls:
            try:
                self._log(f"[启动器] 尝试连接: {u}")
                req = urllib.request.Request(u)
                with opener.open(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    latest_ver = data.get("launcher_version")
                    download_url = data.get("download_url")
                    if latest_ver:
                        self._log(f"[启动器] 成功获取最新版本: {latest_ver}")
                        break
            except Exception as e:
                self._log(f"[启动器] 连接失败: {e}")
                continue

        if not latest_ver:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "检查失败", "无法连接到任何更新服务器，请检查网络。")
            return

        if latest_ver == CURRENT_LAUNCHER_VERSION:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "已是最新", f"当前启动器已是最新版 ({CURRENT_LAUNCHER_VERSION})。")
            return

        from PyQt6.QtWidgets import QMessageBox, QApplication
        reply = QMessageBox.question(self, "发现新版本",
                                     f"发现新版启动器 {latest_ver}，是否立即更新？\\n（更新后程序会自动重启）",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self._log(f"[启动器] 开始下载更新包: {download_url}")
            try:
                if hasattr(self, 'proc') and self.proc:
                    self.stop()

                new_exe = "SASES启动器_new.exe"
                urllib.request.urlretrieve(download_url, new_exe)

                self._log("[启动器] 下载完成，正在准备替换...")
                bat_content = f"""@echo off
cd /d "%~dp0"
timeout /t 2 /nobreak >nul
taskkill /f /im "SASES启动器.exe" >nul 2>&1
if exist "SASES启动器.exe" del "SASES启动器.exe"
rename "SASES启动器_new.exe" "SASES启动器.exe"
start "" "SASES启动器.exe"
del "%~f0"
"""
                with open("update.bat", "w", encoding="gbk") as f:
                    f.write(bat_content)

                subprocess.Popen("update.bat", shell=True)
                QApplication.quit()
                os._exit(0)
            except Exception as e:
                QMessageBox.critical(self, "更新失败", f"下载出错: {e}")
'''

if pattern.search(code):
    code = pattern.sub(new_method, code)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: _check_update method replaced successfully!")
else:
    print("ERROR: Could not find _check_update method to replace.")
