import os, json, urllib.request
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from launcher.hardware import get_hardware_fingerprint

class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SASES 激活")
        self.setFixedSize(350, 200)
        
        self.license_data = None
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("请输入您的 SASES 卡密:"))
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("例如: SASES-XXXX-XXXX")
        layout.addWidget(self.input_key)
        
        self.btn_activate = QPushButton("立即激活")
        self.btn_activate.clicked.connect(self._do_activate)
        layout.addWidget(self.btn_activate)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: red;")
        layout.addWidget(self.lbl_status)

    def _do_activate(self):
        key = self.input_key.text().strip()
        if not key:
            self.lbl_status.setText("卡密不能为空")
            return
            
        self.btn_activate.setEnabled(False)
        self.lbl_status.setText("正在连接云端验证...")
        self.lbl_status.setStyleSheet("color: blue;")
        
        fp = get_hardware_fingerprint()
        
        # 这里填你云端的真实 IP
        api_url = "http://47.96.87.147:8001/auth/license/activate"
        payload = json.dumps({
            "key_code": key,
            "device_fingerprint": fp,
            "user_id": 1  # 默认本地主账号为 1
        }).encode('utf-8')
        
        req = urllib.request.Request(api_url, data=payload, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                self.license_data = res_data
                self.lbl_status.setText("✅ 激活成功！")
                self.lbl_status.setStyleSheet("color: green;")
                self.accept() # 关闭弹窗并返回成功
        except urllib.error.HTTPError as e:
            err_msg = "激活失败"
            try:
                err_json = json.loads(e.read().decode('utf-8'))
                err_msg = err_json.get('detail', err_msg)
            except:
                pass
            self.lbl_status.setText(f"❌ {err_msg}")
            self.lbl_status.setStyleSheet("color: red;")
            self.btn_activate.setEnabled(True)
        except Exception as e:
            self.lbl_status.setText(f"❌ 网络错误: {str(e)}")
            self.lbl_status.setStyleSheet("color: red;")
            self.btn_activate.setEnabled(True)
