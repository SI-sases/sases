"""SASES 启动器入口。"""
import os
import sys
import socket
import subprocess
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox

# 单实例锁：绑定一个不对外开放的本地端口
# 进程退出时端口自动释放，无需清理死锁文件
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


def main():
    if not _acquire_single_instance():
        # 已有实例在跑
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            QMessageBox.warning(
                None, 'SASES 启动器',
                '启动器已在运行中。\n请检查任务栏或系统托盘。'
            )
        except Exception:
            print('[launcher] 启动器已在运行中')
        sys.exit(1)

    # 延迟 import（PyQt 只在真要起窗口时才加载）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from PyQt6.QtWidgets import QApplication
    # ====== 1. 端口残留清理 ======
    try:
        out = subprocess.check_output('wmic process where "commandline like \'%run_forever.py%\'" get processid', shell=True).decode('gbk', errors='ignore')
        pids = [line.strip() for line in out.split('\n') if line.strip().isdigit()]
        if pids:
            for pid in pids:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[launcher] 已清理残留的后端进程")
    except Exception:
        pass

    # ====== 2. 首次运行向导 ======
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root_dir, '.env')

    if not os.path.exists(env_path):
        app = QApplication(sys.argv)
        text, ok = QInputDialog.getText(
            None, 'SASES 首次配置',
            '欢迎使用 SASES！\n\n请输入您的 DeepSeek API Key 以启动本地服务（直接回车跳过，稍后在网页配置）：',
            # 已移除 PyQt6 不兼容的 echo 参数
        )
        if ok and text.strip():
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f"DEEPSEEK_API_KEY={text.strip()}\n")
            QMessageBox.information(None, '配置成功', 'API Key 已保存，即将启动 SASES！')
        else:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("DEEPSEEK_API_KEY=\n")


    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, 'icon.ico')
    if not os.path.exists(ico_path):
        ico_path = os.path.join(base_dir, 'launcher', 'icon.ico')
    app.setWindowIcon(QIcon(ico_path))
    app.setQuitOnLastWindowClosed(False)  # 关键：关窗不退出，托盘还活着
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
