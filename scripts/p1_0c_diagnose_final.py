# -*- coding: utf-8 -*-
"""诊断 3 件事：_call_llm 签名 / scheduled_routes 完整 / finish_run 幂等"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
import inspect

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# 1. _call_llm 真实签名
# ============================================================
print("=" * 70)
print("[1] _call_llm 真实签名")
print("=" * 70)
try:
    sys.path.insert(0, str(ROOT))
    from core.services.swarm.llm_parser import _call_llm
    sig = inspect.signature(_call_llm)
    print(f"  def _call_llm{sig}")
    for name, param in sig.parameters.items():
        default = param.default if param.default is not inspect.Parameter.empty else "<必填>"
        print(f"    - {name}: {param.kind}, default={default}")
except Exception as e:
    print(f"  [ERROR] {e}")

# ============================================================
# 2. scheduled_routes.py 完整内容
# ============================================================
print("\n" + "=" * 70)
print("[2] scheduled_routes.py 完整内容")
print("=" * 70)
sr = ROOT / "core/api_routes/scheduled_routes.py"
if sr.exists():
    content = sr.read_text(encoding="utf-8")
    lines = content.splitlines()
    # 只打印路由定义 + 函数签名
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if (stripped.startswith("@router.") or
            stripped.startswith("async def ") or
            stripped.startswith("def ") or
            "response_model" in stripped or
            "return {" in stripped):
            print(f"  {i:4d} | {line.rstrip()[:150]}")
else:
    print("  [MISS]")

# ============================================================
# 3. finish_run 是否幂等
# ============================================================
print("\n" + "=" * 70)
print("[3] finish_run 实现（runs.py）")
print("=" * 70)
runs = ROOT / "core/services/supervisor/runs.py"
if runs.exists():
    content = runs.read_text(encoding="utf-8")
    lines = content.splitlines()
    # 找 finish_run 定义
    for i, line in enumerate(lines, 1):
        if "def finish_run" in line:
            print(f"\n  [finish_run @ {i}]")
            for j in range(i - 1, min(i + 40, len(lines))):
                print(f"  {j+1:4d} | {lines[j]}")
            break
else:
    print("  [MISS] runs.py")

# ============================================================
# 4. 调度器在 bootstrap.py 里怎么启动的
# ============================================================
print("\n" + "=" * 70)
print("[4] bootstrap.py 里的调度器启动")
print("=" * 70)
bs = ROOT / "core/bootstrap.py"
if bs.exists():
    content = bs.read_text(encoding="utf-8")
    lines = content.splitlines()
    found = False
    for i, line in enumerate(lines, 1):
        if "scheduled" in line.lower() and ("def " in line or "task" in line.lower()):
            print(f"  {i:4d} | {line.rstrip()[:150]}")
            found = True
    if not found:
        print("  [未找到] bootstrap.py 里可能没有调度器启动代码")
        # 扫一下全部 scheduled 相关
        for i, line in enumerate(lines, 1):
            if "scheduled" in line.lower():
                print(f"  {i:4d} | {line.rstrip()[:150]}")

# ============================================================
# 5. reviewer_deep.py 当前的 call_llm 调用格式
# ============================================================
print("\n" + "=" * 70)
print("[5] reviewer_deep.py 里的 call_llm 调用")
print("=" * 70)
rd = ROOT / "core/services/swarm/reviewer_deep.py"
if rd.exists():
    content = rd.read_text(encoding="utf-8")
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if "call_llm" in line and "def " not in line:
            print(f"  {i:4d} | {line.rstrip()[:150]}")
        # 打印调用上下文
        if "resp = await call_llm" in line:
            for j in range(i - 1, min(i + 8, len(lines))):
                print(f"  {j+1:4d} | {lines[j]}")

print("\n=== 诊断完成 ===")
