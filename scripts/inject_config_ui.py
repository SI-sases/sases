import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "launcher", "ui", "main_window.py")

with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace(
    'self.sidebar.addItems(["📜 运行日志", "🛠 诊断工具", "🔄 检查更新"])',
    'self.sidebar.addItems(["📜 运行日志", "⚙️ 服务配置", "🛠 诊断工具", "🔄 检查更新"])'
)

code = code.replace(
    'QFrame\n)',
    'QFrame, QLineEdit\n)'
)

ui_code = """        # 页面 1：服务配置
        page_config = QWidget()
        config_layout = QVBoxLayout(page_config)
        config_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cfg_title = QLabel("服务配置")
        cfg_title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")

        self.cfg_key_input = QLineEdit()
        self.cfg_key_input.setPlaceholderText("输入 DeepSeek API Key...")
        self.cfg_key_input.setFixedWidth(300)
        self.cfg_key_input.setStyleSheet("background-color: #2b2b2b; color: white; padding: 8px; border-radius: 4px;")

        env_p = os.path.join(ROOT, ".env")
        if os.path.exists(env_p):
            with open(env_p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        self.cfg_key_input.setText(line.strip().split("=")[1])

        btn_save_cfg = QPushButton("保存配置")
        btn_save_cfg.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_save_cfg.clicked.connect(self._save_config)

        config_layout.addWidget(cfg_title)
        config_layout.addWidget(self.cfg_key_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(btn_save_cfg, alignment=Qt.AlignmentFlag.AlignCenter)

        # 页面 2：诊断工具
        page_diag = QWidget()"""

if "# 页面 1：服务配置" not in code:
    code = code.replace("        # 页面 1：诊断工具\n        page_diag = QWidget()", ui_code)

save_method = """    def _save_config(self):
        key = self.cfg_key_input.text().strip()
        env_p = os.path.join(ROOT, ".env")
        with open(env_p, "w", encoding="utf-8") as f:
            f.write(f"DEEPSEEK_API_KEY={key}\\n")
        QMessageBox.information(self, "成功", "配置已保存，重启服务生效。")

    def _on_sidebar_changed(self, index):"""

if "def _save_config" not in code:
    code = code.replace("    def _on_sidebar_changed(self, index):", save_method)

code = code.replace(
    'self.stacked_widget.addWidget(page_log)\n        self.stacked_widget.addWidget(page_diag)',
    'self.stacked_widget.addWidget(page_log)\n        self.stacked_widget.addWidget(page_config)\n        self.stacked_widget.addWidget(page_diag)'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("UI 注入成功！")
