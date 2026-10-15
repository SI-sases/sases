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

# ===== 改动 1：轮询触发延迟 2 秒（等 AI 回复） =====
old1 = """      // v0.39.0: 任务完成 → 显示反馈条（不依赖 WS）
      setTimeout(() => {
        try {
          _renderFeedbackBar(taskId, (window.chatState && window.chatState.conversationId) || null);
        } catch (e) { console.warn('[feedback] 轮询触发失败', e); }
      }, 300);"""
new1 = """      // v0.39.1: 任务完成 → 延迟 2 秒显示反馈条（等 AI 回复先落位）
      setTimeout(() => {
        try {
          _renderFeedbackBar(taskId, (window.chatState && window.chatState.conversationId) || null);
        } catch (e) { console.warn('[feedback] 轮询触发失败', e); }
      }, 2000);"""

if old1 in c:
    c = c.replace(old1, new1, 1)
    changes += 1
    print("改动 1: 轮询触发延迟 2 秒")
else:
    print("警告：改动 1 锚点未匹配")

# ===== 改动 2：点击后加诊断日志 + 3 秒移除 =====
old2 = """    btn.onclick = async () => {
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
    };"""

new2 = """    btn.onclick = async () => {
      const rating = btn.dataset.rating;
      console.log('[feedback] 点击', rating, 'task_id=', taskId);
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
        console.log('[feedback] 提交返回', resp.status);
        bar.innerHTML = '<span class="feedback-done">已记录，谢谢 🙏</span>';
        setTimeout(() => { try { bar.remove(); } catch(e) {} }, 3000);
      } catch (e) {
        console.warn('[feedback] 提交失败', e);
        bar.innerHTML = '<span style="color:#ff3b30;">提交失败，请重试</span>';
      }
    };"""

if old2 in c:
    c = c.replace(old2, new2, 1)
    changes += 1
    print("改动 2: 点击加日志 + 3 秒移除")
else:
    print("警告：改动 2 锚点未匹配")

print(f"\n共 {changes} 处改动")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发任务 → 完成后 2 秒反馈条出现（在 AI 回复下方）")
print("3. 点 👎 → 3 秒后消失，显示'已记录'")
print("4. 如果还不对：F12 Console 看 [feedback] 日志")
print("5. del fix_feedback_v2.py")