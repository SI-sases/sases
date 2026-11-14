import os
import re

p = "launcher/ui/license_dialog.py"
if os.path.exists(p):
    c = open(p, "r", encoding="utf-8").read()
    
    # 匹配请求成功的逻辑，把有效期打印出来
    if "有效期至" not in c:
        # 寻找成功后的状态更新
        c = c.replace(
            'self.status_label.setText("✅ 激活成功！")',
            'expire = res_data.get("expire_at", "")[:10]\n        self.status_label.setText(f"✅ 激活成功！有效期至：{expire}")'
        )
        # 如果原版写的是其他文字
        c = re.sub(r'self\.status_label\.setText\(".*?激活成功.*?"\)', 
                   'expire = res_data.get("expire_at", "")[:10]\n        self.status_label.setText(f"✅ 激活成功！有效期至：{expire}")', 
                   c)
        
        open(p, "w", encoding="utf-8").write(c)
        print("✅ 启动器 UI 已修复，重新打开启动器就能看到有效期了。")
    else:
        print("✅ 启动器已有有效期显示。")
else:
    print("❌ 找不到 license_dialog.py")