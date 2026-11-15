# -*- coding: utf-8 -*-
"""修复 A：在 if is_task: 之后插入积分拦截（精确到行号）"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent.parent
SEND = ROOT / "core/services/message/send.py"

content = SEND.read_text(encoding="utf-8")

# 已修复则跳过
if "# [P1-0c-a] 积分拦截" in content:
    print("[SKIP] 积分拦截已存在")
    sys.exit(0)

# 找 if is_task: 的真实行
lines = content.splitlines()
if_line_idx = None
for i, line in enumerate(lines):
    stripped = line.strip()
    indent = len(line) - len(line.lstrip())
    if stripped == "if is_task:" and indent == 12:
        # 检查下一行是否是 friend_gate（确认是派单入口，不是其他 if is_task）
        if i + 1 < len(lines) and "friend_gate" in lines[i + 1]:
            if_line_idx = i
            print(f"[FOUND] if is_task: 在第 {i+1} 行，下一行是 friend_gate")
            break

if if_line_idx is None:
    print("[ERROR] 找不到派单入口 if is_task: 或下一行不是 friend_gate")
    # 打印候选，方便排查
    for i, line in enumerate(lines):
        if "if is_task" in line:
            print(f"  行 {i+1}: {line!r}")
            if i + 1 < len(lines):
                print(f"    下一行: {lines[i+1]!r}")
    sys.exit(1)

# 构建插入代码（缩进 16 空格，因为 if is_task: 内部）
insert_code = '''
                # [P1-0c-a] 积分拦截：派单前检查，避免消耗 API 后才报积分不足
                try:
                    from .. import credit_service as _cs_gate
                    _need_credit_gate = (
                        _force_swarm
                        or _numbered_prefix_matched
                        or content.strip().startswith(('#1', '#2', '#3', '#4'))
                    )
                    if _need_credit_gate:
                        _bal_gate = _cs_gate.get_balance(user_id)
                        if _bal_gate < 5:
                            print(f"[P1-0c-a] 积分不足拦截: balance={_bal_gate} < 5")
                            _gate_msg = f"\\u26a0\\ufe0f 积分不足（当前 {_bal_gate}，至少需要 5 积分才能执行指令）。请先充值或等待空投后再试。"
                            with db_cursor(commit=True) as _cur_gate:
                                _cur_gate.execute(
                                    "INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) VALUES (?, 'assistant', ?, 'standard', '[]')",
                                    (conversation_id, _gate_msg)
                                )
                                _cur_gate.execute(
                                    "UPDATE conversations SET updated_at=? WHERE id=?",
                                    (datetime.now().isoformat(), conversation_id)
                                )
                            return {
                                'conversation_id': conversation_id,
                                'user_message': content,
                                'assistant_reply': _gate_msg,
                                'agent_id': agent_id,
                                'sender_agent_id': sender_agent_id,
                                'mode': mode,
                                'credit_gate': True
                            }
                except Exception as _e_gate:
                    print(f"[P1-0c-a] 积分拦截异常（已放行）: {type(_e_gate).__name__}: {_e_gate}")
'''

# 按行插入（在 if_line_idx 之后）
insert_lines = insert_code.split('\n')
# 去掉开头的空行，保留第一个实际代码行
if insert_lines and insert_lines[0] == '':
    insert_lines = insert_lines[1:]

lines[if_line_idx + 1:if_line_idx + 1] = insert_lines

new_content = '\n'.join(lines)

# 语法验证（写入前）
try:
    ast.parse(new_content)
except SyntaxError as e:
    print(f"[FAIL] 插入后语法错误: {e}")
    print(f"  位置: line {e.lineno}")
    # 打印插入位置附近的代码
    for j in range(max(0, e.lineno - 5), min(len(lines), e.lineno + 3)):
        print(f"  {j+1:4d} | {lines[j]}")
    sys.exit(1)

# 写入
SEND.write_text(new_content, encoding="utf-8")
print(f"[OK] 积分拦截已插入，send.py 从 {len(content)} 增长到 {len(new_content)} 字符")
print(f"[OK] 插入位置：第 {if_line_idx + 1} 行之后（if is_task: 之后、friend_gate 之前）")

# 打印插入后附近 20 行，供确认
print("\n[插入后附近 25 行]")
for j in range(max(0, if_line_idx - 2), min(len(lines), if_line_idx + 30)):
    marker = ">>>" if if_line_idx <= j <= if_line_idx + 28 else "   "
    print(f"{marker} {j+1:4d} | {lines[j]}")

print("\n=== 修复 A 完成，重启服务后生效 ===")
