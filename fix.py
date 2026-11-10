# fix.py
import subprocess
import os

print("🔄 正在将 executor_callback.py 恢复到 P2 纯净版...")
# 1. 强制从 Git 恢复该文件
subprocess.run(["git", "checkout", "p2-completed", "--", "core/services/swarm/executor_callback.py"])

# 2. 注入最简单的双重兜底代码（不用 SQL，只调新任务）
p = 'core/services/swarm/executor_callback.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 强行找到 retry 分支
intercept_code = """
    if review_result == "retry":
        _err_log = str(output or "") + " " + str(review_reason or "")
        if task.get("retry_count", 0) >= 2 and task.get("heal_count", 0) < 2:
            task["heal_count"] = task.get("heal_count", 0) + 1
            print(f"[double_heal] 🚨 触发兜底！(第 {task['heal_count']} 次)")
            try:
                from .auto_heal import auto_heal_code
                _heal_cmd = await auto_heal_code(_err_log)
                if not _heal_cmd:
                    from ..supervisor.diagnose_service import diagnose_and_fix
                    _heal_cmd = await diagnose_and_fix(_err_log)
                if _heal_cmd:
                    print(f"[double_heal] ✅ 兜底成功，处方: {_heal_cmd}")
                    _delete_pending_from_db(task_id)
                    if _run_id:
                        from ..supervisor.runs import finish_run
                        finish_run(_run_id, 'failed')
                    from .commander import plan_task
                    await plan_task(
                        user_id=task.get("user_id"),
                        conversation_id=task.get("conversation_id"),
                        user_input=_heal_cmd,
                        supervisor_id=task.get("supervisor_id")
                    )
                    print("[double_heal] 🚀 处方已派发给护士。")
                    return {"status": "diagnosed", "task_id": task_id}
                else:
                    print("[double_heal] ❌ 医生无法开具处方，放弃治疗。")
                    _delete_pending_from_db(task_id)
                    return {"status": "failed", "task_id": task_id}
            except Exception as e:
                print(f"[double_heal] 异常: {e}")
                _delete_pending_from_db(task_id)
                return {"status": "failed", "task_id": task_id}
"""

c = c.replace('    if review_result == "retry":\n', intercept_code, 1)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print("✅ 恢复并重新注入完成！请重启后端！")
