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

changes = 0

# 改动 1：在 appendChild 后加 30 秒自动移除定时器
old1 = """  container.appendChild(bar);
  container.scrollTop = container.scrollHeight;
}"""

new1 = """  container.appendChild(bar);
  container.scrollTop = container.scrollHeight;
  // v0.39.2: 30 秒未操作自动移除
  bar._autoRemoveTimer = setTimeout(() => {
    try {
      if (bar.parentNode) bar.parentNode.removeChild(bar);
      console.log('[feedback] 30 秒未操作，自动移除');
    } catch (e) {}
  }, 30000);
}"""

if old1 in c and '_autoRemoveTimer' not in c:
    c = c.replace(old1, new1, 1)
    changes += 1
    print("改动 1: 加 30 秒自动移除")
else:
    print("警告：改动 1 锚点未匹配或已改过")

# 改动 2：点击时清掉自动移除定时器
old2 = """      const rating = btn.dataset.rating;
      console.log('[feedback] 点击', rating, 'task_id=', taskId);"""
new2 = """      const rating = btn.dataset.rating;
      if (bar._autoRemoveTimer) { clearTimeout(bar._autoRemoveTimer); bar._autoRemoveTimer = null; }
      console.log('[feedback] 点击', rating, 'task_id=', taskId);"""

if old2 in c and 'bar._autoRemoveTimer = null' not in c:
    c = c.replace(old2, new2, 1)
    changes += 1
    print("改动 2: 点击时清掉自动移除定时器")
else:
    print("警告：改动 2 锚点未匹配或已改过")

print(f"\n共 {changes} 处改动")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发任务 → 反馈条出现")
print("3. 30 秒不点 → 自动消失")
print("4. 30 秒内点 → 正常提交 + 3 秒后消失")
print("5. del fix_feedback_autohide.py")