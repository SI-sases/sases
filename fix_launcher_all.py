import os
import shutil
import ast
from datetime import datetime

backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def _backup(fp):
    b = os.path.join(backup_dir, fp.replace("/", "__").replace("\\", "__") + f".{ts}.bak")
    shutil.copy2(fp, b)
    print(f"  备份: {b}")
    return b

def _write(fp, content, backup):
    try:
        ast.parse(content)
    except SyntaxError as e:
        print(f"  语法检查失败: {e}，回滚")
        shutil.copy2(backup, fp)
        return False
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  已写入，大小 {os.path.getsize(fp)} 字节")
    return True

# ========== 改动 1：launcher/launcher.py 加图标 ==========
print("\n[1/3] 修改 launcher/launcher.py")
FP1 = "launcher/launcher.py"
b1 = _backup(FP1)
with open(FP1, 'r', encoding='utf-8') as f:
    c1 = f.read()

# 加 import
if 'from PyQt6.QtGui import QIcon' not in c1:
    c1 = c1.replace(
        "    from PyQt6.QtWidgets import QApplication\n    from ui.main_window import MainWindow",
        "    from PyQt6.QtWidgets import QApplication\n    from PyQt6.QtGui import QIcon\n    from ui.main_window import MainWindow",
        1
    )
    print("  + 加 import QIcon")

# 加 setWindowIcon
if 'setWindowIcon' not in c1:
    c1 = c1.replace(
        "    app = QApplication(sys.argv)\n    app.setQuitOnLastWindowClosed(False)",
        "    app = QApplication(sys.argv)\n    _icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')\n    if os.path.exists(_icon_path):\n        app.setWindowIcon(QIcon(_icon_path))\n    app.setQuitOnLastWindowClosed(False)",
        1
    )
    print("  + 加 setWindowIcon")

_write(FP1, c1, b1)

# ========== 改动 2：main_window.py 修托盘退出 + 修关闭慢 + 修图标 ==========
print("\n[2/3] 修改 launcher/ui/main_window.py")
FP2 = "launcher/ui/main_window.py"
b2 = _backup(FP2)
with open(FP2, 'r', encoding='utf-8') as f:
    c2 = f.read()

# 2a. 修托盘 TypeError
old_click = '''    def _on_tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()'''

new_click = '''    def _on_tray_clicked(self, reason):
        try:
            if int(reason) == int(QSystemTrayIcon.ActivationReason.Trigger):
                self._show_window()
        except Exception:
            self._show_window()'''

if old_click in c2:
    c2 = c2.replace(old_click, new_click, 1)
    print("  修托盘 TypeError")
elif '_on_tray_clicked' in c2:
    # 兜底：替换整个函数体
    import re
    c2 = re.sub(
        r'def _on_tray_clicked\(self, reason\):.*?self\._show_window\(\)',
        '''def _on_tray_clicked(self, reason):
        try:
            if int(reason) == int(QSystemTrayIcon.ActivationReason.Trigger):
                self._show_window()
        except Exception:
            self._show_window()''',
        c2, count=1, flags=re.DOTALL
    )
    print("  修托盘 TypeError (正则)")
else:
    print("  跳过托盘修复（未找到函数）")

# 2b. 修关闭慢 + _real_quit 释放 QProcess
old_quit = '''    def _real_quit(self):
        self._allow_close = True
        self.close()'''

new_quit = '''    def _real_quit(self):
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
        _os_q._exit(0)'''

if old_quit in c2:
    c2 = c2.replace(old_quit, new_quit, 1)
    print("  修关闭慢 + 强制退出")

# 2c. 托盘图标替换（跨行）
old_icon = '''        self.tray.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )'''
new_icon = '''        _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icon.ico')
        if os.path.exists(_ico):
            self.tray.setIcon(QIcon(_ico))
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))'''

if old_icon in c2:
    c2 = c2.replace(old_icon, new_icon, 1)
    print("  替换托盘图标")
else:
    print("  跳过图标替换（锚点未匹配）")

_write(FP2, c2, b2)

print("\n[3/3] 完成")

# 清理临时脚本提示
print("\n接下来：")
print("1. 重启启动器验证：python launcher/launcher.py")
print("2. 验证通过后，删除本脚本：del fix_launcher_all.py")