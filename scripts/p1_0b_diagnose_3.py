# -*- coding: utf-8 -*-
"""第 3 轮诊断：解决 GBK 编码 + 精准打印 run()/decider/FORCE_RETRY"""
import sys
import io

# 强制 UTF-8 输出（解决 GBK 控制台报错）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def dump(path, start, end, label):
    print(f"\n{'='*70}")
    print(f"=== {label} ({path}:{start}-{end}) ===")
    print('='*70)
    full = ROOT / path
    if not full.exists():
        print(f"  [文件不存在] {path}")
        return
    lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
    for i in range(start - 1, min(end, len(lines))):
        print(f"  {i+1:4d} | {lines[i]}")


# ============ 1. file_patch 的 run() 完整函数（424-520） ============
dump("harness_modules/file_patch/main.py", 424, 520,
     "file_patch run() 完整函数（找外层 try/except 吞错的地方）")

# ============ 2. decider.py 30-80（防假成功白名单） ============
dump("core/services/supervisor/decider.py", 30, 80,
     "decider.py 30-80（防假成功判断逻辑）")

# ============ 3. FORCE_RETRY 定义位置（grep 全项目） ============
print(f"\n{'='*70}")
print("=== FORCE_RETRY 定义位置（grep 全项目）===")
print('='*70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                     "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "FORCE_RETRY" not in content:
        continue
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        # 只看定义位置或调用位置，不要打印无关注释
        if "FORCE_RETRY" in line and "def " not in line:
            print(f"  [FILE] {py.relative_to(ROOT)}:{i}")
            print(f"    {line.rstrip()[:200]}")
            # 只打印前后 3 行上下文
            for j in range(max(0, i - 3), min(len(lines), i + 2)):
                if j == i - 1:
                    continue
                print(f"    {j+1:4d} | {lines[j].rstrip()[:200]}")

# ============ 4. insufficient_credits 处理 ============
print(f"\n{'='*70}")
print("=== insufficient_credits 处理位置 ===")
print('='*70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                     "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "insufficient_credits" not in content:
        continue
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if "insufficient_credits" in line:
            print(f"  [FILE] {py.relative_to(ROOT)}:{i}")
            for j in range(max(0, i - 3), min(len(lines), i + 3)):
                print(f"  {j+1:4d} | {lines[j].rstrip()[:200]}")

# ============ 5. task_summarizer 里的写操作白名单 ============
print(f"\n{'='*70}")
print("=== task_summarizer 的写操作检查（打印函数内所有相关行）===")
print('='*70)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                     "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "def task_summarizer" not in content:
        continue
    lines = content.splitlines()
    start = next(i for i, l in enumerate(lines) if "def task_summarizer" in l)
    # 打印该函数内所有提到工具名的行
    for i in range(start, min(start + 200, len(lines))):
        line = lines[i]
        if any(k in line for k in ["file_patch", "run_python", "file_write",
                                     "ssh_exec", "run_forever", "写操作",
                                     "修改动词", "无 file_patch"]):
            print(f"  {py.relative_to(ROOT)}:{i+1}: {line.rstrip()[:200]}")
    print(f"  [函数起始行] {py.relative_to(ROOT)}:{start+1}")
    break

# ============ 6. file_write 工具是否存在 ============
print(f"\n{'='*70}")
print("=== file_write 工具是否存在 ===")
print('='*70)
fw = ROOT / "harness_modules/file_write/main.py"
if fw.exists():
    print(f"  [EXIST] harness_modules/file_write/main.py ({fw.stat().st_size} bytes)")
    # 看它返回什么结构
    content = fw.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(content.splitlines(), 1):
        if '"success"' in line or "return {" in line:
            print(f"    {i:4d} | {line.rstrip()[:150]}")
else:
    print(f"  [MISS] harness_modules/file_write/main.py")

print("\n=== 诊断 3 完成 ===")
