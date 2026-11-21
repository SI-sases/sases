# core/services/proposed_run_service.py
# -*- coding: utf-8 -*-
"""A2A: proposed run 超时自动拒绝 + 回执。"""
import asyncio
import datetime

from ..db import db_cursor


async def expire_stale(minutes=5):
    try:
        cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=int(minutes))).isoformat()
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM supervisor_runs WHERE status='proposed' AND created_at < ? LIMIT 50",
                (cutoff,),
            )
            ids = [r["id"] for r in cur.fetchall()]
        n = 0
        for rid in ids:
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE supervisor_runs SET status='rejected', finished_at=? WHERE id=? AND status='proposed'",
                            (datetime.datetime.now().isoformat(), rid))
            try:
                from .cross_account_delivery import notify_a2a_rejected
                await notify_a2a_rejected(rid)
            except Exception as e:
                print("[a2a] 超时回执失败: " + str(e))
            n += 1
        if n:
            print("[a2a] 超时拒绝 " + str(n) + " 个 proposed run")
        return n
    except Exception as e:
        print("[a2a] 超时检查失败: " + str(e))
        return 0


async def periodic(interval_seconds=60):
    while True:
        try:
            await expire_stale(5)
        except Exception as e:
            print("[a2a] periodic 失败: " + str(e))
        await asyncio.sleep(interval_seconds)
