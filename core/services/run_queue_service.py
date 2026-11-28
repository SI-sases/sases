# core/services/run_queue_service.py
# -*- coding: utf-8 -*-
"""P1 后台执行队列：一个进程内 asyncio worker，状态落 supervisor_runs。"""
import asyncio

from ..db import db_cursor

_queue = asyncio.PriorityQueue()
_started = False
_workers = []
_queued_ids = set()


def _get_run(run_id):
    with db_cursor() as cur:
        cur.execute("SELECT id,user_id,conversation_id,goal,supervisor_id,task_type,status "
                    "FROM supervisor_runs WHERE id=?", (int(run_id),))
        row = cur.fetchone()
    return dict(row) if row else None


def _set_status(run_id, status):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status=? WHERE id=?", (status, int(run_id)))


async def _notify(user_id, run_id, status):
    try:
        from ..api_routes.ws_routes import broadcast_to_user
        await broadcast_to_user(int(user_id), {
            "type": "sases_run_update", "run_id": int(run_id), "status": status,
        })
    except Exception:
        pass


async def enqueue(run_id, priority=5):
    _set_status(run_id, "queued")
    _queued_ids.add(int(run_id))
    await _queue.put((int(priority), int(run_id)))
    try:
        run = _get_run(run_id)
        if run:
            await _notify(run["user_id"], run_id, "queued")
    except Exception:
        pass
    return int(run_id)


async def _worker():
    while True:
        _prio, run_id = await _queue.get()
        _queued_ids.discard(int(run_id))
        try:
            run = _get_run(run_id)
            if not run or run.get("status") not in ("queued", "interrupted", "running"):
                continue
            from . import run_service
            await run_service.run_once(
                run["user_id"], run["conversation_id"], run["goal"],
                source=run.get("task_type") or "chat",
                supervisor_id=run.get("supervisor_id") or "sases_assistant",
                max_steps=20, run_id=run_id, finish=True,
            )
            await _notify(run["user_id"], run_id, "completed")
            latest = _get_run(run_id)
            if latest and latest.get("status"):
                await _notify(run["user_id"], run_id, latest["status"])
        except Exception as e:
            print("[queue] run 失败: " + str(e))
            try:
                _set_status(run_id, "failed")
            except Exception:
                pass
        finally:
            _queue.task_done()


async def _sweeper():
    # 兜底：队列内存丢失/worker 卡死时，定时把 queued 重新入队
    while True:
        try:
            await asyncio.sleep(5)
            with db_cursor() as cur:
                cur.execute("SELECT id FROM supervisor_runs WHERE status='queued' ORDER BY id")
                ids = [int(r["id"]) for r in cur.fetchall()]
            for rid in ids:
                if rid not in _queued_ids:
                    _queued_ids.add(rid)
                    await _queue.put((5, rid))
        except Exception:
            await asyncio.sleep(5)


async def start():
    global _started, _workers
    if _started:
        return
    _started = True
    from .capacity_service import profile
    n = max(1, int(profile().get("background_parallel") or 1))
    _workers = [asyncio.create_task(_worker()) for _ in range(n)]
    _workers.append(asyncio.create_task(_sweeper()))
    from core.quiet import boot
    boot("[queue] workers=" + str(n))
    try:
        with db_cursor() as cur:
            cur.execute("SELECT id FROM supervisor_runs WHERE status='queued' ORDER BY id")
            ids = [int(r["id"]) for r in cur.fetchall()]
        for rid in ids:
            _queued_ids.add(rid)
            await _queue.put((5, rid))
        if ids:
            print("[queue] requeued " + str(len(ids)))
    except Exception as e:
        print("[queue] recover failed: " + str(e))
