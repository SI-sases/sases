"""SASES 启动器入口。"""
import os
import sys
import socket
import subprocess
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton

# 单实例锁：绑定一个不对外开放的本地端口
_LOCK_PORT = 54821
_lock_sock = None

def _acquire_single_instance():
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', _LOCK_PORT))
        s.listen(1)
        _lock_sock = s
        return True
    except OSError:
        return False

class SetupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SASES 首次配置')
        self.setFixedSize(480, 240)
        # 统一风格：背景深灰，字体白
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: 'Microsoft YaHei';")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        title = QLabel("欢迎使用 SASES！")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4a90e2;")
        desc = QLabel("请输入您的 DeepSeek API Key 以启动本地服务\n（直接跳过则稍后在网页端配置）：")
        desc.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setStyleSheet("background-color: #2b2b2b; border: 1px solid #3c3c3c; padding: 10px; color: white; border-radius: 4px; font-size: 14px;")
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("保存并启动")
        btn_ok.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_ok.clicked.connect(self._on_ok_check)
        btn_skip = QPushButton("跳过")
        btn_skip.setStyleSheet("background-color: #3c3c3c; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_skip.clicked.connect(self.reject)
        
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_skip)
        btn_layout.addWidget(btn_ok)
        
        layout.addWidget(title)
        layout.addWidget(desc)
        from PyQt6.QtWidgets import QCheckBox
        self.agree_cb = QCheckBox("我已阅读并同意《免责声明》：本工具仅供学习交流，AI 生成内容及本地执行操作由使用者自行承担全部责任。")
        self.agree_cb.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        layout.addWidget(self.agree_cb)
        layout.addWidget(self.input)
        layout.addLayout(btn_layout)
        
        self.text = ""
        self.ok = False
        btn_ok.clicked.connect(self._on_ok)
        btn_skip.clicked.connect(self._on_skip)
        
    def _on_ok_check(self):
        if not self.agree_cb.isChecked():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "请先勾选同意免责声明！")
            return
        self.accept()


    def _on_ok(self):
        self.text = self.input.text()
        self.ok = True
        self.accept()
        
    def _on_skip(self):
        self.text = ""
        self.ok = False
        self.reject()

def main():
    import traceback
    import datetime
    def my_excepthook(exc_type, exc_value, exc_tb):
        with open("fatal_error.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now()}] Uncaught Exception:\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = my_excepthook

    if not _acquire_single_instance():
        try:
            app = QApplication(sys.argv)
            QMessageBox.warning(None, 'SASES 启动器', '启动器已在运行中。\n请检查任务栏或系统托盘。')
        except Exception:
            print('[launcher] 启动器已在运行中')
        sys.exit(1)

    try:
        out = subprocess.check_output('wmic process where "commandline like \'%run_forever.py%\'" get processid', shell=True).decode('gbk', errors='ignore')
        pids = [line.strip() for line in out.split('\n') if line.strip().isdigit()]
        if pids:
            for pid in pids:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[launcher] 已清理残留的后端进程")
    except Exception:
        pass

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root_dir, '.env')
    
    if not os.path.exists(env_path):
        app = QApplication(sys.argv)
        dialog = SetupDialog()
        dialog.exec()
        if dialog.ok and dialog.text.strip():
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f"DEEPSEEK_API_KEY={dialog.text.strip()}\n")
            QMessageBox.information(None, '配置成功', 'API Key 已保存，即将启动 SASES！')
        else:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("DEEPSEEK_API_KEY=\n")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    _base = sys._MEIPASS if getattr(sys, 'frozen', False) else base_dir
    ico_path = os.path.join(_base, 'launcher', 'icon.ico')
    if not os.path.exists(ico_path):
        ico_path = os.path.join(_base, 'icon.ico')
    
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))
        
    app.setQuitOnLastWindowClosed(False)
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
