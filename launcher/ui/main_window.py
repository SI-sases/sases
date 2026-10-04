"""SASES 启动器主窗口。"""
import os, sys
import urllib.request
import launcher.launcher_config


def _decode_child_line(raw):
    for enc in ('utf-8', 'gbk', 'cp936', 'latin-1'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', 'replace')
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QMainWindow, QWidget, QPushButton, QPlainTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox

# 项目根目录（launcher/ui/main_window.py -> 上溯三层）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MainWindow(QMainWindow):
    def __init__(self):
        self.cfg = ensure_default_config()
        self.port = self.cfg.get("port", 8001)
        self.python_path = self.cfg.get("python_path", "")
        self.script_path = self.cfg.get("script_path", "")
        self.work_dir = self.cfg.get("work_dir", "")
        self.port = self.cfg.get("port", 8001)
        self.python_path = self.cfg.get("python_path", "")
        self.script_path = self.cfg.get("script_path", "")
        self.work_dir = self.cfg.get("work_dir", "")
        super().__init__()
        self.proc = None
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

    def out(self, t):
        self.log.appendPlainText(t.rstrip())

    def start(self):
        import urllib.request
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/hive/info", timeout=2)
            self.statusBar().showMessage("已运行（外部进程）")
            return
        except Exception:
            pass
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{self.port}/hive/info', timeout=2)
            self.statusBar().showMessage('已运行（外部进程）')
            self.log('检测到外部进程，跳过启动')
            return
        except Exception:
            pass
        import urllib.request
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/hive/info', timeout=2)
            self.log.appendPlainText('检查到外部服务已运行')
            return
        except Exception:
            pass
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{launcher.launcher_config.PORT}/hive/info', timeout=2).close()
            _log = getattr(self, 'log', None) or getattr(self, 'log_view', None) or getattr(self, 'output', None)
            if _log is None:
                from PyQt6.QtWidgets import QPlainTextEdit as _QPT
                _logs = self.findChildren(_QPT)
                _log = _logs[0] if _logs else None
            if _log is not None:
                if hasattr(_log, 'appendPlainText'):
                    _log.appendPlainText('检查到外部服务已运行')
                elif hasattr(_log, 'append'):
                    _log.append('检查到外部服务已运行')
            _status = getattr(self, 'status', None) or getattr(self, 'status_label', None) or getattr(self, 'label_status', None)
            if _status is None:
                from PyQt6.QtWidgets import QLabel as _QL
                _labels = self.findChildren(_QL)
                _status = _labels[0] if _labels else None
            if _status is not None and hasattr(_status, 'setText'):
                _status.setText('已运行（外部进程）')
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        if self.proc:
            return
        p = QProcess(self)
        p.setWorkingDirectory(ROOT)
        p.readyReadStandardOutput.connect(self.read)
        p.readyReadStandardError.connect(self.read)
        p.finished.connect(self.done)
        p.start(sys.executable, ['scripts/run_forever.py'])
        self.proc = p
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage('运行中')
        self.out('[启动器] 已启动 SASES 服务')

    def read(self):
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

    def closeEvent(self, e):
        if self.proc:
            r = QMessageBox.question(self, '确认', '服务还在运行，确定退出？')
            if r != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
            self.stop()
        e.accept()
