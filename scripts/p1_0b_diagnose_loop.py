# -*- coding: utf-8 -*-
"""诊断：file_patch 空内容 + 防假成功误判 + file_write 白名单 + credits FORCE_RETRY"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

# ============ 1. file_patch 的 create 模式代码 ============
print("=== 1. file_patch create 模式（找 new_length=0 的根因）===")
fp = ROOT / "harness_modules/file_patch/main.py"
if fp.exists():
    content = fp.read_text(encoding="utf-8")
    # 找 create_if_missing 相关逻辑
    for i, line in enumerate(content.splitlines(), 1):
        if any(k in line for k in ["create_if_missing", "mode.*create",
                                     "new_length", "new_content"]):
            print(f"  {i:4d} | {line.rstrip()[:120]}")
else:
    print("  [file_patch/main.py 不存在]")

# ============ 2. 防假成功逻辑位置 ============
print("\n=== 2. 防假成功逻辑（search '防假成功' / '没有任何成功的'）===")
for py in ROOT.rglob("*.py"):
    if "venv" in str(py) or "python312" in str(py) or "__pycache__" in str(py):
        continue
    if "build_portable" in str(py) or "_archive" in str(py) or "core.bak" in str(py):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "防假成功" in content or "没有任何成功的" in content:
        print(f"\n  [FILE] {py.relative_to(ROOT)}")
        for i, line in enumerate(content.splitlines(), 1):
            if "防假成功" in line or "没有任何成功的" in line:
                print(f"    {i:4d} | {line.rstrip()[:140]}")

# ============ 3. 写操作白名单在哪 ============
print("\n=== 3. 写操作白名单（search 'run_forever' 和 'ssh_exec' 同现）===")
for py in ROOT.rglob("*.py"):
    if "venv" in str(py) or "python312" in str(py) or "__pycache__" in str(py):
        continue
    if "build_portable" in str(py) or "_archive" in str(py) or "core.bak" in str(py):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    # 找同时包含 file_patch 和 run_python 和 ssh_exec 的行（白名单定义的特征）
    for i, line in enumerate(content.splitlines(), 1):
        if ("file_patch" in line and "run_python" in line
            and "ssh_exec" in line):
            print(f"  {py.relative_to(ROOT)}:{i}")
            print(f"    {line.rstrip()[:200]}")

# ============ 4. FORCE_RETRY 触发点 ============
print("\n=== 4. FORCE_RETRY 触发点（credits 不足后不该重试）===")
for py in ROOT.rglob("*.py"):
    if "venv" in str(py) or "python312" in str(py) or "__pycache__" in str(py):
        continue
    if "build_portable" in str(py) or "_archive" in str(py) or "core.bak" in str(py):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for i, line in enumerate(content.splitlines(), 1):
        if "FORCE_RETRY" in line and "def " not in line:
            print(f"  {py.relative_to(ROOT)}:{i}: {line.rstrip()[:120]}")

# ============ 5. task_summarizer 里怎么写操作检查的 ============
print("\n=== 5. task_summarizer 的写操作检查（找关键词）===")
# 找 task_summarizer 定义在哪
for py in ROOT.rglob("*.py"):
    if "venv" in str(py) or "python312" in str(py) or "__pycache__" in str(py):
        continue
    if "build_portable" in str(py) or "_archive" in str(py) or "core.bak" in str(py):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "def task_summarizer" in content:
        print(f"  [FOUND] {py.relative_to(ROOT)}")
        lines = content.splitlines()
        start = next(i for i, l in enumerate(lines) if "def task_summarizer" in l)
        # 打印该函数内所有提到写操作工具的行
        for i in range(start, min(start + 200, len(lines))):
            if any(k in lines[i] for k in ["file_patch", "run_python", "file_write",
                                             "ssh_exec", "run_forever",
                                             "写操作", "修改动词"]):
                print(f"    {i+1:4d} | {lines[i].rstrip()[:140]}")

print("\n=== 诊断完成 ===")
