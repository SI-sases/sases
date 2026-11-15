# -*- coding: utf-8 -*-
"""定位 get_run 未定义 + 另一处假完成拦截"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = ["venv", "python312", "__pycache__", "build_portable",
        "_archive", "core.bak", "scripts/p1_0b_diagnose"]

# ============ 1. 搜"假完成拦截"真实位置 ============
print("=" * 70)
print("=== 1. 搜 '假完成拦截' 或 '无 file_patch' 真实位置 ===")
print("=" * 70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in SKIP):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "假完成拦截" in content or "无 file_patch" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if "假完成拦截" in line or "无 file_patch" in line:
                print(f"\n[FILE] {py.relative_to(ROOT)}:{i}")
                # 打印前后 15 行
                for j in range(max(0, i-15), min(len(lines), i+5)):
                    marker = ">>>" if j == i-1 else "   "
                    print(f"{marker} {j+1:4d} | {lines[j]}")

# ============ 2. executor_callback.py 里 get_run 的 import 情况 ============
print("\n" + "=" * 70)
print("=== 2. executor_callback.py 里 get_run 的 import ===")
print("=" * 70)
ec = ROOT / "core/services/swarm/executor_callback.py"
ec_lines = ec.read_text(encoding="utf-8").splitlines()
print("[顶部 25 行 import]")
for i in range(0, min(25, len(ec_lines))):
    line = ec_lines[i]
    if "import" in line or line.strip().startswith("from"):
        print(f"  {i+1:4d} | {line}")

print("\n[所有 get_run 使用位置]")
for i, line in enumerate(ec_lines, 1):
    if "get_run" in line and "def " not in line:
        print(f"  {i+1:4d} | {line.rstrip()[:150]}")

# ============ 3. handle_step_done 函数起始位置 ============
print("\n" + "=" * 70)
print("=== 3. handle_step_done 函数定义 + 前 20 行 ===")
print("=" * 70)
for i, line in enumerate(ec_lines, 1):
    if "async def handle_step_done" in line or "def handle_step_done" in line:
        print(f"\n[函数起始] 第 {i} 行")
        for j in range(i-1, min(i+20, len(ec_lines))):
            print(f"  {j+1:4d} | {ec_lines[j]}")
        break

# ============ 4. 第 314 行附近我插入的代码是否在正确作用域 ============
print("\n" + "=" * 70)
print("=== 4. 第 314-335 行（我插入的 get_run 调用所在位置）===")
print("=" * 70)
for i in range(313, min(335, len(ec_lines))):
    line = ec_lines[i]
    stripped = line.lstrip(' ')
    indent = len(line) - len(stripped)
    visual = '·' * indent + stripped
    print(f"  {i+1:4d} | {visual}")

# ============ 5. supervisor_service 是否有 get_run ============
print("\n" + "=" * 70)
print("=== 5. supervisor_service 是否导出 get_run ===")
print("=" * 70)
sv = ROOT / "core/services/supervisor_service.py"
if sv.exists():
    sv_content = sv.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(sv_content.splitlines(), 1):
        if "get_run" in line and ("import" in line or "def " in line or "=" in line):
            print(f"  {i:4d} | {line.rstrip()[:150]}")

print("\n=== 诊断完成 ===")
