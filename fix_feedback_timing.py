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

# ============ 改动 1：_pollTaskStatus 完成分支改挂起 ============
old1 = """    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
      // v0.39.0: 任务完成 → 显示反馈条（不依赖 WS）
      setTimeout(() => {
        try {
          _renderFeedbackBar(taskId, (window.chatState && window.chatState.conversationId) || null);
        } catch (e) { console.warn('[feedback] 轮询触发失败', e); }
      }, 2000);
    }"""

new1 = """    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
      // v0.39.3: 挂起反馈条，等 AI 回复落位后再显示
      if (window.chatState) {
        window.chatState._pendingFeedback = {
          taskId: taskId,
          conversationId: window.chatState.conversationId || null,
        };
      }
      // 立即尝试一次（如果 AI 回复已经到了）
      setTimeout(() => { try { _tryFlushPendingFeedback(); } catch (e) {} }, 500);
      // 兜底：8 秒内 AI 回复未到，也强行显示
      setTimeout(() => {
        const st = window.chatState;
        if (st && st._pendingFeedback && st._pendingFeedback.taskId === taskId) {
          console.log('[feedback] 兜底渲染（AI 回复超时未到达）');
          try { _tryFlushPendingFeedback(); } catch (e) {}
        }
      }, 8000);
    }"""

if old1 in c:
    c = c.replace(old1, new1, 1)
    changes += 1
    print("改动 1: _pollTaskStatus 改挂起机制")
else:
    print("警告：改动 1 锚点未匹配")

# ============ 改动 2：加 _tryFlushPendingFeedback 函数 ============
old2 = "function _renderFeedbackBar(taskId, conversationId) {"
new2 = """function _tryFlushPendingFeedback() {
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
}

function _renderFeedbackBar(taskId, conversationId) {"""

if old2 in c and '_tryFlushPendingFeedback' not in c:
    c = c.replace(old2, new2, 1)
    changes += 1
    print("改动 2: 加 _tryFlushPendingFeedback")
else:
    print("警告：改动 2 锚点未匹配")

# ============ 改动 3：initChat 里加 MutationObserver ============
old3 = """  if (messagesContainer) {
    messagesContainer.addEventListener('scroll', handleScroll);
  }"""

new3 = """  if (messagesContainer) {
    messagesContainer.addEventListener('scroll', handleScroll);
    // v0.39.3: 监听消息区变化，自动 flush 挂起的反馈条
    if (!messagesContainer._sasesFeedbackObserver) {
      const _obs = new MutationObserver(() => {
        try { _tryFlushPendingFeedback(); } catch (e) {}
      });
      _obs.observe(messagesContainer, { childList: true });
      messagesContainer._sasesFeedbackObserver = _obs;
    }
  }"""

if old3 in c and '_sasesFeedbackObserver' not in c:
    c = c.replace(old3, new3, 1)
    changes += 1
    print("改动 3: initChat 加 MutationObserver")
else:
    print("警告：改动 3 锚点未匹配")

print(f"\n共 {changes} 处改动")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发任务 → AI 回复先落位 → 反馈条在其下方出现")
print("3. 长文回复也不会被顶开")
print("4. del fix_feedback_timing.py")