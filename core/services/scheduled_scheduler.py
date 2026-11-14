# core/services/scheduled_scheduler.py
import asyncio
from datetime import datetime, timedelta
from ..db import db_cursor
from . import scheduled_task_service


async def scheduled_task_scheduler():
    """每分钟扫一次，到点的任务执行"""
    while True:
        try:
            now = datetime.now().isoformat()
            with db_cursor() as cur:
                cur.execute(
                    "SELECT * FROM scheduled_tasks WHERE enabled=1 AND next_run_at <= ? ORDER BY next_run_at LIMIT 10",
                    (now,)
                )
                due_tasks = [dict(r) for r in cur.fetchall()]

            for task in due_tasks:
                last = task.get('last_run_at')
                if last:
                    try:
                        last_dt = datetime.fromisoformat(last)
                        if (datetime.now() - last_dt).total_seconds() < 300:
                            continue
                    except Exception:
                        pass

                result = await scheduled_task_service.execute_task(task)
                if result.get('ok'):
                    print('[sched] ' + task['id'] + ' -> run ' + str(result.get('run_id')))
                else:
                    print('[sched] ' + task['id'] + ' failed: ' + str(result.get('error')))

        except Exception as e:
            print('[sched] scheduler error: ' + str(e))

        await asyncio.sleep(60)