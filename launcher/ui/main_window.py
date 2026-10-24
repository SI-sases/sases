"""SASES 启动器主窗口（终极防冲突版）。"""
import os, sys, time
import urllib.request
import urllib.error
import webbrowser
import socket
import subprocess
import launcher_config
from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, Qt
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QSystemTrayIcon, QMenu, QStyle, QListWidget, QStackedWidget,
    QFrame
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
        self.work_dir = self.cfg.get("work_dir", "")
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
        self.sidebar.addItems(["📜 运行日志", "🛠 诊断工具", "🔄 检查更新"])
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

        # 页面 1：诊断工具
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
        import json, urllib.request
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        url = f"http://127.0.0.1:{self._chosen_port}/version/check-update"
        try:
            req = urllib.request.Request(url, method="POST")
            with opener.open(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            if data.get("has_update"):
                QMessageBox.information(self, "检查更新", f"发现新版本！\n本地: {data.get('local')}\n远程: {data.get('remote')}\n\n请运行更新.bat")
            else:
                QMessageBox.information(self, "检查更新", "当前已是最新版本")
        except Exception as e:
            QMessageBox.warning(self, "检查失败", f"无法连接后端检查更新：\n{e}")

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
        _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icon.ico')
        if os.path.exists(_ico):
            self.tray.setIcon(QIcon(_ico))
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.setToolTip('SASES 启动器')
        menu = QMenu()
        act_show = QAction('显示窗口', self)
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
