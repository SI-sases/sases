# -*- coding: utf-8 -*-
"""第 2 轮诊断：打印完整函数体，不再只搜关键词"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

def print_lines(path, start, end, label=""):
    """打印文件指定行范围"""
    print(f"\n{'='*70}")
    print(f"=== {label} ({path}:{start}-{end}) ===")
    print('='*70)
    full = ROOT / path
    if not full.exists():
        print(f"  [文件不存在] {path}")
        return
    lines = full.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i in range(start - 1, min(end, len(lines))):
        print(f"  {i+1:4d} | {lines[i]}")

# ============ 1. file_patch 的 _mode_create 完整代码 ============
# 诊断发现第 316-355 行是 create 逻辑，打印 310-380
print_lines("harness_modules/file_patch/main.py", 310, 380,
            "file_patch _mode_create 完整代码")

# ============ 2. file_patch 的 run() 分派逻辑 ============
# 看 390-430，确认 create 分支怎么走
print_lines("harness_modules/file_patch/main.py", 390, 430,
            "file_patch run() 分派逻辑")

# ============ 3. decider.py 的防假成功完整逻辑 ============
print_lines("core/services/supervisor/decider.py", 1, 100,
            "decider.py 前 100 行（防假成功逻辑）")

# ============ 4. task_summarizer 的写操作检查 ============
print("\n" + "="*70)
print("=== 4. task_summarizer 定义位置 + 写操作检查 ===")
print("="*70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                     "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "def task_summarizer" in content:
        print(f"\n[FILE] {py.relative_to(ROOT)}")
        lines = content.splitlines()
        # 找函数起始行
        start = next(i for i, l in enumerate(lines) if "def task_summarizer" in l)
        # 打印该函数全文（最多 150 行）
        for i in range(start, min(start + 150, len(lines))):
            print(f"  {i+1:4d} | {lines[i]}")
        break

# ============ 5. FORCE_RETRY 的触发点 ============
print("\n" + "="*70)
print("=== 5. FORCE_RETRY 触发点（在 continuation.py 里）===")
print("="*70)
cont = ROOT / "core/services/supervisor/continuation.py"
if cont.exists():
    lines = cont.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, 1):
        if "FORCE_RETRY" in line or "insufficient_credits" in line:
            # 打印前后 10 行
            start = max(0, i - 10)
            end = min(len(lines), i + 5)
            print(f"\n  [行 {i}] {line.strip()}")
            print(f"  --- 上下文 ---")
            for j in range(start, end):
                marker = ">>>" if j == i - 1 else "   "
                print(f"  {marker} {j+1:4d} | {lines[j]}")
            break

# ============ 6. 全局搜索写操作白名单 ============
print("\n" + "="*70)
print("=== 6. 写操作白名单（搜 'file_patch' 和 'run_python' 同现的行）===")
print("="*70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                     "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        # 找同时包含 file_patch 和 run_python 的行（白名单特征）
        if "file_patch" in line and "run_python" in line and len(line) < 500:
            print(f"\n  [FILE] {py.relative_to(ROOT)}:{i}")
            print(f"  {line.rstrip()[:300]}")

# ============ 7. insufficient_credits 后是否立即 return ============
print("\n" + "="*70)
print("=== 7. insufficient_credits 处理逻辑 ===")
print("="*70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                     "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "insufficient_credits" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if "insufficient_credits" in line:
                print(f"\n  [FILE] {py.relative_to(ROOT)}:{i}")
                # 打印前后 5 行
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                for j in range(start, end):
                    marker = ">>>" if j == i - 1 else "   "
                    print(f"  {marker} {j+1:4d} | {lines[j]}")

print("\n=== 诊断 2 完成 ===")
