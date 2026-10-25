"""SASES 启动器主窗口（终极防冲突版）。"""
import os, sys, time
import urllib.request
import urllib.error
import webbrowser
import socket
import subprocess
import launcher_config

CURRENT_LAUNCHER_VERSION = "1.0.0"

import urllib.request
import urllib.error
import ssl
import json
import sys
from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, Qt
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QSystemTrayIcon, QMenu, QStyle, QListWidget, QStackedWidget,
    QFrame, QLineEdit
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HIDDEN_NODE_PORTS = [8101, 8102]

def _decode_child_line(raw):
    for enc in ('utf-8', 'gbk', 'cp936', 'latin-1'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', 'replace')

class MainWindow(QMainWindow):
    def __init__(self):
        self.cfg = launcher_config.ensure_default_config()
        self.port = int(self.cfg.get("port", 8001))
        self.python_path = self.cfg.get("python_path", "")
        self.script_path = self.cfg.get("script_path", "")
        self.work_dir = launcher_config.resolve_path(self.cfg.get("work_dir", ""))
        self.script_path = launcher_config.resolve_path(self.cfg.get("script_path", ""))
        self.python_path = launcher_config.resolve_path(self.cfg.get("python_path", ""))
        super().__init__()
        self.proc = None
        self._chosen_port = self.port
        self._allow_close = False
        self._browser_opened = False
        
        self.setWindowTitle('SASES 启动器')
        self.resize(950, 650)
        
        self._init_ui()
        self._setup_tray()
        
        QTimer.singleShot(500, self._check_existing)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== 左侧导航 ==========
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #aaaaaa;
                border: none;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                height: 50px;
                padding-left: 20px;
                border-bottom: 1px solid #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #3c3f41;
                color: #ffffff;
                border-left: 4px solid #4a90e2;
            }
            QListWidget::item:hover:!selected {
                background-color: #333333;
            }
        """)
        self.sidebar.addItems(["📜 运行日志", "⚙️ 服务配置", "🛠 诊断工具", "🔄 检查更新"])
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        
        # ========== 右侧主区域 ==========
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #1e1e1e;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 顶部状态栏
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        
        self.status_label = QLabel('未运行')
        self.status_label.setStyleSheet("color: #ff5c5c; font-weight: bold; font-size: 14px;")
        
        self.version_label = QLabel('版本：未加载')
        self.version_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        self.btn_version = QPushButton('刷新版本')
        self.btn_version.clicked.connect(self._load_version_info)
        self.btn_version.setStyleSheet("background: transparent; color: #4a90e2; border: none; text-decoration: underline; cursor: pointer;")
        
        top_layout.addWidget(self.status_label)
        top_layout.addStretch(1)
        top_layout.addWidget(self.version_label)
        top_layout.addWidget(self.btn_version)
        
        # ========== 页面堆叠区 ==========
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #1e1e1e;")

        # 页面 0：运行日志
        page_log = QWidget()
        log_layout = QVBoxLayout(page_log)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(50000)
        self.log.setStyleSheet("background-color: #1e1e1e; color: #00ff00; border: none; font-family: Consolas, monospace; padding: 10px;")
        log_layout.addWidget(self.log)

        # 页面 1：服务配置
        page_config = QWidget()
        config_layout = QVBoxLayout(page_config)
        config_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        cfg_title = QLabel("模型服务配置")
        cfg_title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        
        self.cfg_key_input = QLineEdit()
        self.cfg_key_input.setPlaceholderText("API Key (本地模型可留空)")
        self.cfg_key_input.setFixedWidth(350)
        self.cfg_key_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")
        
        self.cfg_url_input = QLineEdit()
        self.cfg_url_input.setPlaceholderText("接口地址 (如 http://127.0.0.1:11434/v1)")
        self.cfg_url_input.setFixedWidth(350)
        self.cfg_url_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")
        
        self.cfg_model_input = QLineEdit()
        self.cfg_model_input.setPlaceholderText("模型名称 (如 deepseek-v4-flash 或 qwen:7b)")
        self.cfg_model_input.setFixedWidth(350)
        self.cfg_model_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")
        
        env_p = os.path.join(ROOT, ".env")
        if os.path.exists(env_p):
            with open(env_p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        self.cfg_key_input.setText(line.strip().split("=")[1])
                    elif line.startswith("DEEPSEEK_BASE_URL="):
                        self.cfg_url_input.setText(line.strip().split("=")[1])
                    elif line.startswith("MODEL_NAME="):
                        self.cfg_model_input.setText(line.strip().split("=")[1])

        btn_save_cfg = QPushButton("保存配置")
        btn_save_cfg.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_save_cfg.clicked.connect(self._save_config)
        
        config_layout.addWidget(cfg_title)
        config_layout.addWidget(self.cfg_key_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(self.cfg_url_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(self.cfg_model_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(btn_save_cfg, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout = QVBoxLayout(page_config)
        config_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cfg_title = QLabel("服务配置")
        cfg_title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")

        self.cfg_key_input = QLineEdit()
        self.cfg_key_input.setPlaceholderText("输入 DeepSeek API Key...")
        self.cfg_key_input.setFixedWidth(300)
        self.cfg_key_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")

        env_p = os.path.join(ROOT, ".env")
        if os.path.exists(env_p):
            with open(env_p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        self.cfg_key_input.setText(line.strip().split("=")[1])

        btn_save_cfg = QPushButton("保存配置")
        btn_save_cfg.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_save_cfg.clicked.connect(self._save_config)

        config_layout.addWidget(cfg_title)
        config_layout.addWidget(self.cfg_key_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(btn_save_cfg, alignment=Qt.AlignmentFlag.AlignCenter)

        # 页面 2：诊断工具
        page_diag = QWidget()
        diag_layout = QVBoxLayout(page_diag)
        diag_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        diag_title = QLabel("系统诊断")
        diag_title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        diag_desc = QLabel("如果你的启动器连不上服务，或者遇到未知错误，\n请点击下方按钮生成诊断报告，并发送给开发者。")
        diag_desc.setStyleSheet("color: #aaa; font-size: 14px; text-align: center; margin-bottom: 20px;")
        diag_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_do_diag = QPushButton("生成诊断报告")
        btn_do_diag.setFixedSize(160, 40)
        btn_do_diag.setStyleSheet("background-color: #4a90e2; color: white; border-radius: 4px; font-weight: bold;")
        btn_do_diag.clicked.connect(self._export_diag)
        
        diag_layout.addWidget(diag_title)
        diag_layout.addWidget(diag_desc)
        diag_layout.addWidget(btn_do_diag, alignment=Qt.AlignmentFlag.AlignCenter)

        # 页面 2：检查更新
        page_update = QWidget()
        update_layout = QVBoxLayout(page_update)
        update_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        upd_title = QLabel("版本更新")
        upd_title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        upd_desc = QLabel("点击下方按钮检查是否有最新的代码更新。")
        upd_desc.setStyleSheet("color: #aaa; font-size: 14px; text-align: center; margin-bottom: 20px;")
        upd_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_do_update = QPushButton("检查更新")
        btn_do_update.setFixedSize(160, 40)
        btn_do_update.setStyleSheet("background-color: #4a90e2; color: white; border-radius: 4px; font-weight: bold;")
        btn_do_update.clicked.connect(self._check_update)
        
        update_layout.addWidget(upd_title)
        update_layout.addWidget(upd_desc)
        update_layout.addWidget(btn_do_update, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stacked_widget.addWidget(page_log)
        self.stacked_widget.addWidget(page_config)
        self.stacked_widget.addWidget(page_diag)
        self.stacked_widget.addWidget(page_update)
        
        # ========== 底部操作区（右下角悬浮控制） ==========
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color: #1e1e1e;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 10, 30, 30)
        bottom_layout.addStretch(1)
        
        self.btn_toggle = QPushButton("▶")
        self.btn_toggle.setFixedSize(60, 60)
        self.btn_toggle.clicked.connect(self._toggle_service)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_running_ui(False)
        
        bottom_layout.addWidget(self.btn_toggle)
        
        right_layout.addWidget(top_bar)
        right_layout.addWidget(self.stacked_widget)
        right_layout.addWidget(bottom_bar)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(right_panel)
        
        self.sidebar.setCurrentRow(0)

    def _save_config(self):
        key = self.cfg_key_input.text().strip()
        url = self.cfg_url_input.text().strip()
        model = self.cfg_model_input.text().strip()
        env_p = os.path.join(ROOT, ".env")
        with open(env_p, "w", encoding="utf-8") as f:
            if key: f.write(f"DEEPSEEK_API_KEY={key}\n")
            if url: f.write(f"DEEPSEEK_BASE_URL={url}\n")
            if model: f.write(f"MODEL_NAME={model}\n")
        QMessageBox.information(self, "成功", "配置已保存，重启服务生效。")

    def _on_sidebar_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def _set_running_ui(self, is_running):
        if is_running:
            self.status_label.setText(f"运行中 :{self._chosen_port}")
            self.status_label.setStyleSheet("color: #34c759; font-weight: bold; font-size: 14px;")
            self.btn_toggle.setText("⏹")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #ff5c5c;
                    color: white;
                    border-radius: 30px;
                    font-size: 24px;
                }
                QPushButton:hover { background-color: #d94b4b; }
            """)
        else:
            self.status_label.setText("未运行")
            self.status_label.setStyleSheet("color: #ff5c5c; font-weight: bold; font-size: 14px;")
            self.btn_toggle.setText("▶")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #4a90e2;
                    color: white;
                    border-radius: 30px;
                    font-size: 24px;
                    padding-left: 5px;
                }
                QPushButton:hover { background-color: #357abd; }
            """)

    def _toggle_service(self):
        if self.proc is None:
            self.start()
        else:
            self.stop()

    def _kill_port_process(self, port):
        """强制杀掉占用指定端口的进程"""
        try:
            out = subprocess.check_output(["netstat", "-ano"], text=True, encoding='gbk', errors='ignore')
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        self._log(f"[启动器] 发现残留进程 PID={pid} 占用端口 {port}，正在清理...")
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
            time.sleep(1) # 给系统一点时间释放端口
        except Exception as e:
            self._log(f"[启动器] 清理端口异常: {e}")

    # ====== 版本与功能逻辑 ======
    def _load_version_info(self):
        import json
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        url = f"http://127.0.0.1:{self._chosen_port}/version"
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=3) as r:
                data = json.loads(r.read().decode())
            txt = f"v{data.get('commit','?')} ({data.get('branch','?')}) | Schema:{data.get('schema','?')} | 节点:{data.get('node_id','?')}"
        except Exception:
            txt = "版本不可用（服务未启动？）"
        self.version_label.setText(txt)

    def _export_diag(self):
        import datetime
        path = os.path.join(os.path.dirname(__file__), "diag.txt")
        lines = [f"=== SASES 诊断报告 {datetime.datetime.now()} ==="]
        try:
            out = subprocess.check_output(["netstat", "-ano"], text=True, timeout=10, encoding='gbk', errors='ignore')
            port_lines = [l for l in out.splitlines() if f":{self._chosen_port}" in l]
            lines.append(f"[端口 {self._chosen_port}]")
            lines.extend(port_lines or ["未监听"])
        except Exception as e:
            lines.append(f"[端口] 检测失败: {e}")
        
        lines.append(f"[版本] {self.version_label.text()}")
        
        log_path = os.path.join(os.getcwd(), "logs", "latest.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    tail = f.readlines()[-50:]
                lines.append("[日志尾部]")
                lines.extend(tail)
            except Exception as e:
                lines.append(f"[日志] 读取失败: {e}")
                
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        QMessageBox.information(self, "导出成功", f"诊断报告已生成：\n{path}")

    def _check_update(self):
        QMessageBox.information(self, "自动更新", "SASES 采用全自动热更新机制。\n\n您无需手动检查，每次点击右下角“▶”启动服务时，系统会自动与云端同步最新代码并拉取更新。")
        import ssl
        import json
        import os
        import subprocess
        from PyQt6.QtWidgets import QMessageBox, QApplication
        
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
            QMessageBox.warning(self, "检查失败", "无法连接到任何更新服务器，请检查网络。")
            return
            
        if latest_ver == CURRENT_LAUNCHER_VERSION:
            QMessageBox.information(self, "已是最新", f"当前启动器已是最新版 ({CURRENT_LAUNCHER_VERSION})。")
            return
            
        reply = QMessageBox.question(self, "发现新版本", 
                                     f"发现新版启动器 {latest_ver}，是否立即更新？\n（更新后程序会自动重启）",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._log(f"[启动器] 正在唤起后台下载器...")
            try:
                if hasattr(self, 'proc') and self.proc:
                    self.stop()
                
                import sys
                import os
                # 关键：获取当前 EXE 所在的绝对目录
                if getattr(sys, 'frozen', False):
                    exe_dir = os.path.dirname(sys.executable)
                else:
                    exe_dir = os.path.dirname(os.path.abspath(__file__))
                    
                bat_path = os.path.join(exe_dir, "update.bat")
                
                # 利用 Windows 自带的 curl 在 bat 中下载，彻底避免 Python 卡死
                bat_content = f"""@echo off
cd /d "%~dp0"
echo 正在后台下载最新版，请稍候...
curl -L -o "SASES启动器_new.exe" "{download_url}"
echo 下载完成，准备替换...
ping 127.0.0.1 -n 3 > nul
taskkill /f /im "SASES启动器.exe" >nul 2>&1
if exist "SASES启动器.exe" del "SASES启动器.exe"
rename "SASES启动器_new.exe" "SASES启动器.exe"
start "" "SASES启动器.exe"
del "%~f0"
"""
                with open(bat_path, "w", encoding="gbk") as f:
                    f.write(bat_content)
                
                import subprocess
                # 使用 cmd.exe /c 强制拉起批处理，并在独立的控制台窗口中运行
                subprocess.Popen(f'start cmd.exe /c "{bat_path}"', shell=True)
                
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(self, "更新失败", f"更新脚本出错: {e}")
            self._log(f"[启动器] 正在唤起后台下载器...")
            try:
                if hasattr(self, 'proc') and self.proc:
                    self.stop()
                
                bat_content = f"""@echo off
cd /d "%~dp0"
echo 正在后台下载最新版，请稍候...
curl -L -o "SASES启动器_new.exe" "{download_url}"
echo 下载完成，准备替换...
ping 127.0.0.1 -n 3 > nul
taskkill /f /im "SASES启动器.exe" >nul 2>&1
if exist "SASES启动器.exe" del "SASES启动器.exe"
rename "SASES启动器_new.exe" "SASES启动器.exe"
start "" "SASES启动器.exe"
del "%~f0"
"""
                with open("update.bat", "w", encoding="gbk") as f:
                    f.write(bat_content)
                
                import subprocess
                subprocess.Popen("start update.bat", shell=True)
                
                import sys
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(self, "更新失败", f"更新脚本出错: {e}")
            self._log(f"[启动器] 开始静默下载更新包: {download_url}")
            try:
                if hasattr(self, 'proc') and self.proc:
                    self.stop()

                new_exe = "SASES启动器_new.exe"
                import urllib.request
                urllib.request.urlretrieve(download_url, new_exe)

                self._log("[启动器] 下载完成，正在准备强制替换...")
                # 使用 ping 延迟等待，彻底脱离父进程
                bat_content = "@echo off\ncd /d \"%~dp0\"\nping 127.0.0.1 -n 3 > nul\ntaskkill /f /im \"SASES启动器.exe\" >nul 2>&1\nif exist \"SASES启动器.exe\" del \"SASES启动器.exe\"\nrename \"SASES启动器_new.exe\" \"SASES启动器.exe\"\nstart \"\" \"SASES启动器.exe\"\ndel \"%~f0\"\n"
                with open("update.bat", "w", encoding="gbk") as f:
                    f.write(bat_content)

                import subprocess
                # 使用 DETACHED_PROCESS 标志，让 bat 完全独立运行，不受父进程退出影响
                subprocess.Popen("update.bat", shell=True, creationflags=0x00000008)
                QApplication.quit()
                os._exit(0)
            except Exception as e:
                QMessageBox.critical(self, "更新失败", f"下载出错: {e}")

    # ====== 进程控制 ======
    def _check_existing(self):
        # 启动器刚打开时，如果发现服务已经在跑，只接管状态，不自动弹网页
        try:
            proxy = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy)
            with opener.open(f"http://127.0.0.1:{self._chosen_port}/version", timeout=2):
                self._log("[启动器] 检测到服务已在后台运行")
                self._set_running_ui(True)
                self._load_version_info()
        except Exception:
            pass

    def start(self):
        if self.proc is not None:
            return
            
        # ====== 更新检测逻辑：优先 Git，降级中转 ======
        git_success = False
        try:
            git_dir = os.path.join(self.work_dir, ".git")
            if os.path.exists(git_dir):
                self._log("[启动器] 优先尝试 Git 增量更新...")
                res = subprocess.run("git pull origin main", cwd=self.work_dir, shell=True, capture_output=True, timeout=5)
                if res.returncode == 0:
                    self._log("[启动器] Git 更新成功，当前已是最新版本。")
                    git_success = True
                else:
                    self._log("[启动器] Git 更新失败，准备降级。")
            else:
                self._log("[启动器] 本地无 Git 环境，准备降级。")
        except Exception as e:
            self._log(f"[启动器] Git 更新超时（无 VPN 网络），触发降级。")

        if not git_success:
            self._log("[启动器] 正在通过国内中转服务器拉取更新...")
            try:
                import urllib.request
                import zipfile
                import io
                import ssl

                # 简易双线优选：默认用国内，如果异常再切香港
                update_url = "http://47.96.87.147:8001/static/downloads/code_update.zip"
                try:
                    import urllib.request
                    urllib.request.urlopen(update_url, timeout=2)
                except Exception:
                    update_url = "https://8.210.238.165:8443/downloads/code_update.zip"
                req = urllib.request.Request(update_url)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                    zip_data = response.read()

                self._log("[启动器] 下载更新包成功，正在解压...")
                with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                    z.extractall(self.work_dir)
                self._log("[启动器] 中转同步完成，代码已更新！")
            except Exception as e:
                self._log(f"[启动器] 中转更新跳过（可能是首次运行或网络异常）")
        # ==================================================

        # 启动前尝试静默拉取最新代码（防报错：如果没装 git 或非 git 仓库则跳过）
        self._log("[启动器] 正在检查代码更新...")
        try:
            git_dir = os.path.join(self.work_dir, ".git")
            if os.path.exists(git_dir):
                subprocess.run("git pull origin main", cwd=self.work_dir, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                self._log("[启动器] 代码同步完成")
            else:
                self._log("[启动器] 当前为非 git 环境，跳过自动更新")
        except Exception:
            self._log("[启动器] 更新检查超时或被跳过")

        # 最关键的一步：启动前强制清理残留进程
        self._kill_port_process(self._chosen_port)

        self._set_running_ui(True)
        self.sidebar.setCurrentRow(0)
        self._log(f"[启动器] 正在启动 SASES 服务 :{self._chosen_port}")
        self._browser_opened = False

        env = QProcessEnvironment.systemEnvironment()
        env.insert("SASES_PORT", str(self._chosen_port))
        
        self.proc = QProcess(self)
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_out)
        self.proc.finished.connect(self._on_finished)
        self.proc.setWorkingDirectory(self.work_dir)
        
        self.proc.start(self.python_path, [self.script_path])
        QTimer.singleShot(5000, self._load_version_info)

    def stop(self):
        self._log("[启动器] 正在停止 SASES 服务...")
        if self.proc:
            pid = self.proc.processId()
            if pid:
                try:
                    subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                except Exception:
                    pass
            self.proc.terminate()
            if not self.proc.waitForFinished(1000):
                self.proc.kill()
        self._on_finished()

    def _on_finished(self):
        self.proc = None
        self._set_running_ui(False)
        self._log("[启动器] 服务已停止")

    def _read_out(self):
        if not self.proc:
            return
        raw = self.proc.readAllStandardOutput().data()
        text = _decode_child_line(raw)
        for line in text.splitlines():
            self._log(line)
            if "Application startup complete" in line or "服务已就绪" in line:
                self._set_running_ui(True)
                self._load_version_info()
                self._open_browser()

    def _open_browser(self):
        if not self._browser_opened:
            self._browser_opened = True
            url = f"http://127.0.0.1:{self._chosen_port}/static/index.html"
            self._log(f"[启动器] 打开浏览器 {url}")
            webbrowser.open(url)

    def _log(self, text):
        self.log.appendPlainText(text)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ====== 托盘 ======
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _ico = os.path.join(base_dir, 'launcher', 'icon.ico')
        if not os.path.exists(_ico):
            _ico = os.path.join(base_dir, 'icon.ico')
        if os.path.exists(_ico):
            self.tray.setIcon(QIcon(_ico))
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        self.tray.setToolTip('SASES 启动器')
        
        menu = QMenu()
        
        act_show = QAction('显示主界面', self)
        act_show.triggered.connect(self._show_window)
        act_start = QAction('启动服务', self)
        act_start.triggered.connect(self.start)
        act_stop = QAction('停止服务', self)
        act_stop.triggered.connect(self.stop)
        act_quit = QAction('退出', self)
        act_quit.triggered.connect(self._real_quit)
        
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_start)
        menu.addAction(act_stop)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event):
        if not self._allow_close:
            event.ignore()
            self.hide()
        else:
            event.accept()

    def _real_quit(self):
        self._allow_close = True
        self.stop()
        self.close()
        QTimer.singleShot(200, lambda: os._exit(0))
