# -*- coding: utf-8 -*-
"""修复 executor_callback.py：FORCE_RETRY 前加 run 状态检查（精确缩进版）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "core/services/swarm/executor_callback.py"
content = EC.read_text(encoding="utf-8")

# ============ 第 1 处（20 空格缩进） ============
old1 = """                    if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:
                        _force_retry_count = task.get('_force_retry_count', 0)
                        if _force_retry_count < 2:
                            task['_force_retry_count'] = _force_retry_count + 1
                            _continue = True
                            print(f'[supervisor] FORCE_RETRY: 判定未完成，强制覆盖为 True 进入下一轮（第 {_force_retry_count + 1} 次）')"""

new1 = """                    if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:
                        # run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                        _r_chk1 = get_run(_run_id) if _run_id else None
                        _r_st1 = (_r_chk1 or {}).get('status', '')
                        if _r_st1 in ('insufficient_credits', 'failed', 'completed'):
                            print(f'[supervisor] run 状态={_r_st1}，跳过 FORCE_RETRY，直接终止')
                            return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st1} 终止"}
                        _force_retry_count = task.get('_force_retry_count', 0)
                        if _force_retry_count < 2:
                            task['_force_retry_count'] = _force_retry_count + 1
                            _continue = True
                            print(f'[supervisor] FORCE_RETRY: 判定未完成，强制覆盖为 True 进入下一轮（第 {_force_retry_count + 1} 次）')"""

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("[OK] 第 1 处（20 空格）已加状态检查")
elif "_r_chk1" in content:
    print("[SKIP] 第 1 处已修复")
else:
    print("[ERROR] 第 1 处锚点不匹配")
    print("请检查第 314-319 行的真实内容")

# ============ 第 2 处（16 空格缩进） ============
old2 = """                if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:
                    _force_retry_count = task.get('_force_retry_count', 0)
                    if _force_retry_count < 2:
                        task['_force_retry_count'] = _force_retry_count + 1
                        _continue = True
                        print(f'[supervisor] FORCE_RETRY: 判定未完成，强制覆盖为 True 进入下一轮（第 {_force_retry_count + 1} 次）')"""

new2 = """                if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:
                    # run 状态检查：insufficient_credits / failed / completed 后不再 FORCE_RETRY
                    _r_chk2 = get_run(_run_id) if _run_id else None
                    _r_st2 = (_r_chk2 or {}).get('status', '')
                    if _r_st2 in ('insufficient_credits', 'failed', 'completed'):
                        print(f'[supervisor] run 状态={_r_st2}，跳过 FORCE_RETRY，直接终止')
                        return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_r_st2} 终止"}
                    _force_retry_count = task.get('_force_retry_count', 0)
                    if _force_retry_count < 2:
                        task['_force_retry_count'] = _force_retry_count + 1
                        _continue = True
                        print(f'[supervisor] FORCE_RETRY: 判定未完成，强制覆盖为 True 进入下一轮（第 {_force_retry_count + 1} 次）')"""

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("[OK] 第 2 处（16 空格）已加状态检查")
elif "_r_chk2" in content:
    print("[SKIP] 第 2 处已修复")
else:
    print("[ERROR] 第 2 处锚点不匹配")
    print("请检查第 707-712 行的真实内容")

EC.write_text(content, encoding="utf-8")
print(f"[OK] executor_callback.py 已更新，{EC.stat().st_size} bytes")
