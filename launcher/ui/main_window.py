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
    QSystemTrayIcon, QMenu, QStyle, QLabel,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 隐藏节点默认端口
HIDDEN_NODE_PORTS = [8101, 8102]


class MainWindow(QMainWindow):
    def __init__(self):
        self.cfg = launcher_config.ensure_default_config()
        self.port = int(self.cfg.get("port", 8001))
        self.python_path = self.cfg.get("python_path", "")
        self.script_path = self.cfg.get("script_path", "")
        self.work_dir = self.cfg.get("work_dir", "")
        super().__init__()
        self.proc = None
        self.hidden_procs = []          # 隐藏节点的 QProcess 列表
        self._chosen_port = self.port
        self._allow_close = False
        self.setWindowTitle('SASES 启动器')
        self.resize(900, 600)
        self.btn_start = QPushButton('启动')
        self.btn_stop = QPushButton('停止')
        self.version_label = QLabel('版本：未加载')
        self.btn_version = QPushButton('刷新版本')
        self.btn_version.clicked.connect(self._load_version_info)
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(50000)
        h = QHBoxLayout()
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        h.addWidget(self.version_label)
        h.addWidget(self.btn_version)
        self.btn_diag = QPushButton('导出诊断')
        self.btn_diag.clicked.connect(self._export_diag)
        h.addWidget(self.btn_diag)
        self.btn_update = QPushButton('检查更新')
        self.btn_update.clicked.connect(self._check_update)
        h.addWidget(self.btn_update)
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
    def _check_update(self):
        import json, urllib.request
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8001/version/check-update",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            has_update = bool(data.get("has_update"))
        except Exception:
            has_update = False
        if has_update:
            QMessageBox.information(self, "检查更新", "有新版本，请运行更新.bat")
        else:
            QMessageBox.information(self, "检查更新", "已是最新版本")


    def _export_diag(self):
        import datetime, sys, subprocess, urllib.request
        lines = []
        lines.append('时间: ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        lines.append('Python: ' + sys.version)
        try:
            out = subprocess.run('netstat -ano | findstr :8001', shell=True, capture_output=True, text=True, timeout=10)
            lines.append('端口8001:\n' + (out.stdout or '(无输出)'))
        except Exception as e:
            lines.append('端口检查失败: ' + str(e))
        try:
            url = 'http://127.0.0.1:%s/version' % self._chosen_port
            with urllib.request.urlopen(url, timeout=5) as r:
                lines.append('版本接口: ' + r.read().decode('utf-8', 'ignore'))
        except Exception as e:
            lines.append('版本接口失败: ' + str(e))
        try:
            with open('logs/latest.log', 'r', encoding='utf-8', errors='ignore') as f:
                tail = f.readlines()[-50:]
            lines.append('日志末尾50行:\n' + ''.join(tail))
        except Exception as e:
            lines.append('日志读取失败: ' + str(e))
        try:
            with open('diag.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            QMessageBox.information(self, '导出诊断', '诊断文件已生成: diag.txt')
        except Exception as e:
            QMessageBox.warning(self, '导出诊断', '写入失败: ' + str(e))


    def _load_version_info(self):
        import json
        import urllib.request
        # 禁用代理，防止访问本地端口被代理软件拦截
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        url = f"http://127.0.0.1:{self._chosen_port}/version"
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=3) as r:
                data = json.loads(r.read().decode())
            txt = (
                f"版本：{data.get('commit','?')} ({data.get('branch','?')}) | "
                f"Schema：{data.get('schema','?')} | "
                f"节点：{data.get('node_id','?')} | "
                f"端口：{data.get('port','?')}"
            )
        except Exception as e:
            txt = f"版本：不可用 [URL: {url}] ({e})"
        self.version_label.setText(txt)

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
        self.tray_menu = menu  # 保存引用，不用 setContextMenu（Windows 下会冲突）
        self.tray.activated.connect(self._on_tray_clicked)
        self.tray.show()

    def _on_tray_clicked(self, reason):
        try:
            _name = str(reason).split('.')[-1]
        except Exception:
            _name = ''
        if _name == 'Trigger':
            self._show_window()
        elif _name == 'Context':
            try:
                from PyQt6.QtGui import QCursor
                self.tray_menu.popup(QCursor.pos())
            except Exception:
                pass
    
    def _show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _real_quit(self):
        self._allow_close = True
        try:
            self._stop_hidden_nodes()
            if self.proc:
                pid = int(self.proc.processId())
                QProcess.startDetached('taskkill', ['/F', '/T', '/PID', str(pid)])
        except Exception:
            pass
        self.proc = None
        self.hidden_procs = []
        import os as _os_q
        _os_q._exit(0)

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

    # ---------- 隐藏节点 ----------
    def _start_hidden_nodes(self):
        """主 SASES 启动后，依次拉起 2 个隐藏节点。"""
        for i, port in enumerate(HIDDEN_NODE_PORTS, start=1):
            if self._port_busy(port):
                self.out(f'[启动器] 隐藏节点端口 {port} 被占用，跳过')
                continue
            p = QProcess(self)
            p.setWorkingDirectory(ROOT)
            env = QProcessEnvironment.systemEnvironment()
            env.insert('SASES_PORT', str(port))
            env.insert('SASES_NODE_ID', f'node-hidden-{i}')
            env.insert('HIVE_ROLE', 'slave')
            env.insert('HIVE_MASTER', f'http://127.0.0.1:{self._chosen_port}')
            env.insert('HIVE_PEERS', f'http://127.0.0.1:{self._chosen_port}')
            env.insert('ENABLE_HIVE', 'true')
            p.setProcessEnvironment(env)
            p.readyReadStandardOutput.connect(self._read_hidden)
            p.readyReadStandardError.connect(self._read_hidden)
            p.start(sys.executable, ['-m', 'core.hive.standalone'])
            self.hidden_procs.append(p)
            # 静默启动，不打印日志（隐藏节点对用户不可见）

    def _read_hidden(self):
        # 隐藏节点日志不输出到主窗口（保持用户无感）
        # 仅消费缓冲区，防止管道阻塞
        for p in list(self.hidden_procs):
            if p.bytesAvailable() > 0:
                p.readAllStandardOutput()
                p.readAllStandardError()

    def _stop_hidden_nodes(self):
        for p in self.hidden_procs:
            try:
                pid = int(p.processId())
                QProcess.startDetached('taskkill', ['/F', '/T', '/PID', str(pid)])
            except Exception:
                pass
        self.hidden_procs = []
        # 静默停止，不打印日志

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
            # 主服务就绪后，启动隐藏节点
            self._start_hidden_nodes()
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
        # 先停隐藏节点
        self._stop_hidden_nodes()
        if not self.proc:
            return
        pid = int(self.proc.processId())
        QProcess.startDetached('taskkill', ['/F', '/T', '/PID', str(pid)])
        self.out('[启动器] 已停止主服务 pid=%s' % pid)

    # ---------- 托盘行为 ----------
    def closeEvent(self, e):
        if self._allow_close:
            if self.proc:
                self.stop()
            e.accept()
            return
        e.ignore()
        self.hide()
        try:
            self.tray.showMessage(
                'SASES 启动器', '已最小化到托盘，双击图标恢复',
                QSystemTrayIcon.MessageIcon.Information, 2000
            )
        except Exception:
            pass
