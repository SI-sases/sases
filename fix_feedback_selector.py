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

old = """function _tryFlushPendingFeedback() {
  // 检查是否该渲染挂起的反馈条
  const st = window.chatState;
  if (!st || !st._pendingFeedback) return;
  const container = document.getElementById('chat-messages');
  if (!container) return;
  // 找最后一个消息行
  const rows = container.querySelectorAll('.message-row');
  if (!rows.length) return;
  const lastRow = rows[rows.length - 1];
  // 最后一条是用户消息 → AI 还没回复，不渲染
  if (lastRow.classList.contains('user')) return;
  // 渲染
  const { taskId, conversationId } = st._pendingFeedback;
  st._pendingFeedback = null;
  console.log('[feedback] AI 回复落位，渲染反馈条', taskId);
  _renderFeedbackBar(taskId, conversationId);
}"""

new = """function _tryFlushPendingFeedback() {
  // 检查是否该渲染挂起的反馈条
  const st = window.chatState;
  if (!st || !st._pendingFeedback) return;
  const container = document.getElementById('chat-messages');
  if (!container) return;
  // v0.39.4: 消息元素用 data-role 属性标记，不是 class
  const rows = container.querySelectorAll('[data-role]');
  if (!rows.length) return;
  const lastRow = rows[rows.length - 1];
  const _role = lastRow.dataset.role || '';
  // 最后一条是用户消息 → AI 还没回复，不渲染
  if (_role === 'user') return;
  // 渲染
  const { taskId, conversationId } = st._pendingFeedback;
  st._pendingFeedback = null;
  console.log('[feedback] AI 回复落位，渲染反馈条', taskId, '最后消息 role=', _role);
  _renderFeedbackBar(taskId, conversationId);
}"""

if old in c:
    c = c.replace(old, new, 1)
    print("改动: _tryFlushPendingFeedback 改用 [data-role]")
else:
    print("警告：锚点未匹配")
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发任务 → AI 回复先落位 → 反馈条出现在回复下方")
print("3. Console 应看到：[feedback] AI 回复落位，渲染反馈条 t_xxx 最后消息 role= assistant")
print("4. del fix_feedback_selector.py")