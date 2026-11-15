# -*- coding: utf-8 -*-
"""最终修复：decider 第二处白名单 + 清理重复 + get_run 定位"""
from pathlib import Path
import ast
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# A. decider.py：293-311 行的白名单扩展（这才是真正卡住的）
# ============================================================
print("=" * 60)
print("A. decider.py 293-311 行白名单")
print("=" * 60)

DEC = ROOT / "core/services/supervisor/decider.py"
dec = DEC.read_text(encoding="utf-8")

old_patch_check = """        _has_patch_ok = any(
            str(r.get('command') or r.get('module_id') or '') == 'file_patch' and r.get('status') == 'success'
            for r in results
        )"""

new_patch_check = """        # [P1-0b] 白名单扩展：run_python / file_write 也算写操作
        _WRITE_TOOLS_V2 = ('file_patch', 'run_python', 'file_write')
        _has_patch_ok = any(
            str(r.get('command') or r.get('module_id') or '') in _WRITE_TOOLS_V2
            and r.get('status') == 'success'
            for r in results
        )"""

if "_WRITE_TOOLS_V2" in dec:
    print("[SKIP] 293-311 行白名单已修复")
elif old_patch_check in dec:
    dec = dec.replace(old_patch_check, new_patch_check, 1)
    DEC.write_text(dec, encoding="utf-8")
    print(f"[OK] 293-311 行白名单已扩展为 file_patch/run_python/file_write")
else:
    print("[ERROR] 找不到 293-311 行的白名单原文")
    # 打印 295-305 行帮助排查
    lines = dec.splitlines()
    for i in range(294, min(306, len(lines))):
        print(f"  {i+1:4d} | {lines[i]}")
    exit(1)

# ============================================================
# B. executor_callback.py：清理我插入的重复代码
# ============================================================
print("\n" + "=" * 60)
print("B. executor_callback.py 清理重复代码")
print("=" * 60)

EC = ROOT / "core/services/swarm/executor_callback.py"
ec = EC.read_text(encoding="utf-8")

# 匹配两份重复的 _r_chk 和 _r_chk1（我插入的有 2 份）
duplicate_block = """# [P1-0b] run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                        _r_chk = get_run(_run_id) if _run_id else None
                        _r_st = (_r_chk or {}).get("status", "")
                        if _r_st in ("insufficient_credits", "failed", "completed"):
                            print(f"[supervisor] run 状态={_r_st}，跳过 FORCE_RETRY，直接终止")
                            return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st} 终止"}
                        # run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                        _r_chk1 = get_run(_run_id) if _run_id else None
                        _r_st1 = (_r_chk1 or {}).get('status', '')
                        if _r_st1 in ('insufficient_credits', 'failed', 'completed'):
                            print(f'[supervisor] run 状态={_r_st1}，跳过 FORCE_RETRY，直接终止')
                            return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st1} 终止"}
                        """

single_block = """# [P1-0b] run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                        _r_chk = get_run(_run_id) if _run_id else None
                        _r_st = (_r_chk or {}).get("status", "")
                        if _r_st in ("insufficient_credits", "failed", "completed"):
                            print(f"[supervisor] run 状态={_r_st}，跳过 FORCE_RETRY，直接终止")
                            return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st} 终止"}
                        """

if duplicate_block in ec:
    ec = ec.replace(duplicate_block, single_block, 1)
    print("[OK] 重复代码已清理")
elif "_r_chk1" not in ec:
    print("[SKIP] 无重复代码")
else:
    print("[WARN] 有 _r_chk1 但无法精确匹配，跳过清理（不影响功能）")

# 同样处理第 2 处（713 行）
duplicate_block_2 = """# [P1-0b] run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                    _r_chk = get_run(_run_id) if _run_id else None
                    _r_st = (_r_chk or {}).get("status", "")
                    if _r_st in ("insufficient_credits", "failed", "completed"):
                        print(f"[supervisor] run 状态={_r_st}，跳过 FORCE_RETRY，直接终止")
                        return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st} 终止"}
                    # run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                    _r_chk1 = get_run(_run_id) if _run_id else None
                    _r_st1 = (_r_chk1 or {}).get('status', '')
                    if _r_st1 in ('insufficient_credits', 'failed', 'completed'):
                        print(f'[supervisor] run 状态={_r_st1}，跳过 FORCE_RETRY，直接终止')
                        return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st1} 终止"}
                    """

single_block_2 = """# [P1-0b] run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                    _r_chk = get_run(_run_id) if _run_id else None
                    _r_st = (_r_chk or {}).get("status", "")
                    if _r_st in ("insufficient_credits", "failed", "completed"):
                        print(f"[supervisor] run 状态={_r_st}，跳过 FORCE_RETRY，直接终止")
                        return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st} 终止"}
                    """

if duplicate_block_2 in ec:
    ec = ec.replace(duplicate_block_2, single_block_2, 1)
    print("[OK] 第 2 处重复代码已清理")

EC.write_text(ec, encoding="utf-8")
print(f"[OK] executor_callback.py 已更新，{EC.stat().st_size} bytes")

# ============================================================
# C. 定位 get_run 未定义的位置
# ============================================================
print("\n" + "=" * 60)
print("C. 定位 get_run 未定义位置")
print("=" * 60)

# 检查 continuation.py 里 get_run 的 import
CONT = ROOT / "core/services/supervisor/continuation.py"
if CONT.exists():
    cont = CONT.read_text(encoding="utf-8")
    has_get_run_import = "get_run" in cont.split("\n\n")[0] or "from .runs import" in cont
    print(f"[continuation.py] 是否 import get_run: {has_get_run_import}")
    # 打印顶部 15 行
    lines = cont.splitlines()
    print("[顶部 15 行]")
    for i in range(min(15, len(lines))):
        print(f"  {i+1:4d} | {lines[i]}")
    # 打印所有调用点
    for i, line in enumerate(lines, 1):
        if "get_run" in line and "import" not in line:
            print(f"  [调用] {i}: {line.strip()[:100]}")

# ============================================================
# D. 语法验证
# ============================================================
print("\n" + "=" * 60)
print("D. 语法验证")
print("=" * 60)

for path in [DEC, EC]:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        print(f"[OK] {path.name} 语法通过")
    except SyntaxError as e:
        print(f"[FAIL] {path.name}: {e}")
        exit(1)

print("\n=== 修复完成 ===")
