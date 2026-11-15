# -*- coding: utf-8 -*-
"""#5 回复落库 v2：行号定位 + 局部锚点"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
import ast
import shutil
import datetime

ROOT = Path(__file__).resolve().parent.parent
SEND = ROOT / "core/services/message/send.py"
content = SEND.read_text(encoding="utf-8")

if "# [P1-1c] 定时任务回复落库" in content:
    print("[SKIP] 已修复")
    sys.exit(0)

lines = content.splitlines()

# 1. 找 _reply = "❌ 格式错误 这一行（唯一锚点）
anchor_idx = None
for i, line in enumerate(lines):
    if '_reply = "' in line and "格式错误" in line:
        anchor_idx = i
        print(f"[FOUND] _reply 错误提示行在第 {i+1} 行")
        break

if anchor_idx is None:
    print("[ERROR] 找不到 _reply = \"...格式错误...\"")
    sys.exit(1)

# 2. 从这行往下找 return {
return_idx = None
for j in range(anchor_idx, min(anchor_idx + 20, len(lines))):
    if lines[j].strip() == "return {":
        return_idx = j
        print(f"[FOUND] return {{ 在第 {j+1} 行")
        break

if return_idx is None:
    print("[ERROR] 从 _reply 行往下 20 行内没找到 return {")
    print("=== 当前代码 ===")
    for j in range(anchor_idx, min(anchor_idx + 25, len(lines))):
        print(f"  {j+1:4d} | {lines[j]}")
    sys.exit(1)

# 3. 构造插入代码（8 空格缩进，和 return 同层）
insert_block = [
    "",
    "        # [P1-1c] 定时任务回复落库（修复刷新后消失）",
    "        try:",
    "            with db_cursor(commit=True) as _cur5r:",
    "                _cur5r.execute(",
    '                    "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, \'assistant\', ?, ?, \'standard\', \'[]\')",',
    "                    (conversation_id, _reply, sender_agent_id or agent_id)",
    "                )",
    "        except Exception as _e5r:",
    '            print(f"[#5] 回复落库失败: {_e5r}")',
    "",
]

# 4. 在 return_idx 之前插入
new_lines = lines[:return_idx] + insert_block + lines[return_idx:]
new_content = "\n".join(new_lines)

# 5. 备份
bak = SEND.with_suffix(f".py.bak_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(SEND, bak)
print(f"[OK] 已备份: {bak.name}")

# 6. 语法验证（写入前）
try:
    ast.parse(new_content)
    print("[OK] 插入后语法通过")
except SyntaxError as e:
    print(f"[FAIL] 语法错: {e} line {e.lineno}")
    print("=== 插入位置附近 ===")
    for k in range(max(0, e.lineno - 5), min(len(new_lines), e.lineno + 3)):
        print(f"  {k+1:4d} | {new_lines[k]}")
    sys.exit(1)

# 7. 写入
SEND.write_text(new_content, encoding="utf-8")
print(f"[OK] send.py 已更新: {SEND.stat().st_size} bytes")

# 8. 打印结果
print("\n=== 插入后 140-170 行 ===")
for k in range(139, min(170, len(new_lines))):
    marker = ">>>" if return_idx <= k < return_idx + len(insert_block) else "   "
    print(f"{marker} {k+1:4d} | {new_lines[k]}")

print("\n=== 完成，重启服务后生效 ===")
print("测试：浏览器发 '#5: 每天5点 整理收件箱未读邮件'，刷新后消息应该还在")
