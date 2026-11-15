# -*- coding: utf-8 -*-
"""诊断 2 件事：积分拦截为什么没生效 + L2 的 LLM import 正确路径"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# 1. credit_service.get_balance 的真实实现
# ============================================================
print("=" * 70)
print("[1] credit_service.get_balance 实现")
print("=" * 70)

cs = ROOT / "core/services/credit_service.py"
if cs.exists():
    content = cs.read_text(encoding="utf-8")
    lines = content.splitlines()
    # 找 get_balance 函数
    for i, line in enumerate(lines, 1):
        if "def get_balance" in line:
            print(f"\n[get_balance 定义 @ {i}]")
            for j in range(i - 1, min(i + 20, len(lines))):
                print(f"  {j+1:4d} | {lines[j]}")
            break
else:
    print("[MISS] credit_service.py 不存在")

# ============================================================
# 2. _numbered_prefix_matched 定义位置
# ============================================================
print("\n" + "=" * 70)
print("[2] _numbered_prefix_matched 定义")
print("=" * 70)

send = ROOT / "core/services/message/send.py"
send_content = send.read_text(encoding="utf-8")
send_lines = send_content.splitlines()
for i, line in enumerate(send_lines, 1):
    if "_numbered_prefix_matched" in line and ("=" in line or "def " in line):
        print(f"  {i:4d} | {line.rstrip()[:150]}")

# ============================================================
# 3. _force_swarm 定义位置
# ============================================================
print("\n" + "=" * 70)
print("[3] _force_swarm 定义")
print("=" * 70)
for i, line in enumerate(send_lines, 1):
    if "_force_swarm" in line and "=" in line:
        print(f"  {i:4d} | {line.rstrip()[:150]}")

# ============================================================
# 4. L2 的 call_llm 正确 import 路径
# ============================================================
print("\n" + "=" * 70)
print("[4] call_llm 真实定义位置（找 commander 或类似）")
print("=" * 70)

# 已知 commander.py 会调 LLM
commander = ROOT / "core/services/swarm/commander.py"
if commander.exists():
    cmd_content = commander.read_text(encoding="utf-8")
    cmd_lines = cmd_content.splitlines()
    print("\n[commander.py 的 import + call_llm 用法]")
    for i, line in enumerate(cmd_lines, 1):
        if ("import" in line and ("openai" in line or "llm" in line.lower())) \
           or ("call_llm" in line and "def " not in line):
            print(f"  {i:4d} | {line.rstrip()[:150]}")

# 全项目找 call_llm 定义
print("\n[全项目 def call_llm / async def call_llm]")
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                    "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "def call_llm" in content or "async def call_llm" in content:
        for i, line in enumerate(content.splitlines(), 1):
            if "def call_llm" in line or "async def call_llm" in line:
                print(f"  {py.relative_to(ROOT)}:{i}: {line.strip()[:120]}")

# ============================================================
# 5. reviewer_deep.py 当前的 import 语句
# ============================================================
print("\n" + "=" * 70)
print("[5] reviewer_deep.py 当前的 import")
print("=" * 70)
rd = ROOT / "core/services/swarm/reviewer_deep.py"
if rd.exists():
    for i, line in enumerate(rd.read_text(encoding="utf-8").splitlines(), 1):
        if "import" in line and "llm_client" in line:
            print(f"  {i:4d} | {line.rstrip()}")

print("\n=== 诊断完成 ===")
