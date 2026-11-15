# -*- coding: utf-8 -*-
"""修复 executor_callback.py：insufficient_credits 后立即 return（幂等）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "core/services/swarm/executor_callback.py"
content = EC.read_text(encoding="utf-8")

# 找两处 FORCE_RETRY 的入口，在它前面插入状态检查
old_force = """                        if _force_retry_count < 3:
                            task['_force_retry_count'] = _force_retry_count + 1
                            _continue = True"""

new_force = """                        # 检查 run 状态：insufficient_credits / failed 后不再 FORCE_RETRY
                        _run_now = get_run(_run_id) if _run_id else None
                        _run_status = (_run_now or {}).get('status', '')
                        if _run_status in ('insufficient_credits', 'failed', 'completed'):
                            print(f'[supervisor] run 状态={_run_status}，跳过 FORCE_RETRY，直接终止')
                            return {"status": "failed", "task_id": task_id, "summary": f"任务因 {_run_status} 终止"}

                        if _force_retry_count < 3:
                            task['_force_retry_count'] = _force_retry_count + 1
                            _continue = True"""

if old_force in content:
    content = content.replace(old_force, new_force)
    print("[OK] FORCE_RETRY 前已加状态检查（两处）")
elif "run 状态=" in content and "跳过 FORCE_RETRY" in content:
    print("[SKIP] 状态检查已存在")
else:
    print("[ERROR] 找不到 FORCE_RETRY 原文，手工检查")
    exit(1)

EC.write_text(content, encoding="utf-8")
print(f"[OK] executor_callback.py 已更新，{EC.stat().st_size} bytes")
