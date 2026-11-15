# -*- coding: utf-8 -*-
"""最终修复：_call_llm 签名 + _TERMINAL 加 insufficient_credits"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# A. reviewer_deep.py: call_llm 改成 positional 参数
# ============================================================
print("=" * 60)
print("A. reviewer_deep.py 的 call_llm 调用")
print("=" * 60)

RD = ROOT / "core/services/swarm/reviewer_deep.py"
rd = RD.read_text(encoding="utf-8")

old_call = """        resp = await call_llm(
            system_prompt=system_prompt,
            user=f"触发原因：{trigger_reason}\\n请输出测试步骤 JSON。",
            max_tokens=800,
            temperature=0.1,
        )"""

new_call = """        resp = await call_llm(
            f"触发原因：{trigger_reason}\\n请输出测试步骤 JSON。",
            system_prompt,
            max_tokens=800,
        )"""

if "user=f\"触发原因" in rd:
    rd = rd.replace(old_call, new_call, 1)
    RD.write_text(rd, encoding="utf-8")
    print("[OK] call_llm 已改为 positional 参数")
elif "resp = await call_llm(\n            f\"触发原因" in rd:
    print("[SKIP] 已经是 positional 格式")
else:
    print("[ERROR] 找不到 old_call，打印当前调用")
    for i, line in enumerate(rd.splitlines(), 1):
        if "call_llm" in line:
            for j in range(max(0, i-1), min(len(rd.splitlines()), i+8)):
                print(f"  {j+1:4d} | {rd.splitlines()[j]}")
    sys.exit(1)

# ============================================================
# B. runs.py: _TERMINAL 加 insufficient_credits
# ============================================================
print("\n" + "=" * 60)
print("B. runs.py 的 _TERMINAL")
print("=" * 60)

RUNS = ROOT / "core/services/supervisor/runs.py"
runs = RUNS.read_text(encoding="utf-8")

if "'insufficient_credits'" in runs:
    print("[SKIP] insufficient_credits 已在 _TERMINAL")
else:
    old_terminal = """    _TERMINAL = ('completed', 'failed', 'cancelled', 'rejected', 'plan_failed',
                 'no_progress', 'timeout', 'interrupted', 'error', 'waiting_user')"""
    new_terminal = """    _TERMINAL = ('completed', 'failed', 'cancelled', 'rejected', 'plan_failed',
                 'no_progress', 'timeout', 'interrupted', 'error', 'waiting_user',
                 'insufficient_credits')"""
    if old_terminal in runs:
        runs = runs.replace(old_terminal, new_terminal, 1)
        RUNS.write_text(runs, encoding="utf-8")
        print("[OK] insufficient_credits 已加入 _TERMINAL")
    else:
        print("[ERROR] 找不到 _TERMINAL 原文")
        sys.exit(1)

# ============================================================
# C. 语法验证
# ============================================================
print("\n" + "=" * 60)
print("C. 语法验证")
print("=" * 60)
for path in [RD, RUNS]:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        print(f"  [OK] {path.name}")
    except SyntaxError as e:
        print(f"  [FAIL] {path.name}: {e}")
        sys.exit(1)

print("\n=== 修复完成 ===")
