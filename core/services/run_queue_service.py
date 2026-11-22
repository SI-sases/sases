# core/services/run_queue_service.py
# -*- coding: utf-8 -*-
"""P1 后台执行队列：一个进程内 asyncio worker，状态落 supervisor_runs。"""
import asyncio

from ..db import db_cursor

_queue = asyncio.PriorityQueue()
_started = False
_worker_task = None


def _get_run(run_id):
    with db_cursor() as cur:
        cur.execute("SELECT id,user_id,conversation_id,goal,supervisor_id,task_type,status "
                    "FROM supervisor_runs WHERE id=?", (int(run_id),))
        row = cur.fetchone()
    return dict(row) if row else None


def _set_status(run_id, status):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status=? WHERE id=?", (status, int(run_id)))


async def enqueue(run_id, priority=5):
    _set_status(run_id, "queued")
    await _queue.put((int(priority), int(run_id)))
    return int(run_id)


async def _worker():
    while True:
        _prio, run_id = await _queue.get()
        try:
            run = _get_run(run_id)
            if not run or run.get("status") not in ("queued", "interrupted", "running"):
                continue
            from . import run_service
            await run_service.run_once(
                run["user_id"], run["conversation_id"], run["goal"],
                source=run.get("task_type") or "chat",
                supervisor_id=run.get("supervisor_id") or "sases_assistant",
                run_id=run_id, finish=True,
            )
        except Exception as e:
            print("[queue] run 失败: " + str(e))
            try:
                _set_status(run_id, "failed")
            except Exception:
                pass
        finally:
            _queue.task_done()


async def start():
    global _started, _worker_task
    if _started:
        return
    _started = True
    _worker_task = asyncio.create_task(_worker())
    try:
        with db_cursor() as cur:
            cur.execute("SELECT id FROM supervisor_runs WHERE status='queued' ORDER BY id")
            ids = [int(r["id"]) for r in cur.fetchall()]
        for rid in ids:
            await _queue.put((5, rid))
        if ids:
            print("[queue] requeued " + str(len(ids)))
    except Exception as e:
        print("[queue] recover failed: " + str(e))
