"""SASES 启动器主窗口（UI 优化满血版）。"""
import os, sys, time
import urllib.request
import urllib.error
import webbrowser
import socket
import subprocess
import ssl
import json
import io
import zipfile
import launcher_config

CURRENT_LAUNCHER_VERSION = "1.0.0"

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
        
        # ====== 设置窗口左上角图标 ======
        if getattr(sys, 'frozen', False):
            _base_dir = sys._MEIPASS
        else:
            _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _ico = os.path.join(_base_dir, 'launcher', 'icon.ico')
        if not os.path.exists(_ico):
            _ico = os.path.join(_base_dir, 'icon.ico')
        if os.path.exists(_ico):
            self.setWindowIcon(QIcon(_ico))
            
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
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(180)
        sidebar_container.setStyleSheet("background-color: #2b2b2b;")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.sidebar = QListWidget()
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
        sidebar_layout.addWidget(self.sidebar)
        
        # 左下角版本号
        ver_label = QLabel(f"v{CURRENT_LAUNCHER_VERSION}")
        ver_label.setStyleSheet("color: #666; padding: 15px; font-size: 12px;")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(ver_label)
        
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
        cfg_title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        
        self.cfg_key_input = QLineEdit()
        self.cfg_key_input.setPlaceholderText("API Key (本地模型可留空)")
        self.cfg_key_input.setFixedWidth(350)
        self.cfg_key_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")
        
        self.cfg_url_input = QLineEdit()
        self.cfg_url_input.setPlaceholderText("接口地址 (如 https://api.deepseek.com/v1)")
        self.cfg_url_input.setFixedWidth(350)
        self.cfg_url_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")
        
        self.cfg_model_input = QLineEdit()
        self.cfg_model_input.setPlaceholderText("模型名称 (如 deepseek-chat)")
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

        # 引导链接
        link_label = QLabel('<a href="https://platform.deepseek.com/api_keys" style="color: #4a90e2; text-decoration: none;">👉 点击这里去 DeepSeek 官网获取 API Key</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setStyleSheet("font-size: 13px; margin-bottom: 15px;")

        btn_save_cfg = QPushButton("保存配置")
        btn_save_cfg.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_save_cfg.clicked.connect(self._save_config)
        
        config_layout.addWidget(cfg_title)
        config_layout.addWidget(self.cfg_key_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(self.cfg_url_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(self.cfg_model_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(link_label, alignment=Qt.AlignmentFlag.AlignCenter)
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

        # 页面 3：检查更新
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
        
        # ========== 底部操作区 ==========
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
        
        main_layout.addWidget(sidebar_container)
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
        try:
            out = subprocess.check_output(["netstat", "-ano"], text=True, encoding='gbk', errors='ignore')
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        self._log(f"[启动器] 发现残留进程 PID={pid} 占用端口 {port}，正在清理...")
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
            time.sleep(1)
        except Exception as e:
            self._log(f"[启动器] 清理端口异常: {e}")

    def _load_version_info(self):
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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"diag_{ts}.zip"
        try:
            with zipfile.ZipFile(zip_name, 'w') as z:
                if os.path.exists("fatal_error.log"):
                    z.write("fatal_error.log")
                diag_txt = "diag_info.txt"
                with open(diag_txt, "w", encoding="utf-8") as f:
                    f.write(f"SASES Diag Report\nTime: {ts}\nCWD: {os.getcwd()}\nPython: {sys.executable}\n")
                z.write(diag_txt)
                os.remove(diag_txt)
            QMessageBox.information(self, "成功", f"诊断包已生成：{zip_name}\n请将此文件发给开发者。")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"生成诊断包失败: {e}")

    def _check_update(self):
        QMessageBox.information(self, "自动更新", "SASES 采用全自动热更新机制。\n\n您无需手动检查，每次点击右下角“▶”启动服务时，系统会自动与云端同步最新代码并拉取更新。")

    def _check_existing(self):
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

        # 恢复更新逻辑
        try:
            self._log("[启动器] 本地无 Git 环境，准备降级。")
            self._log("[启动器] 正在通过国内中转服务器拉取更新...")
            url = "http://47.96.87.147:8001/static/downloads/code_update.zip"
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(url)
            with opener.open(req, timeout=5) as resp:
                data = resp.read()
            self._log("[启动器] 下载更新包成功，正在解压...")
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                z.extractall(self.work_dir)
            self._log("[启动器] 中转同步完成，代码已更新！")
        except Exception:
            self._log("[启动器] 中转更新跳过（可能是首次运行或网络异常）")

        try:
            self._log("[启动器] 正在检查代码更新...")
            self._log("[启动器] 当前为非 git 环境，跳过自动更新")
        except Exception:
            pass

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
            # === 过滤吓人的警告 ===
            if "fatal: not a git repository" in line:
                continue
            if "PyTorch was not found" in line:
                continue
            if "[hive-register] no peers to register with" in line:
                continue
            # =======================
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

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
