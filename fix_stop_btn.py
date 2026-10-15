import os
import shutil
from datetime import datetime

backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def _backup(fp):
    b = os.path.join(backup_dir, fp.replace("/", "__").replace("\\", "__") + f".{ts}.bak")
    shutil.copy2(fp, b)
    print(f"  备份: {b}")
    return b

# ============ 1. index.html 加 stop-btn ============
print("\n[1/2] index.html")
FP = "static/index.html"
_backup(FP)
with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

old = '<button id="send-btn" class="send-btn" style="display:none;">发送</button>'
new = '<button id="send-btn" class="send-btn" style="display:none;">发送</button>\n            <button id="stop-btn" class="send-btn" style="display:none;background:#ff3b30;">⏹</button>'

if old in c and 'stop-btn' not in c:
    c = c.replace(old, new, 1)
    print("  + 加 stop-btn")
else:
    print("  已存在或锚点未匹配")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)

# ============ 2. chat.js 加逻辑 ============
print("\n[2/2] chat.js")
FP = "static/modules/chat.js"
_backup(FP)
with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

# 2a. 加显示/隐藏函数
helpers = '''
// ===== 停止按钮（v0.38.0）=====
function _showStopBtn(taskId) {
  if (window.chatState) window.chatState.currentTaskId = taskId;
  const sendBtn = document.getElementById('send-btn');
  const stopBtn = document.getElementById('stop-btn');
  if (sendBtn) sendBtn.style.display = 'none';
  if (stopBtn) stopBtn.style.display = 'block';
  if (window.chatState) {
    if (window.chatState._stopTimer) clearTimeout(window.chatState._stopTimer);
    window.chatState._stopTimer = setTimeout(() => _hideStopBtn(), 30000);
  }
}

function _hideStopBtn() {
  if (window.chatState) {
    window.chatState.currentTaskId = null;
    if (window.chatState._stopTimer) {
      clearTimeout(window.chatState._stopTimer);
      window.chatState._stopTimer = null;
    }
  }
  const stopBtn = document.getElementById('stop-btn');
  if (stopBtn) stopBtn.style.display = 'none';
  if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
}

async function _stopCurrentTask() {
  const tid = window.chatState && window.chatState.currentTaskId;
  _hideStopBtn();
  if (!tid) return;
  try {
    const token = localStorage.getItem('sases_token');
    await fetch('/swarm/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ task_id: tid })
    });
  } catch (e) { console.warn('[stop] 取消失败', e); }
}

window._showStopBtn = _showStopBtn;
window._hideStopBtn = _hideStopBtn;
window._stopCurrentTask = _stopCurrentTask;

'''

if '_showStopBtn' not in c:
    anchor = "async function sendMessage() {"
    if anchor in c:
        c = c.replace(anchor, helpers + anchor, 1)
        print("  + 加 _showStopBtn/_hideStopBtn/_stopCurrentTask")
    else:
        print("  警告：找不到 sendMessage 锚点")

# 2b. sendMessage 里调用
old2 = """    else if (data.swarm && data.task_id) {
      showSwarmActionButtons(data.task_id, text, data.swarm_status);
    }"""
new2 = """    else if (data.swarm && data.task_id) {
      showSwarmActionButtons(data.task_id, text, data.swarm_status);
      _showStopBtn(data.task_id);
    }"""
if old2 in c and '_showStopBtn(data.task_id)' not in c:
    c = c.replace(old2, new2, 1)
    print("  + sendMessage 里调用 _showStopBtn")

# 2c. openChatWindow 里绑定 click
old3 = "  updateSendButtonVisibility();\n  hideQuoteBar();\n  closeChatPlusPanel();"
new3 = """  updateSendButtonVisibility();
  hideQuoteBar();
  closeChatPlusPanel();
  const _stopBtn = document.getElementById('stop-btn');
  if (_stopBtn && !_stopBtn._sasesStopBound) {
    _stopBtn._sasesStopBound = true;
    _stopBtn.onclick = _stopCurrentTask;
  }
  _hideStopBtn();"""
if 'updateSendButtonVisibility();\n  hideQuoteBar();' in c and '_sasesStopBound' not in c:
    c = c.replace(old3, new3, 1)
    print("  + openChatWindow 里绑定 stop-btn click")

# 2d. closeChatWindow 里重置
old4 = "  hideQuoteBar();\n  closeChatPlusPanel();\n}"
if 'hideQuoteBar();\n  closeChatPlusPanel();\n}' in c and '// closeChatWindow' not in c:
    # 这个位置可能匹配到多个地方，只改最靠后的
    idx = c.rfind("  hideQuoteBar();\n  closeChatPlusPanel();\n}")
    if idx > 0:
        c = c[:idx] + "  hideQuoteBar();\n  closeChatPlusPanel();\n  _hideStopBtn();\n}" + c[idx+len("  hideQuoteBar();\n  closeChatPlusPanel();\n}"):]
        print("  + closeChatWindow 里重置")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"  已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 发一条 swarm 任务，发送按钮应变为 ⏹")
print("3. 点 ⏹ 应触发取消")
print("4. del fix_stop_btn.py")