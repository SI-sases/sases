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

# 在 _pollTaskStatus 里任务完成时触发反馈条
old = """    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
    }"""

new = """    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
      // 新增：轮询路径触发反馈条（不依赖 WS）
      setTimeout(() => {
        try {
          _renderFeedbackBar(taskId, window.chatState && window.chatState.conversationId);
        } catch (e) { console.warn('[feedback] 轮询触发失败', e); }
      }, 200);
    }"""

if old in c and '_renderFeedbackBar(taskId' not in c:
    c = c.replace(old, new, 1)
    print("+ _pollTaskStatus 里加反馈条触发")
else:
    print("警告：锚点未匹配或已改过")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发 swarm 任务 → 3-6 秒后反馈条出现")
print("3. del fix_feedback_ui_v2.py")