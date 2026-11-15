# -*- coding: utf-8 -*-
"""最终修复：第 2 处 FORCE_RETRY（行号插入）+ task_summarizer 宽松判断 + debug"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "core/services/swarm/executor_callback.py"
DEC = ROOT / "core/services/supervisor/decider.py"

# ============================================================
# A. executor_callback.py: 用行号插入，不用文本锚点
# ============================================================
print("=" * 60)
print("A. executor_callback.py: 按行号插入 FORCE_RETRY 状态检查")
print("=" * 60)

ec_lines = EC.read_text(encoding="utf-8").splitlines()

# 找所有触发点（不管缩进多少）
trigger_indices = []
for i, line in enumerate(ec_lines):
    if "if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:" in line:
        trigger_indices.append(i)

print(f"[INFO] 找到 {len(trigger_indices)} 处触发点: {[i+1 for i in trigger_indices]}")

# 检查每处是否已修（下一行包含 _r_chk）
need_fix = []
for i in trigger_indices:
    next_line = ec_lines[i+1] if i+1 < len(ec_lines) else ""
    if "_r_chk" in next_line:
        print(f"[SKIP] 第 {i+1} 行已修复")
    else:
        need_fix.append(i)
        print(f"[NEED] 第 {i+1} 行需要修复")

# 从大到小插入（避免行号偏移）
for i in sorted(need_fix, reverse=True):
    indent = len(ec_lines[i]) - len(ec_lines[i].lstrip())
    sp = ' ' * indent
    insert_code = [
        sp + '# [P1-0b] run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY',
        sp + '    _r_chk = get_run(_run_id) if _run_id else None',
        sp + '    _r_st = (_r_chk or {}).get("status", "")',
        sp + '    if _r_st in ("insufficient_credits", "failed", "completed"):',
        sp + '        print(f"[supervisor] run 状态={_r_st}，跳过 FORCE_RETRY，直接终止")',
        sp + '        return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st} 终止"}',
    ]
    ec_lines[i+1:i+1] = insert_code
    print(f"[OK] 在第 {i+1} 行后插入 6 行")

if need_fix:
    EC.write_text('\n'.join(ec_lines), encoding="utf-8")
    print(f"[OK] executor_callback.py 已更新，{EC.stat().st_size} bytes")
else:
    print("[SKIP] 所有触发点已修复")

# ============================================================
# B. decider.py: 宽松判断 + debug 打印
# ============================================================
print("\n" + "=" * 60)
print("B. decider.py: 宽松判断 + debug")
print("=" * 60)

dec_content = DEC.read_text(encoding="utf-8")

# 匹配所有可能的旧代码
patterns = [
    # 原始版
    """        _has_success_patch = any(r.get('command') == 'file_patch' and r.get('status') == 'success' for r in _res)
        _has_success_python = any(r.get('command') == 'run_python' and r.get('status') == 'success' for r in _res)""",
    # 修复 2 版
    """        _WRITE_TOOLS = ('file_patch', 'run_python', 'file_write')
        _has_success_patch = any(
            (r.get('command') in _WRITE_TOOLS or r.get('module_id') in _WRITE_TOOLS)
            and r.get('status') == 'success' for r in _res
        )
        _has_success_python = _has_success_patch  # 合并判断，向后兼容""",
]

new_block = """        # [P1-0b] 宽松判断：任何成功的写操作都算修改成功
        print(f"[task_summarizer DEBUG] _res 数量={len(_res)}")
        for _di, _dr in enumerate(_res):
            print(f"  [{_di}] command={_dr.get('command')!r} module_id={_dr.get('module_id')!r} status={_dr.get('status')!r}")
        _WRITE_TOOLS = ('file_patch', 'run_python', 'file_write', 'file_replace_range')
        _has_success_patch = False
        for _r in _res:
            if _r.get('status') != 'success':
                continue
            _cmd = str(_r.get('command', ''))
            _mod = str(_r.get('module_id', ''))
            for _tool in _WRITE_TOOLS:
                if _tool in _cmd or _tool in _mod:
                    _has_success_patch = True
                    print(f"[task_summarizer] 命中写操作: tool={_tool}, cmd={_cmd[:50]}, mod={_mod[:50]}")
                    break
            if _has_success_patch:
                break
        _has_success_python = _has_success_patch"""

replaced = False
for old in patterns:
    if old in dec_content:
        dec_content = dec_content.replace(old, new_block, 1)
        print(f"[OK] 已替换为宽松版")
        replaced = True
        break

if not replaced:
    if "宽松判断：任何成功的写操作都算修改成功" in dec_content:
        print("[SKIP] decider.py 已修复")
    else:
        print("[ERROR] decider.py 锚点不匹配，需要手工检查")
        # 打印第 45-60 行看真实内容
        lines = dec_content.splitlines()
        for i in range(44, min(60, len(lines))):
            print(f"  {i+1:4d} | {lines[i]}")
        exit(1)

DEC.write_text(dec_content, encoding="utf-8")
print(f"[OK] decider.py 已更新，{DEC.stat().st_size} bytes")

# ============================================================
# C. 语法验证
# ============================================================
print("\n" + "=" * 60)
print("C. 语法验证")
print("=" * 60)
import ast

for path in [EC, DEC]:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        print(f"[OK] {path.name} 语法通过")
    except SyntaxError as e:
        print(f"[FAIL] {path.name} 语法错: {e}")
        exit(1)

print("\n=== 修复完成 ===")
