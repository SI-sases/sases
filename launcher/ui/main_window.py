# SASES Launcher Module
"""SASES 启动器主窗口。"""
import os, sys
import urllib.request
import urllib.error
import webbrowser
import socket
import launcher_config


def _decode_child_line(raw):
    for enc in ('utf-8', 'gbk', 'cp936', 'latin-1'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', 'replace')


from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox,
    QSystemTrayIcon, QMenu, QStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        self._allow_close = False          # 托盘退出时才置 True
        self.setWindowTitle('SASES 启动器')
        self.resize(900, 600)
        self.btn_start = QPushButton('启动')
        self.btn_stop = QPushButton('停止')
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        h = QHBoxLayout()
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        h.addStretch(1)
        v = QVBoxLayout()
        v.addLayout(h)
        v.addWidget(self.log)
        w = QWidget()
        w.setLayout(v)
        self.setCentralWidget(w)
        self.statusBar().showMessage('未运行')
        self.btn_stop.setEnabled(False)
        self._setup_tray()

    # ---------- 托盘 ----------
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
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
        self.tray.activated.connect(self._on_tray_clicked)
        self.tray.show()

    def _on_tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _real_quit(self):
        self._allow_close = True
        self.close()

    # ---------- 工具 ----------
    def out(self, t):
        self.log.appendPlainText(t.rstrip())

    def _check_running(self, port):
        try:
            urllib.request.urlopen(
                f'http://127.0.0.1:{port}/hive/info', timeout=2
            ).close()
            return True
        except Exception:
            return False

    def _port_busy(self, p):
        """用 connect 判占用（避开 Windows SO_REUSEADDR 陷阱）。"""
        for family, host in (
            (socket.AF_INET,  '127.0.0.1'),
            (socket.AF_INET6, '::1'),
        ):
            try:
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    if s.connect_ex((host, p)) == 0:
                        return True
            except Exception:
                continue
        return False

    def _find_free_port(self, start, span=20):
        for p in range(start, start + span):
            if not self._port_busy(p):
                return p
        return start

    def _open_browser(self, port):
        url = f'http://127.0.0.1:{port}/static/index.html'
        self.out(f'[启动器] 打开浏览器 {url}')
        try:
            webbrowser.open(url)
        except Exception as e:
            self.out(f'[启动器] 打开浏览器失败: {e}')

    # ---------- 生命周期 ----------
    def start(self):
        if self._check_running(self.port):
            self.statusBar().showMessage('已运行（外部进程）')
            self.out('检测到外部进程，跳过启动')
            self._open_browser(self.port)
            return

        chosen = self._find_free_port(self.port)
        if chosen != self.port:
            self.out(f'[启动器] 端口 {self.port} 被占用，改用 {chosen}')
        self._chosen_port = chosen

        if self.proc:
            return

        p = QProcess(self)
        p.setWorkingDirectory(ROOT)
        env = QProcessEnvironment.systemEnvironment()
        env.insert('SASES_PORT', str(chosen))
        p.setProcessEnvironment(env)
        p.readyReadStandardOutput.connect(self.read)
        p.readyReadStandardError.connect(self.read)
        p.finished.connect(self.done)
        p.start(sys.executable, ['scripts/run_forever.py'])

        self.proc = p
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage(f'运行中 :{chosen}')
        self.out(f'[启动器] 已启动 SASES 服务 :{chosen}')

        QTimer.singleShot(2000, lambda: self._poll_ready(chosen, 15))

    def _poll_ready(self, port, attempts):
        if self._check_running(port):
            self.out(f'[启动器] 服务已就绪 :{port}')
            self._open_browser(port)
            return
        if attempts <= 0:
            self.out(f'[启动器] 服务未在预期时间内就绪 :{port}')
            return
        QTimer.singleShot(2000, lambda: self._poll_ready(port, attempts - 1))

    def read(self):
        if not self.proc:
            return
        b = self.proc.readAllStandardOutput() + self.proc.readAllStandardError()
        for line in _decode_child_line(bytes(b)).splitlines():
            self.out(line)

    def done(self, code, st):
        self.out('[启动器] 进程结束 code=%s' % code)
        self.proc = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage('未运行')

    def stop(self):
        if not self.proc:
            return
        pid = int(self.proc.processId())
        QProcess.startDetached('taskkill', ['/F', '/T', '/PID', str(pid)])
        self.out('[启动器] 已停止 pid=%s' % pid)

    # ---------- 托盘行为 ----------
    def closeEvent(self, e):
        if self._allow_close:
            # 真正退出
            if self.proc:
                self.stop()
            e.accept()
            return
        # 关闭 = 最小化到托盘
        e.ignore()
        self.hide()
        try:
            self.tray.showMessage(
                'SASES 启动器', '已最小化到托盘，双击图标恢复',
                QSystemTrayIcon.MessageIcon.Information, 2000
            )
        except Exception:
            pass
