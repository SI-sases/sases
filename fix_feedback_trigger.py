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

# 精确锚点：_pollTaskStatus 里的任务完成分支
old = """    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
    }"""

new = """    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
      // v0.39.0: 任务完成 → 显示反馈条（不依赖 WS）
      setTimeout(() => {
        try {
          _renderFeedbackBar(taskId, (window.chatState && window.chatState.conversationId) || null);
        } catch (e) { console.warn('[feedback] 轮询触发失败', e); }
      }, 300);
    }"""

if old in c and '_renderFeedbackBar(taskId, (window.chatState' not in c:
    c = c.replace(old, new, 1)
    print("+ _pollTaskStatus 完成分支加反馈条触发")
else:
    print("警告：锚点未匹配或已改过")
    print("请检查 chat.js 里 'last.review_result' 附近")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！下一步：")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发 swarm 任务 → 任务完成后 3-6 秒内出现 👍👎🤷")
print("3. 点 👎 → 显示'已记录'")
print("4. del fix_feedback_trigger.py")