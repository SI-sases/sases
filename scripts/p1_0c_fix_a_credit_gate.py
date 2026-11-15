# -*- coding: utf-8 -*-
"""修复 A：在 #4 派单前检查积分，不足直接拦截"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEND = ROOT / "core/services/message/send.py"

if not SEND.exists():
    print("[ERROR] send.py 不存在")
    exit(1)

content = SEND.read_text(encoding="utf-8")

# 标记：已在入口处加了积分检查
if "# [P1-0c] #4 积分拦截" in content:
    print("[SKIP] 积分拦截已存在")
    exit(0)

# 找 #4 派单入口的锚点
# 通过前面诊断知道 send.py 有 _cs0.get_balance 在某处，但不知道 #4 分支在哪
# 我们找 "is_task" 或 "dispatch" 或 "swarm" 附近

# 策略：找 send_message 函数里的 #4 检测点
# 常见写法：
#   if content.startswith("#4:") or similar
# 或者
#   is_task = True

# 先打印候选锚点，让用户看
print("=" * 60)
print("[候选锚点扫描] send.py 里所有 #4 / dispatch / is_task 出现处")
print("=" * 60)

lines = content.splitlines()
candidates = []
for i, line in enumerate(lines, 1):
    if any(k in line for k in ['#4', 'dispatch', 'is_task', 'plan_task',
                                'task_engine', 'swarm_service']):
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            print(f"  {i:4d} | {line.rstrip()[:150]}")
            candidates.append((i, line))

if not candidates:
    print("[WARN] 没找到候选锚点，可能需要手工定位")
    exit(1)

print(f"\n[共 {len(candidates)} 个候选]")
print("\n请把上面的输出贴回来，我根据真实锚点给精确的注入代码。")
