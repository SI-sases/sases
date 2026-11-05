import os
import asyncio
import json
import httpx
from datetime import datetime
from core.services.outbox.outbox_db import outbox_cursor
from core.services.outbox.outbox_service import mark_success, mark_failed

API_BASE = os.environ.get("SASES_API_BASE", "http://127.0.0.1:8001")
WORKER_INTERVAL = 2
BATCH_SIZE = 20

def _fetch_due():
    now = datetime.now().isoformat()
    with outbox_cursor() as cur:
        cur.execute("SELECT * FROM outbox WHERE status IN ('pending','sending') AND next_retry_at <= ? ORDER BY id ASC LIMIT ?", (now, BATCH_SIZE))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]

def _group_by_conv(rows):
    groups = {}
    for r in rows:
        try:
            payload = json.loads(r.get("payload") or "{}")
        except Exception:
            payload = {}
        key = payload.get("conversation_id") or payload.get("target_uid") or r.get("target_url")
        groups.setdefault(key, []).append(r)
    return groups


async def _send_sequential(rows):
    for row in rows:
        ok = await _send_one(row)
        if not ok:
            break


async def _send_one(row):
    try:
        headers = json.loads(row.get("headers") or "{}")
    except Exception:
        headers = {}
    _tu = row["target_url"]
    url = _tu if _tu.startswith("http") else API_BASE + _tu
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            resp = await cli.post(url, content=row["payload"], headers=headers)
        if resp.status_code in (200, 201, 409):
            mark_success(row["msg_id"])
            return True
        mark_failed(row["msg_id"], f"HTTP {resp.status_code}")
        return False
    except Exception as e:
        mark_failed(row["msg_id"], str(e)[:200])
        return False





async def outbox_worker():
    print("[outbox] worker started")
    idle_ticks = 0
    while True:
        try:
            rows = _fetch_due()
            if rows:
                idle_ticks = 0
                groups = _group_by_conv(rows)
                await asyncio.gather(*[_send_sequential(g) for g in groups.values()], return_exceptions=True)
                print(f"[outbox] processed {len(rows)} messages")
            else:
                idle_ticks += 1
                if idle_ticks % 30 == 0:
                    print("[outbox] idle, pending=0")
        except Exception as e:
            print(f"[outbox] worker error: {e}")
        await asyncio.sleep(WORKER_INTERVAL)
