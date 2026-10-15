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

# 1. 加轮询函数（在 _hideStopBtn 后）
old1 = """function _hideStopBtn() {"""
new1 = """async function _pollTaskStatus(taskId) {
  // 轮询任务状态，任务完成后自动隐藏停止按钮
  if (!window.chatState || window.chatState.currentTaskId !== taskId) return;
  try {
    const token = localStorage.getItem('sases_token');
    const r = await fetch('/swarm/reviews?task_id=' + encodeURIComponent(taskId) + '&limit=1', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!r.ok) return;
    const data = await r.json();
    const reviews = data.reviews || [];
    if (!reviews.length) return;
    const last = reviews[0];
    // 任务已完结（pass 或 done）
    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
    }
  } catch (e) { /* 忽略 */ }
}

function _startPollTimer(taskId) {
  if (window.chatState && window.chatState._pollTimer) {
    clearInterval(window.chatState._pollTimer);
  }
  if (window.chatState) {
    window.chatState._pollTimer = setInterval(() => _pollTaskStatus(taskId), 3000);
  }
}

function _hideStopBtn() {"""

if old1 in c and '_pollTaskStatus' not in c:
    c = c.replace(old1, new1, 1)
    print("+ 加 _pollTaskStatus / _startPollTimer")

# 2. _showStopBtn 里启动轮询
old2 = """  if (window.chatState) {
    if (window.chatState._stopTimer) clearTimeout(window.chatState._stopTimer);
    window.chatState._stopTimer = setTimeout(() => _hideStopBtn(), 30000);
  }
}"""
new2 = """  if (window.chatState) {
    if (window.chatState._stopTimer) clearTimeout(window.chatState._stopTimer);
    window.chatState._stopTimer = setTimeout(() => _hideStopBtn(), 30000);
  }
  try { _startPollTimer(taskId); } catch (e) {}
}"""
if old2 in c and '_startPollTimer(taskId);' not in c:
    c = c.replace(old2, new2, 1)
    print("+ _showStopBtn 里启动轮询")

# 3. _hideStopBtn 里清轮询
old3 = """  const stopBtn = document.getElementById('stop-btn');
  if (stopBtn) stopBtn.style.display = 'none';
  if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
}"""
new3 = """  if (window.chatState && window.chatState._pollTimer) {
    clearInterval(window.chatState._pollTimer);
    window.chatState._pollTimer = null;
  }
  const stopBtn = document.getElementById('stop-btn');
  if (stopBtn) stopBtn.style.display = 'none';
  if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
}"""
if old3 in c and '_pollTimer = null' not in c:
    c = c.replace(old3, new3, 1)
    print("+ _hideStopBtn 里清轮询")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器")
print("2. 发 swarm 任务 → ⏹ 出现 → 3-6 秒后自动消失")
print("3. del fix_stop_poll.py")