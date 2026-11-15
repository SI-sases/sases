# -*- coding: utf-8 -*-
"""P1-0 诊断 2：Healer 深度 + REPLAN prompt + script_fallback 触发逻辑"""
from pathlib import Path
import subprocess
import re

ROOT = Path(__file__).resolve().parent.parent

# ============ 1. healer.py 当前内容 ============
print("=== 1. healer.py 当前内容（140 字节）===")
h = ROOT / "core/services/swarm/healer.py"
print(h.read_text(encoding="utf-8"))

# ============ 2. healer.py 的 git 历史（找回完整版的希望） ============
print("\n=== 2. healer.py 的 git 历史 ===")
try:
    r = subprocess.run(
        ["git", "log", "--all", "--oneline", "--follow", "--",
         "core/services/swarm/healer.py"],
        capture_output=True, text=True, cwd=str(ROOT),
        encoding="utf-8", errors="ignore"
    )
    print(r.stdout or "[无 git 历史]")
except Exception as e:
    print(f"[git 执行失败] {e}")

# ============ 3. REPLAN_SYSTEM_PROMPT 完整内容 ============
print("\n=== 3. REPLAN_SYSTEM_PROMPT 完整内容 ===")
pp = ROOT / "core/services/swarm/prompts.py"
content = pp.read_text(encoding="utf-8")
m = re.search(r'REPLAN_SYSTEM_PROMPT\s*=\s*"""(.*?)"""', content, re.DOTALL)
if m:
    print(m.group(1))
else:
    print("[未找到 REPLAN_SYSTEM_PROMPT]")

# ============ 4. SCRIPT_FALLBACK_PROMPT 前 2000 字 ============
print("\n=== 4. SCRIPT_FALLBACK_PROMPT（前 2000 字）===")
m = re.search(r'SCRIPT_FALLBACK_PROMPT\s*=\s*"""(.*?)"""', content, re.DOTALL)
if m:
    print(m.group(1)[:2000])
else:
    print("[未找到 SCRIPT_FALLBACK_PROMPT]")

# ============ 5. executor_callback.py 435-480 行 ============
print("\n=== 5. executor_callback.py 435-480 行 ===")
ec = ROOT / "core/services/swarm/executor_callback.py"
lines = ec.read_text(encoding="utf-8").splitlines()
for i in range(434, min(480, len(lines))):
    print(f"{i+1:4d} | {lines[i]}")

# ============ 6. 是否有同类错误计数 / _heal_count ============
print("\n=== 6. executor_callback.py 里的计数/熔断变量 ===")
for i, line in enumerate(lines, 1):
    low = line.lower()
    if ("heal" in low or "_same_error" in low
        or "_heal_count" in low or "attempt" in low
        or "_script_fallback" in low):
        print(f"{i:4d} | {line.rstrip()}")

# ============ 7. replan 调用点在哪（谁触发重拆） ============
print("\n=== 7. replan_failed_steps 调用点 ===")
for i, line in enumerate(lines, 1):
    if "replan" in line.lower():
        print(f"{i:4d} | {line.rstrip()}")

print("\n=== 诊断完成 ===")
