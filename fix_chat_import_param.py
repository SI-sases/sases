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

# 1. 顶部 import
if 'param_bar.js' not in c:
    old = "import { "
    idx = c.find(old)
    if idx >= 0:
        # 在第一个 import 前加
        c = "import { initParamBar, getParamMaxSteps } from './param_bar.js';\n" + c
        changes += 1
        print("1. 加 import param_bar")
    else:
        print("警告：找不到 import")

# 2. openChatWindow 里调用 initParamBar
old2 = "  updateModeText();\n  updateInputPlaceholder();\n  updateIdentityButton(chatState);"
new2 = "  updateModeText();\n  updateInputPlaceholder();\n  updateIdentityButton(chatState);\n  try { initParamBar(); } catch (e) { console.warn('[chat] param_bar 初始化失败', e); }"

if 'initParamBar()' not in c and old2 in c:
    c = c.replace(old2, new2, 1)
    changes += 1
    print("2. openChatWindow 里加 initParamBar")
else:
    print("警告：openChatWindow 锚点未匹配或已存在")

# 3. sendMessage 里加 max_steps
old3 = """    const data = await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: text,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode
    });"""
new3 = """    let _maxSteps = null;
    try { _maxSteps = getParamMaxSteps(); } catch (e) {}
    const data = await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: text,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode,
      max_steps: _maxSteps
    });"""

if '_maxSteps' not in c and old3 in c:
    c = c.replace(old3, new3, 1)
    changes += 1
    print("3. sendMessage 里加 max_steps")
else:
    print("警告：sendMessage 锚点未匹配或已存在")

print(f"\n共 {changes} 处改动")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("下一步：")
print("1. 硬刷新浏览器 Ctrl+Shift+R")
print("2. 看胶囊是否显示 ⚙️ 8步")
print("3. 点击胶囊看是否弹出预设菜单")