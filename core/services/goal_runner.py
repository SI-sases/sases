# core/services/goal_runner.py
# -*- coding: utf-8 -*-
"""自动循环目标：每轮创建普通 run，走 agent_loop，不再使用四角色。"""
import asyncio
import os
from datetime import datetime, timedelta

from ..db import db_cursor


def _now():
    return datetime.now().isoformat()


def create_goal(user_id, conversation_id, goal, max_rounds=10, budget_tokens=200000):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO agent_goals (user_id, conversation_id, goal, status, max_rounds, "
            "rounds_done, budget_tokens, next_run_at, created_at, updated_at) "
            "VALUES (?,?,?,'active',?,0,?,?,?,?)",
            (int(user_id), int(conversation_id or 0), str(goal), int(max_rounds),
             int(budget_tokens), _now(), _now(), _now()))
        return cur.lastrowid


def due_goals(limit=5):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM agent_goals WHERE status='active' "
                    "AND (next_run_at IS NULL OR next_run_at<=?) ORDER BY id LIMIT ?",
                    (_now(), int(limit)))
        return [dict(r) for r in cur.fetchall()]


def finish_round(goal_id, run_id, status):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM agent_goals WHERE id=?", (goal_id,))
        g = cur.fetchone()
        if not g:
            return
        rounds = int(g["rounds_done"] or 0) + 1
        if status != "completed":
            cur.execute("UPDATE agent_goals SET rounds_done=?, last_run_id=?, status='blocked', "
                        "updated_at=? WHERE id=?", (rounds, run_id, _now(), goal_id))
            return
        if rounds >= int(g["max_rounds"] or 1):
            cur.execute("UPDATE agent_goals SET rounds_done=?, last_run_id=?, status='completed', "
                        "updated_at=? WHERE id=?", (rounds, run_id, _now(), goal_id))
            return
        nxt = (datetime.now() + timedelta(seconds=60)).isoformat()
        cur.execute("UPDATE agent_goals SET rounds_done=?, last_run_id=?, next_run_at=?, "
                    "status='active', updated_at=? WHERE id=?", (rounds, run_id, nxt, _now(), goal_id))


async def run_goal_round(g):
    from . import run_service
    user_id = int(g["user_id"])
    cid = int(g["conversation_id"] or 0)
    if not cid:
        return
    run_id = run_service.create_run(user_id, cid, "goal", g["goal"],
                                    supervisor_id="sases_assistant",
                                    max_rounds=int(g.get("max_rounds") or 10))
    # 标记为运行中，避免下一次轮询重复取
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE agent_goals SET status='running', last_run_id=?, updated_at=? WHERE id=?",
                    (run_id, _now(), g["id"]))
    try:
        res = await run_service.run_once(user_id, cid, g["goal"], source="goal",
                                         supervisor_id="sases_assistant",
                                         max_steps=8, run_id=run_id)
        finish_round(g["id"], run_id, "completed" if res.get("status") == "completed" else "failed")
    except Exception as e:
        print("[goal] round 失败: " + str(e))
        finish_round(g["id"], run_id, "failed")


async def goal_runner_loop(interval=10):
    print("[goal] runner started")
    while True:
        if os.getenv("SASES_GOAL_RUNNER", "1") != "0":
            try:
                for g in due_goals():
                    await run_goal_round(g)
            except Exception as e:
                print("[goal] 轮询失败: " + str(e))
        await asyncio.sleep(interval)
