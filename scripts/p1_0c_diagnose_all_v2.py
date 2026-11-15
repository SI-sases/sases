# -*- coding: utf-8 -*-
"""综合诊断 v2：不用 TextIOWrapper，用 reconfigure，所有输出纯 ASCII"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 用 os.walk 剪枝，不进入 venv/python312 等大目录
SKIP_DIRS = {"venv", "venv312", "python312", "__pycache__",
             "build_portable", "_archive", "core.bak", "node_modules",
             ".git", ".pytest_cache"}

def walk_py(root):
    """遍历 .py，跳过 SKIP_DIRS 里的目录"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                yield Path(dirpath) / fn

def walk_md(root):
    """遍历 .md，跳过 SKIP_DIRS 里的目录"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".md"):
                yield Path(dirpath) / fn

# ============================================================
# 1. 积分拦截：continuation.py 的 deduct_round + finish_run
# ============================================================
print("=" * 70)
print("[1] 积分拦截: continuation.py 关键行")
print("=" * 70)
cont = ROOT / "core/services/supervisor/continuation.py"
if cont.exists():
    lines = cont.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines, 1):
        if any(k in line for k in ["insufficient_credits", "deduct_round",
                                    "finish_run", "def check_and_continue"]):
            print(f"  {i:4d} | {line.rstrip()[:150]}")

print("\n[1b] send.py 里是否检查积分")
send_py = ROOT / "core/services/message/send.py"
if send_py.exists():
    lines = send_py.read_text(encoding="utf-8", errors="replace").splitlines()
    hit = False
    for i, line in enumerate(lines, 1):
        if "credits" in line.lower() or "balance" in line.lower() or "deduct" in line.lower():
            print(f"  {i:4d} | {line.rstrip()[:150]}")
            hit = True
    if not hit:
        print("  [NONE] send.py 里没有积分检查")

print("\n[1c] 派单入口 task_engine.py 是否检查积分")
te = ROOT / "core/services/task_engine.py"
if te.exists():
    lines = te.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines, 1):
        if "credits" in line.lower() or "balance" in line.lower():
            print(f"  {i:4d} | {line.rstrip()[:150]}")

# ============================================================
# 2. L2 深度审核接入
# ============================================================
print("\n" + "=" * 70)
print("[2] L2 深度审核接入")
print("=" * 70)

ec = ROOT / "core/services/swarm/executor_callback.py"
if ec.exists():
    content = ec.read_text(encoding="utf-8", errors="replace")
    print(f"  executor_callback.py 引用 reviewer_deep: {'reviewer_deep' in content}")
    print(f"  executor_callback.py 调用 should_deep_review: {'should_deep_review' in content}")
    lines = content.splitlines()
    print("\n  [review_step 调用行]")
    for i, line in enumerate(lines, 1):
        if "review_step(" in line and "def " not in line and "import" not in line:
            print(f"    {i:4d} | {line.rstrip()[:150]}")

rd = ROOT / "core/services/swarm/reviewer_deep.py"
if rd.exists():
    content = rd.read_text(encoding="utf-8", errors="replace")
    print(f"\n  reviewer_deep.py 大小: {len(content)} 字符")
    for fn in ["should_deep_review", "generate_test_steps",
               "dispatch_test_task", "mark_deep_review_used"]:
        has = f"def {fn}" in content or f"async def {fn}" in content
        print(f"    {fn}: {'YES' if has else 'NO'}")
else:
    print("\n  [MISS] reviewer_deep.py 不存在")

# ============================================================
# 3. .md 文件扫描
# ============================================================
print("\n" + "=" * 70)
print("[3] .md 文件清理")
print("=" * 70)

md_list = []
for md in walk_md(ROOT):
    try:
        size = md.stat().st_size
        md_list.append((md, size))
    except Exception:
        pass

print(f"  总 .md 文件: {len(md_list)}")

empty = [(m, s) for m, s in md_list if s < 100]
tiny = [(m, s) for m, s in md_list if 100 <= s < 500]
temp = [(m, s) for m, s in md_list if any(
    x in m.name.lower() for x in ["temp", "tmp", "bak", "old"])]

print(f"  空文件 (<100B): {len(empty)}")
print(f"  极小 (100-500B): {len(tiny)}")
print(f"  临时文件 (名含temp/bak): {len(temp)}")

if empty:
    print("\n  [空文件]")
    for m, s in empty:
        print(f"    {m.relative_to(ROOT)} ({s}B)")

if temp:
    print("\n  [临时文件]")
    for m, s in temp:
        print(f"    {m.relative_to(ROOT)} ({s}B)")

print("\n  [最大 10 个 .md]")
for m, s in sorted(md_list, key=lambda x: -x[1])[:10]:
    print(f"    {m.relative_to(ROOT)} ({s // 1024}KB)")

print("\n  [docs/ 目录结构]")
docs = ROOT / "docs"
if docs.exists():
    for item in sorted(docs.iterdir()):
        if item.is_dir():
            count = sum(1 for _ in item.rglob("*.md"))
            print(f"    {item.name}/ ({count} .md)")
        elif item.suffix == ".md":
            print(f"    {item.name} ({item.stat().st_size}B)")

print("\n" + "=" * 70)
print("=== 诊断完成 ===")
print("=" * 70)
