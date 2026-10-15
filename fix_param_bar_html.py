import os
import shutil
import ast
from datetime import datetime

FP = "static/index.html"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"static__index.html.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

old = '''          <div class="chat-input-area">
            <button id="toggle-voice-btn" class="voice-toggle-btn" aria-label="语音切换">🎤</button>'''

new = '''          <div id="param-bar" class="param-bar">
            <span id="param-rounds" class="param-pill" title="点击设置本轮最大步数">⚙️ 8步</span>
          </div>
          <div class="chat-input-area">
            <button id="toggle-voice-btn" class="voice-toggle-btn" aria-label="语音切换">🎤</button>'''

if old in c:
    c = c.replace(old, new, 1)
    print("已插入 param-bar")
else:
    print("警告：锚点未匹配")
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 下一步：给 style.css 加样式")