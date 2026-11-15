# -*- coding: utf-8 -*-
"""修复 B：把 reviewer_deep 接入 executor_callback，同步跑测试"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# B1. 给 reviewer_deep.py 追加 execute_test_steps_sync 函数
# ============================================================
RD = ROOT / "core/services/swarm/reviewer_deep.py"
if not RD.exists():
    print("[ERROR] reviewer_deep.py 不存在")
    exit(1)

rd = RD.read_text(encoding="utf-8")

if "async def execute_test_steps_sync" in rd:
    print("[SKIP] execute_test_steps_sync 已存在")
else:
    func_code = '''

# ============================================================
# P1-0c 新增：同步执行测试步骤（供 executor_callback 调用）
# ============================================================
async def execute_test_steps_sync(test_steps):
    """同步执行测试步骤，返回结果列表

    支持：command / verify_syntax / run_python / file_read
    """
    import subprocess as _sp
    results = []

    for step in (test_steps or [])[:3]:  # 最多 3 步
        _type = step.get("type", "")
        _params = step.get("params", {}) or {}
        _step_no = step.get("step", len(results) + 1)

        try:
            if _type == "command":
                _cmd = _params.get("command", "")
                if not _cmd:
                    results.append({
                        "step": _step_no, "type": _type,
                        "status": "skipped", "output": "空命令",
                    })
                    continue
                _r = _sp.run(_cmd, shell=True, capture_output=True,
                             text=True, timeout=60, encoding="utf-8",
                             errors="replace")
                results.append({
                    "step": _step_no, "type": _type,
                    "status": "success" if _r.returncode == 0 else "failed",
                    "output": ((_r.stdout or "") + (_r.stderr or ""))[:500],
                })
            else:
                # verify_syntax / run_python / file_read
                from ...harness_runtime import invoke_tool
                _tool_result = await invoke_tool(_type, _params)
                if hasattr(_tool_result, "success"):
                    _ok = _tool_result.success
                    _out = str(getattr(_tool_result, "output", ""))[:500]
                elif isinstance(_tool_result, dict):
                    _ok = _tool_result.get("success") or _tool_result.get("syntax_ok")
                    _out = str(_tool_result)[:500]
                else:
                    _ok = False
                    _out = str(_tool_result)[:500]
                results.append({
                    "step": _step_no, "type": _type,
                    "status": "success" if _ok else "failed",
                    "output": _out,
                })
        except Exception as _e:
            results.append({
                "step": _step_no, "type": _type,
                "status": "failed",
                "output": f"异常: {type(_e).__name__}: {_e}"[:500],
            })

    return results
'''
    rd += func_code
    RD.write_text(rd, encoding="utf-8")
    print(f"[OK] execute_test_steps_sync 已追加，reviewer_deep.py 现在 {len(rd)} 字符")


# ============================================================
# B2. 在 executor_callback.py 的 review_step 后接入 L2
# ============================================================
EC = ROOT / "core/services/swarm/executor_callback.py"
if not EC.exists():
    print("[ERROR] executor_callback.py 不存在")
    exit(1)

ec = EC.read_text(encoding="utf-8")

if "# [P1-0c] L2 深度审核接入" in ec:
    print("[SKIP] L2 接入已存在")
    exit(0)

# 锚点：第 75 行 review_step 调用 + 紧跟 task["done"].add(step_id)
old_block = '''    review_result, review_reason = review_step(original_step, status, output)

    task["done"].add(step_id)'''

new_block = '''    review_result, review_reason = review_step(original_step, status, output)

    task["done"].add(step_id)

    # [P1-0c] L2 深度审核接入：所有步骤 done 后触发，只触发一次
    if review_result == "pass" and not task.get("_deep_review_done"):
        try:
            if len(task["done"]) == len(task["steps"]):
                task["_deep_review_done"] = True
                from .reviewer_deep import (
                    should_deep_review, mark_deep_review_used,
                    generate_test_steps, execute_test_steps_sync,
                )
                _l2_input = {
                    "task_id": task_id,
                    "module_id": original_step.get("module_id") or original_step.get("type"),
                    "params": original_step.get("params") or {},
                    "status": status,
                    "output": output,
                    "diff_bytes": payload.get("diff_bytes", 0),
                }
                _should, _reason = should_deep_review(task, _l2_input)
                if _should:
                    mark_deep_review_used(task_id)
                    print(f"[L2] 触发深度审核: {_reason}")
                    _test_steps = await generate_test_steps(task, _l2_input, _reason)
                    if _test_steps:
                        _test_results = await execute_test_steps_sync(_test_steps)
                        for _tr in _test_results:
                            task["results"].append({
                                "step": "L2-" + str(_tr["step"]),
                                "description": "L2 深度审核测试",
                                "command": _tr.get("type", "test"),
                                "status": _tr.get("status", "failed"),
                                "output": (_tr.get("output") or "")[:500],
                            })
                        _pass = sum(1 for r in _test_results if r.get("status") == "success")
                        print(f"[L2] 测试完成 {_pass}/{len(_test_results)} 通过")
                    else:
                        print("[L2] 审核员未生成测试步骤，跳过")
        except Exception as _e_l2:
            print(f"[L2] 接入异常（已降级为 L1）: {type(_e_l2).__name__}: {_e_l2}")
'''

if old_block in ec:
    ec = ec.replace(old_block, new_block, 1)
    EC.write_text(ec, encoding="utf-8")
    print(f"[OK] L2 已接入，executor_callback.py 现在 {len(ec)} 字符")
else:
    print("[ERROR] 锚点不匹配，打印真实代码让用户确认")
    lines = ec.splitlines()
    for i, line in enumerate(lines, 1):
        if "review_step(" in line and "def " not in line:
            for j in range(max(0, i-2), min(len(lines), i+5)):
                print(f"  {j+1:4d} | {lines[j]}")
            break
    exit(1)

# ============================================================
# B3. 语法验证
# ============================================================
print("\n[语法验证]")
import ast
for path in [RD, EC]:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        print(f"  [OK] {path.name}")
    except SyntaxError as e:
        print(f"  [FAIL] {path.name}: {e}")
        exit(1)

print("\n=== 修复 B 完成 ===")
