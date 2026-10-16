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

# 替换整个 _renderFeedbackBar 函数
old = """function _renderFeedbackBar(taskId, conversationId) {
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
      if (bar._autoRemoveTimer) { clearTimeout(bar._autoRemoveTimer); bar._autoRemoveTimer = null; }
      console.log('[feedback] 点击', rating, 'task_id=', taskId);
      // 立即禁用所有按钮，避免重复点击
      bar.querySelectorAll('.feedback-btn').forEach(b => { b.disabled = true; });
      try {
        const token = localStorage.getItem('sases_token');
        const resp = await fetch('/feedback/submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ task_id: taskId, rating, conversation_id: conversationId })
        });
        console.log('[feedback] 提交返回', resp.status, '父节点存在:', !!bar.parentNode);
        // 替换为"已记录"
        if (bar.parentNode) {
          bar.innerHTML = '<span class="feedback-done">已记录，谢谢 🙏</span>';
          console.log('[feedback] innerHTML 已替换，内容:', bar.innerHTML);
        }
        // 3 秒后移除（用 parentNode 检查）
        setTimeout(() => {
          try {
            if (bar.parentNode) bar.parentNode.removeChild(bar);
            console.log('[feedback] bar 已移除');
          } catch (e) { console.warn('[feedback] remove 失败', e); }
        }, 3000);
      } catch (e) {
        console.warn('[feedback] 提交失败', e);
        bar.innerHTML = '<span style="color:#ff3b30;">提交失败，请重试</span>';
      }
    };
  });
  container.appendChild(bar);
  container.scrollTop = container.scrollHeight;
  // v0.39.2: 30 秒未操作自动移除
  bar._autoRemoveTimer = setTimeout(() => {
    try {
      if (bar.parentNode) bar.parentNode.removeChild(bar);
      console.log('[feedback] 30 秒未操作，自动移除');
    } catch (e) {}
  }, 30000);
}"""

new = """function _renderFeedbackBar(taskId, conversationId) {
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

  const _submit = async (rating, reason_tag, reason_text) => {
    bar.querySelectorAll('.feedback-btn').forEach(b => { b.disabled = true; });
    try {
      const token = localStorage.getItem('sases_token');
      const _body = { task_id: taskId, rating, conversation_id: conversationId };
      if (reason_tag) _body.reason_tag = reason_tag;
      if (reason_text) _body.reason_text = reason_text;
      const resp = await fetch('/feedback/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(_body)
      });
      console.log('[feedback] 提交返回', resp.status);
      if (bar.parentNode) {
        bar.innerHTML = '<span class="feedback-done">已记录，谢谢 🙏</span>';
      }
      setTimeout(() => {
        try { if (bar.parentNode) bar.parentNode.removeChild(bar); } catch (e) {}
      }, 3000);
    } catch (e) {
      console.warn('[feedback] 提交失败', e);
      bar.innerHTML = '<span style="color:#ff3b30;">提交失败，请重试</span>';
    }
  };

  const _showReasonPanel = () => {
    // 用二级小条替换主条内容
    bar.innerHTML = '<span class="feedback-label">哪里不满意？</span>'
      + '<button class="feedback-reason-btn" data-rt="understood_wrong">理解错了</button>'
      + '<button class="feedback-reason-btn" data-rt="decomposed_wrong">拆解乱了</button>'
      + '<button class="feedback-reason-btn" data-rt="exec_failed">执行失败</button>'
      + '<button class="feedback-reason-btn" data-rt="output_poor">结果不好看</button>'
      + '<button class="feedback-reason-btn feedback-skip-btn" data-rt="">跳过</button>';
    bar.querySelectorAll('.feedback-reason-btn').forEach(rb => {
      rb.onclick = () => {
        const rt = rb.dataset.rt || null;
        _submit('down', rt, '');
      };
    });
  };

  bar.querySelectorAll('.feedback-btn').forEach(btn => {
    btn.onclick = () => {
      const rating = btn.dataset.rating;
      if (bar._autoRemoveTimer) { clearTimeout(bar._autoRemoveTimer); bar._autoRemoveTimer = null; }
      console.log('[feedback] 点击', rating, 'task_id=', taskId);
      if (rating === 'down') {
        // 弹归因面板
        _showReasonPanel();
      } else {
        _submit(rating, null, '');
      }
    };
  });

  container.appendChild(bar);
  container.scrollTop = container.scrollHeight;
  bar._autoRemoveTimer = setTimeout(() => {
    try {
      if (bar.parentNode) bar.parentNode.removeChild(bar);
      console.log('[feedback] 30 秒未操作，自动移除');
    } catch (e) {}
  }, 30000);
}"""

if old in c:
    c = c.replace(old, new, 1)
    print("  + 替换 _renderFeedbackBar（支持归因面板）")
else:
    print("  警告：_renderFeedbackBar 锚点未匹配")
    raise SystemExit(1)

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

css_block = """
/* 反馈归因按钮（v0.39.5） */
.feedback-reason-btn {
  background: none;
  border: 0.5px solid var(--border-base, #ddd);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-secondary, #666);
}
.feedback-reason-btn:hover {
  background: var(--bg-hover, #eaeaea);
}
.feedback-skip-btn {
  margin-left: auto;
  color: var(--text-muted, #999);
}
"""

if '.feedback-reason-btn' not in css:
    css = css + css_block
    print("  + 加 .feedback-reason-btn 样式")
else:
    print("  已存在，跳过")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(css)
print(f"  已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发任务 → 反馈条出现")
print("3. 点 👎 → 弹出 5 个按钮：[理解错了] [拆解乱了] [执行失败] [结果不好看] [跳过]")
print("4. 点任一 → 提交 → 显示'已记录'")
print("5. del fix_feedback_reason.py")