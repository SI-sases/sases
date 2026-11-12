# fix.py
import os

p = 'launcher/ui/main_window.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 修复导包路径
if 'from launcher.ui.license_dialog import LicenseDialog' in c:
    c = c.replace('from launcher.ui.license_dialog import LicenseDialog', 'from ui.license_dialog import LicenseDialog')
    
# 同时也顺便把之前可能漏掉的其他 launcher. 前缀去掉，防止连带报错
c = c.replace('from launcher.', 'from ')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('✅ 启动器导包路径修复完成！')
