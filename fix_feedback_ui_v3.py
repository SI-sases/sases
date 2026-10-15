import os
import shutil
from datetime import datetime

FP = "static/modules/chat.js"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"static__modules__chat.js.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

old = "window._showStopBtn = _showStopBtn;"
new = "window._renderFeedbackBar = _renderFeedbackBar;\nwindow._showStopBtn = _showStopBtn;"

if old in c and 'window._renderFeedbackBar' not in c:
    c = c.replace(old, new, 1)
    print("+ 挂载 window._renderFeedbackBar")
else:
    print("警告：锚点未匹配或已挂载")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新")
print("2. Console 测：window._renderFeedbackBar('test', 101)")
print("3. del fix_feedback_ui_v3.py")