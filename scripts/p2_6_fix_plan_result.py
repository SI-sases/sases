import shutil
from datetime import datetime

TARGET = "core/services/scheduled_task_service.py"

OLD = '''        await swarm_service.plan_task(
            user_id=user_id,
            conversation_id=cid,
            user_input=goal,
            supervisor_id=sid,
            supervisor_run_id=run_id,
        )

        next_run = _compute_next_run(task['cron_expr'])'''

NEW = '''        plan_result = await swarm_service.plan_task(
            user_id=user_id,
            conversation_id=cid,
            user_input=goal,
            supervisor_id=sid,
            supervisor_run_id=run_id,
        )

        # plan_task 返回 None / no_plan / error 时，标记 run 失败，避免永久卡 running
        if plan_result is None or (isinstance(plan_result, dict) and plan_result.get('status') in ('no_plan', 'error')):
            from .supervisor.runs import finish_run
            try:
                finish_run(run_id, 'plan_failed')
            except Exception:
                pass
            reason = plan_result.get('reason') or plan_result.get('message') if isinstance(plan_result, dict) else 'plan_task returned None'
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE scheduled_tasks SET failure_count=failure_count+1, updated_at=? WHERE id=?",
                            (datetime.now().isoformat(), task_id))
            return {'ok': False, 'error': 'plan_failed: ' + str(reason)}

        next_run = _compute_next_run(task['cron_expr'])'''

def main():
    content = open(TARGET, "r", encoding="utf-8").read()

    if "plan_result = await swarm_service.plan_task" in content:
        print("already patched, skip")
        return

    if OLD not in content:
        print("ERROR: anchor not found")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, TARGET + ".bak_p2_6_" + ts)
    print("backup done")

    content = content.replace(OLD, NEW, 1)
    open(TARGET, "w", encoding="utf-8").write(content)
    print("patched")

if __name__ == "__main__":
    main()