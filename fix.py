# fix.py
p = 'launcher/ui/main_window.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old_catch = '''        except urllib.error.HTTPError as e:
            err_msg = "激活失败"
            try:
                err_json = json.loads(e.read().decode('utf-8'))
                err_msg = err_json.get('detail', err_msg)
            except: pass
            self.lbl_license_status.setText(f"❌ {err_msg}")
            self.lbl_license_status.setStyleSheet("color: #ff3b30; margin-top: 10px;")'''

new_catch = '''        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            self.lbl_license_status.setText(f"❌ 失败({e.code}): {err_body}")
            self.lbl_license_status.setStyleSheet("color: #ff3b30; margin-top: 10px;")'''

c = c.replace(old_catch, new_catch)
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print("✅ 错误提示已增强！")
