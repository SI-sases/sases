import os
import shutil
from datetime import datetime

backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

# ============ 1. chat.js ============
print("\n[1/2] 修改 chat.js")
FP = "static/modules/chat.js"
backup = os.path.join(backup_dir, f"static__modules__chat.js.{ts}.bak")
shutil.copy2(FP, backup)
print(f"  备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

# 1a. 加 _renderFeedbackBar 函数（放在 _hideStopBtn 之后）
old_anchor = "async function _stopCurrentTask() {"
new_funcs = '''function _renderFeedbackBar(taskId, conversationId) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  // 同任务已有反馈条则不重复
  if (container.querySelector('.feedback-bar[data-task-id="' + taskId + '"]')) return;
  const bar = document.createElement('div');
  bar.className = 'feedback-bar';
  bar.dataset.taskId = taskId;
  bar.innerHTML = '<span class="feedback-label">这次结果满意吗？</span>'
    + '<button class="feedback-btn" data-rating="up">👍</button>'
    + '<button class="feedback-btn" data-rating="down">👎</button>'
    + '<button class="feedback-btn" data-rating="neutral">🤷</button>';
  bar.querySelectorAll('.feedback-btn').forEach(btn => {
    btn.onclick = async () => {
      const rating = btn.dataset.rating;
      try {
        const token = localStorage.getItem('sases_token');
        await fetch('/feedback/submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ task_id: taskId, rating, conversation_id: conversationId })
        });
        bar.innerHTML = '<span class="feedback-done">已记录，谢谢 🙏</span>';
        setTimeout(() => bar.remove(), 2000);
      } catch (e) {
        console.warn('[feedback] 提交失败', e);
      }
    };
  });
  container.appendChild(bar);
  container.scrollTop = container.scrollHeight;
}

async function _stopCurrentTask() {'''

if '_renderFeedbackBar' not in c and old_anchor in c:
    c = c.replace(old_anchor, new_funcs, 1)
    print("  + 加 _renderFeedbackBar")
else:
    print("  警告：_renderFeedbackBar 已存在或锚点未匹配")

# 1b. 在 [SUMMARY]: 分支里调用
old2 = """  if (_display.startsWith('[SUMMARY]:')) {
    _display = _display.slice(10);
    try { _hideStopBtn(); } catch (e) {}
  }"""
new2 = """  if (_display.startsWith('[SUMMARY]:')) {
    _display = _display.slice(10);
    const _fbTid = (window.chatState && window.chatState.currentTaskId) || null;
    try { _hideStopBtn(); } catch (e) {}
    if (_fbTid) {
      setTimeout(() => {
        try { _renderFeedbackBar(_fbTid, window.chatState && window.chatState.conversationId); } catch (e) {}
      }, 300);
    }
  }"""

if '_fbTid' not in c and old2 in c:
    c = c.replace(old2, new2, 1)
    print("  + [SUMMARY]: 分支触发反馈条")
else:
    print("  警告：SUMMARY 锚点未匹配或已改过")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"  已写入，大小 {os.path.getsize(FP)} 字节")

# ============ 2. chat.css ============
print("\n[2/2] 修改 chat.css")
FP = "static/css/chat.css"
backup = os.path.join(backup_dir, f"static__css__chat.css.{ts}.bak")
shutil.copy2(FP, backup)
print(f"  备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    css = f.read()

css_block = '''
/* ===== 反馈条（v0.39.0） ===== */
.feedback-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 6px 12px;
  background: var(--bg-input, #f9f9f9);
  border-radius: var(--radius-md, 8px);
  font-size: 12px;
  color: var(--text-secondary, #666);
}
.feedback-label {
  margin-right: auto;
}
.feedback-btn {
  background: none;
  border: 0.5px solid var(--border-base, #ddd);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.feedback-btn:hover {
  background: var(--bg-hover, #eaeaea);
}
.feedback-done {
  color: #34c759;
  font-size: 12px;
}
'''

if '.feedback-bar' not in css:
    css = css + css_block
    print("  + 加 .feedback-bar 样式")
else:
    print("  已存在，跳过")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(css)
print(f"  已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！下一步：")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发 swarm 任务 → 收到 SUMMARY 后出现 👍👎🤷")
print("3. 点 👎 → 显示'已记录'→ 2 秒后消失")
print("4. del fix_feedback_ui.py")