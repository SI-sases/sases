"""SASES 启动器入口。"""
import os
import sys
import socket

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
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关键：关窗不退出，托盘还活着
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
