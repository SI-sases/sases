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

old = "  if (_display.startsWith('[SUMMARY]:')) _display = _display.slice(10);"
new = """  if (_display.startsWith('[SUMMARY]:')) {
    _display = _display.slice(10);
    try { _hideStopBtn(); } catch (e) {}
  }"""

if old in c:
    c = c.replace(old, new, 1)
    print("改动: 收到 [SUMMARY]: 时自动隐藏 ⏹")
else:
    print("警告：锚点未匹配")
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发 swarm 任务 → ⏹ 出现 → 任务完成 → ⏹ 自动消失")
print("3. del fix_stop_btn_autohide.py")