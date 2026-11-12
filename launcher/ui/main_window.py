"""SASES 启动器主窗口（UI 优化满血版 - 顶栏与设置重构）。"""
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
import re
import shutil
import datetime
import winreg
import launcher_config

CURRENT_LAUNCHER_VERSION = "1.0.0"

from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, Qt
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QSystemTrayIcon, QMenu, QStyle, QListWidget, QStackedWidget,
    QFrame, QLineEdit, QFileDialog, QCheckBox, QScrollArea, QDialog
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
        
        # 设置图标
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

        # ========== 左侧导航（精简为两项） ==========
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(180)
        sidebar_container.setStyleSheet("background-color: #2b2b2b;")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setStyleSheet("""
            QListWidget { background-color: #2b2b2b; color: #aaaaaa; border: none; outline: none; font-size: 14px; }
            QListWidget::item { height: 50px; padding-left: 20px; border-bottom: 1px solid #3c3c3c; }
            QListWidget::item:selected { background-color: #3c3f41; color: #ffffff; border-left: 4px solid #4a90e2; }
            QListWidget::item:hover:!selected { background-color: #333333; }
        """)
        self.sidebar.addItems(["📜 运行日志", "⚙️ 统一设置", "🔑 卡密激活"])
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        sidebar_layout.addWidget(self.sidebar)
        
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

        # 🌟 顶部状态栏与快捷按钮
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        
        self.status_label = QLabel('未运行')
        self.status_label.setStyleSheet("color: #ff5c5c; font-weight: bold; font-size: 14px;")
        top_layout.addWidget(self.status_label)
        top_layout.addSpacing(20)

        # 快捷操作按钮
        self.btn_quick_start = QPushButton('启动服务')
        self.btn_quick_start.setStyleSheet("background-color: #4a90e2; color: white; padding: 5px 15px; border-radius: 4px; font-weight: bold;")
        self.btn_quick_start.clicked.connect(self.start)
        
        self.btn_quick_web = QPushButton('打开网页')
        self.btn_quick_web.setStyleSheet("background-color: #34c759; color: white; padding: 5px 15px; border-radius: 4px; font-weight: bold;")
        self.btn_quick_web.clicked.connect(self._open_browser_manual)
        self.btn_quick_web.setEnabled(False)
        
        top_layout.addWidget(self.btn_quick_start)
        top_layout.addWidget(self.btn_quick_web)

        top_layout.addStretch(1)
        
        self.version_label = QLabel('版本：未加载')
        self.version_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        self.btn_version = QPushButton('刷新版本')
        self.btn_version.clicked.connect(self._load_version_info)
        self.btn_version.setStyleSheet("background: transparent; color: #4a90e2; border: none; text-decoration: underline; cursor: pointer;")
        
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

        # 页面 1：统一设置页
        page_settings = QWidget()
        page_settings.setStyleSheet("background-color: #1e1e1e;")
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")
        
        settings_content = QWidget()
        settings_content.setStyleSheet("background-color: #1e1e1e;")
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(40, 30, 40, 30)
        settings_layout.setSpacing(20)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -- 区块 1：模型配置 --
        cfg_title = QLabel("模型服务配置")
        cfg_title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold;")
        self.cfg_key_input = QLineEdit()
        self.cfg_key_input.setPlaceholderText("API Key (本地模型可留空)")
        self.cfg_key_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 10px; border-radius: 4px;")
        self.cfg_url_input = QLineEdit()
        self.cfg_url_input.setPlaceholderText("接口地址 (如 https://api.deepseek.com/v1)")
        self.cfg_url_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 10px; border-radius: 4px;")
        self.cfg_model_input = QLineEdit()
        self.cfg_model_input.setPlaceholderText("模型名称 (如 deepseek-chat)")
        self.cfg_model_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 10px; border-radius: 4px;")
        
        env_p = os.path.join(ROOT, ".env")
        if os.path.exists(env_p):
            with open(env_p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="): self.cfg_key_input.setText(line.strip().split("=")[1])
                    elif line.startswith("DEEPSEEK_BASE_URL="): self.cfg_url_input.setText(line.strip().split("=")[1])
                    elif line.startswith("MODEL_NAME="): self.cfg_model_input.setText(line.strip().split("=")[1])

        btn_save_cfg = QPushButton("保存配置")
        btn_save_cfg.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_save_cfg.clicked.connect(self._save_config)

        # -- 区块 2：系统行为 --
        sys_title = QLabel("系统行为")
        sys_title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold; margin-top: 20px;")
        self.chk_autostart = QCheckBox("开机自动启动 SASES 启动器")
        self.chk_autostart.setStyleSheet("color: #ddd; font-size: 14px;")
        self.chk_autostart.setChecked(self._get_autostart_status())
        self.chk_autostart.stateChanged.connect(self._toggle_autostart)

        # -- 区块 3：维护工具 --
        tool_title = QLabel("维护与诊断")
        tool_title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold; margin-top: 20px;")
        
        btn_do_update = QPushButton("检查并安装更新")
        btn_do_update.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_do_update.clicked.connect(self._check_update)
        
        btn_do_diag = QPushButton("生成诊断报告")
        btn_do_diag.setStyleSheet("background-color: #ff9500; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_do_diag.clicked.connect(self._export_diag)

        # 组装设置页
        settings_layout.addWidget(cfg_title)
        settings_layout.addWidget(self.cfg_key_input)
        settings_layout.addWidget(self.cfg_url_input)
        settings_layout.addWidget(self.cfg_model_input)
        
        link_label = QLabel('<a href="https://platform.deepseek.com/api_keys" style="color: #4a90e2; text-decoration: none;">👉 点击这里去 DeepSeek 官网获取 API Key</a>')
        link_label.setOpenExternalLinks(True)
        settings_layout.addWidget(link_label)
        settings_layout.addWidget(btn_save_cfg)

        settings_layout.addWidget(sys_title)
        settings_layout.addWidget(self.chk_autostart)

        settings_layout.addWidget(tool_title)
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(btn_do_update)
        tool_layout.addWidget(btn_do_diag)
        tool_layout.addStretch(1)
        settings_layout.addLayout(tool_layout)

        settings_scroll.setWidget(settings_content)
        p_set_layout = QVBoxLayout(page_settings)
        p_set_layout.setContentsMargins(0, 0, 0, 0)
        p_set_layout.addWidget(settings_scroll)

        self.stacked_widget.addWidget(page_log)
        self.stacked_widget.addWidget(page_settings)
        
        # ===== 卡密页面（第三页） =====
        self.page_license = QWidget()
        license_layout = QVBoxLayout(self.page_license)
        license_layout.setContentsMargins(30, 30, 30, 30)
        license_layout.setSpacing(15) # 增加元素间距，告别拥挤
        
        title_lic = QLabel("卡密激活")
        title_lic.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        license_layout.addWidget(title_lic)
        
        desc_lbl = QLabel("请输入您的 SASES 卡密（例如: SASES-VIP-8888）：")
        desc_lbl.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        license_layout.addWidget(desc_lbl)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("在此输入卡密...")
        self.license_input.setStyleSheet("padding: 10px; border: 1px solid #555; border-radius: 4px; background: #3c3f41; color: white; font-size: 14px;")
        license_layout.addWidget(self.license_input)
        
        self.btn_activate = QPushButton("立即连接云端激活")
        self.btn_activate.setStyleSheet("padding: 10px; background: #4a90e2; color: white; border-radius: 4px; font-weight: bold; margin-top: 10px;")
        self.btn_activate.clicked.connect(self._do_activate)
        license_layout.addWidget(self.btn_activate)
        
        self.lbl_license_expire = QLabel("")
        license_layout.addWidget(self.lbl_license_expire)
        self._update_license_expire()

        self.lbl_license_status = QLabel("")
        self.lbl_license_status.setStyleSheet("color: #ff9500; font-size: 13px; margin-top: 10px;")
        license_layout.addWidget(self.lbl_license_status)
        
        license_layout.addStretch()
        self.stacked_widget.addWidget(self.page_license)
        # ==============================
        
        # ========== 底部操作区（保留大圆按钮） ==========
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

    # ====== 开机自启与操作逻辑 ======
    def _get_autostart_status(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "SASES_Launcher")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _toggle_autostart(self, state):
        enable = (state == Qt.CheckState.Checked.value)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enable:
                if getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}"'
                else:
                    exe_path = f'"{sys.executable}" "{os.path.join(ROOT, "launcher", "launcher.py")}"'
                winreg.SetValueEx(key, "SASES_Launcher", 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, "SASES_Launcher")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"修改开机启动失败: {e}")
            self.chk_autostart.setChecked(not enable)

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

    def _update_license_expire(self):
        import os, json
        lic_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "license.json")
        if os.path.exists(lic_path):
            try:
                with open(lic_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    exp = data.get("expire_at", "")
                    if exp:
                        self.lbl_license_expire.setText(f"当前授权有效期至：{exp[:10]}")
                        self.lbl_license_expire.setStyleSheet("color: #34c759; font-size: 13px;")
                        return
            except: pass
        
        cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "launcher_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    exp = cfg.get("license_expire_at")
                    if exp:
                        self.lbl_license_expire.setText(f"当前授权有效期至：{exp[:10]}")
                        self.lbl_license_expire.setStyleSheet("color: #34c759; font-size: 13px;")
                        return
            except: pass
        self.lbl_license_expire.setText("当前未激活或授权已失效")
        self.lbl_license_expire.setStyleSheet("color: #ff9500; font-size: 13px;")

    def _do_activate(self):
        key = self.license_input.text().strip()
        if not key:
            self.lbl_license_status.setText("❌ 卡密不能为空")
            self.lbl_license_status.setStyleSheet("color: #ff3b30; margin-top: 10px;")
            return
            
        self.lbl_license_status.setText("正在连接云端验证...")
        self.lbl_license_status.setStyleSheet("color: #4a90e2; margin-top: 10px;")
        self.btn_activate.setEnabled(False)
        
        import urllib.request, urllib.error, json
        import launcher_config
        
        fp = "unknown_fp"
        try:
            from hardware import get_hardware_fingerprint
            fp = get_hardware_fingerprint()
        except: pass
            
        api_url = "http://47.96.87.147:8001/auth/license/activate"
        payload = json.dumps({"key_code": key, "device_fingerprint": fp, "user_id": 1}).encode('utf-8')
        req = urllib.request.Request(api_url, data=payload, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                self.lbl_license_status.setText("✅ 激活成功！")
                self.lbl_license_status.setStyleSheet("color: #34c759; margin-top: 10px;")
                
                cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "launcher_config.json")
                self.cfg["license_expire_at"] = res_data.get("expire_at")
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, ensure_ascii=False, indent=2)
                    
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            self.lbl_license_status.setText(f"❌ 失败({e.code}): {err_body}")
            self.lbl_license_status.setStyleSheet("color: #ff3b30; margin-top: 10px;")
        except Exception as e:
            self.lbl_license_status.setText(f"❌ 网络错误: {str(e)}")
            self.lbl_license_status.setStyleSheet("color: #ff3b30; margin-top: 10px;")
            
        self.btn_activate.setEnabled(True)

    def _on_sidebar_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)


    def _set_running_ui(self, is_running):
        if is_running:
            self.status_label.setText(f"运行中 :{self._chosen_port}")
            self.status_label.setStyleSheet("color: #34c759; font-weight: bold; font-size: 14px;")
            self.btn_toggle.setText("⏹")
            self.btn_toggle.setStyleSheet("QPushButton { background-color: #ff5c5c; color: white; border-radius: 30px; font-size: 24px; } QPushButton:hover { background-color: #d94b4b; }")
            self.btn_quick_start.setVisible(False)
            self.btn_quick_web.setEnabled(True)
        else:
            self.status_label.setText("未运行")
            self.status_label.setStyleSheet("color: #ff5c5c; font-weight: bold; font-size: 14px;")
            self.btn_toggle.setText("▶")
            self.btn_toggle.setStyleSheet("QPushButton { background-color: #4a90e2; color: white; border-radius: 30px; font-size: 24px; padding-left: 5px; } QPushButton:hover { background-color: #357abd; }")
            self.btn_quick_start.setVisible(True)
            self.btn_quick_web.setEnabled(False)

    def _open_browser_manual(self):
        url = f"http://127.0.0.1:{self._chosen_port}/static/index.html"
        webbrowser.open(url)

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
            txt = f"v{data.get('commit','?')} ({data.get('branch','?')})"
        except Exception:
            txt = "版本：未加载"
        self.version_label.setText(txt)

    def _export_diag(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"diag_{ts}.zip"
        save_path, _ = QFileDialog.getSaveFileName(self, "保存诊断包", default_name, "Zip Files (*.zip)")
        if not save_path: return
        try:
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for log_name in ["sases.log", "run.log", "fatal_error.log"]:
                    log_path = os.path.join(self.work_dir, log_name)
                    if os.path.exists(log_path):
                        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                            z.writestr(log_name, "".join(f.readlines()[-1000:]))
                env_path = os.path.join(self.work_dir, ".env")
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
                        z.writestr(".env.masked", re.sub(r'(sk-[a-zA-Z0-9]{5})[a-zA-Z0-9]+', r'\1***', f.read()))
                z.writestr("diag_info.txt", f"Time: {ts}\nPython: {sys.version}\nCWD: {os.getcwd()}\n")
            QMessageBox.information(self, "成功", f"诊断包已生成：\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"生成失败: {e}")

    def _check_update(self):
        url = "http://47.96.87.147:8001/static/downloads/version.json"
        try:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(url)
            with opener.open(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                remote_build = data.get("build_time", "未知")
        except Exception:
            QMessageBox.information(self, "提示", "无法连接更新服务器或已是最新。")
            return

        local_file = os.path.join(self.work_dir, "version.json")
        local_build = "未知"
        if os.path.exists(local_file):
            try:
                with open(local_file, "r", encoding="utf-8") as f: local_build = json.load(f).get("build_time", "未知")
            except: pass

        if remote_build != local_build:
            reply = QMessageBox.question(self, "发现新版本", f"云端：{remote_build}\n本地：{local_build}\n\n是否立即更新？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop()
                QTimer.singleShot(1000, self.start)
        else:
            QMessageBox.information(self, "已是最新", "当前系统已是最新版本。")

    def _check_existing(self):
        try:
            proxy = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy)
            with opener.open(f"http://127.0.0.1:{self._chosen_port}/version", timeout=2):
                self._log("[启动器] 检测到服务已在后台运行")
                self._set_running_ui(True)
                self._load_version_info()
        except Exception: pass

    def start(self):
        if self.proc is not None: return
        self._set_running_ui(True)
        self.sidebar.setCurrentRow(0)
        self._real_start_service()
        self._log("[启动器] 正在通过服务器检查代码更新...")
        import threading
        threading.Thread(target=self._bg_download_update, daemon=True).start()

    def _bg_download_update(self):
        try:
            url = "http://47.96.87.147:8001/static/downloads/code_update.zip"
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(url)
            with opener.open(req, timeout=10) as resp:
                data = resp.read()
            core_dir = os.path.join(self.work_dir, "core")
            static_dir = os.path.join(self.work_dir, "static")
            core_bak = os.path.join(self.work_dir, "core.bak")
            static_bak = os.path.join(self.work_dir, "static.bak")
            
            if os.path.exists(core_dir):
                if os.path.exists(core_bak): shutil.rmtree(core_bak, ignore_errors=True)
                shutil.copytree(core_dir, core_bak)
            if os.path.exists(static_dir):
                if os.path.exists(static_bak): shutil.rmtree(static_bak, ignore_errors=True)
                shutil.copytree(static_dir, static_bak)

            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if "users.db" in info.filename or ".env" in info.filename or "hive-nodes" in info.filename: continue
                    z.extract(info, self.work_dir)
            QTimer.singleShot(0, lambda: self._log("[启动器] ✅ 更新包已静默下载并解压完成（下次启动生效）。"))
        except Exception as e:
            QTimer.singleShot(0, lambda: self._log(f"[启动器] 更新检查跳过或失败: {e}"))

    def _real_start_service(self):
        self._kill_port_process(self._chosen_port)
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
        QTimer.singleShot(3000, self._start_hidden_nodes)
        QTimer.singleShot(5000, self._load_version_info)

    def _start_hidden_nodes(self):
        for i, port in enumerate(HIDDEN_NODE_PORTS, start=1):
            db_dir = os.path.join(os.getcwd(), f"hive-nodes/{port}")
            os.makedirs(db_dir, exist_ok=True)
            env = os.environ.copy()
            env["SASES_PORT"] = str(port)
            env["SASES_NODE_ID"] = f"node-hidden-{i}"
            env["HIVE_ROLE"] = "slave"
            env["HIVE_MASTER"] = "http://127.0.0.1:8001"
            env["SASES_DB_PATH"] = os.path.join(db_dir, "replica.db")
            python_exe = os.path.join(os.getcwd(), "python-embed", "python.exe")
            if not os.path.exists(python_exe): python_exe = sys.executable
            subprocess.Popen([python_exe, "scripts/run_forever.py"], env=env, creationflags=subprocess.CREATE_NO_WINDOW)

    def stop(self):
        self._log("[启动器] 正在停止 SASES 服务...")
        if self.proc:
            pid = self.proc.processId()
            if pid:
                try: subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                except Exception: pass
            self.proc.terminate()
            if not self.proc.waitForFinished(1000): self.proc.kill()
        self._on_finished()

    def _on_finished(self):
        self.proc = None
        self._set_running_ui(False)
        self._log("[启动器] 服务已停止")

    def _read_out(self):
        if not self.proc: return
        raw = self.proc.readAllStandardOutput().data()
        text = _decode_child_line(raw)
        for line in text.splitlines():
            if any(w in line for w in ["fatal: not a git repository", "PyTorch was not found", "[hive-register] no peers"]): continue
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
        _base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _ico = os.path.join(_base_dir, 'launcher', 'icon.ico')
        if not os.path.exists(_ico): _ico = os.path.join(_base_dir, 'icon.ico')
        if os.path.exists(_ico): self.tray.setIcon(QIcon(_ico))
        else: self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        self.tray.setToolTip('SASES 启动器')
        menu = QMenu()
        act_show = QAction('显示主界面', self); act_show.triggered.connect(self._show_window)
        act_start = QAction('启动服务', self); act_start.triggered.connect(self.start)
        act_stop = QAction('停止服务', self); act_stop.triggered.connect(self.stop)
        act_quit = QAction('退出', self); act_quit.triggered.connect(self._real_quit)
        menu.addAction(act_show); menu.addSeparator()
        menu.addAction(act_start); menu.addAction(act_stop); menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger: self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event):
        if not self._allow_close:
            event.ignore()
            self.hide()
        else: event.accept()

    def _real_quit(self):
        self._allow_close = True
        self.stop()
        self.close()
        QTimer.singleShot(200, lambda: os._exit(0))
