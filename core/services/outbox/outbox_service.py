import uuid
import json
from datetime import datetime, timedelta

from core.services.outbox.outbox_db import outbox_cursor


def enqueue(target_url, payload, extra_headers=None):
    msg_id = payload.get("msg_id") or str(uuid.uuid4())
    payload["msg_id"] = msg_id
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    now = datetime.now().isoformat()
    with outbox_cursor(commit=True) as cur:
        cur.execute("INSERT INTO outbox (msg_id, target_url, payload, headers, status, retry_count, max_retries, next_retry_at, created_at) VALUES (?,?,?,?,?,?,?,?,?)", (msg_id, target_url, json.dumps(payload, ensure_ascii=False), json.dumps(headers, ensure_ascii=False), "pending", 0, 5, now, now))
    return msg_id


def mark_success(msg_id):
    with outbox_cursor(commit=True) as cur:
        cur.execute("UPDATE outbox SET status='success', completed_at=? WHERE msg_id=?", (datetime.now().isoformat(), msg_id))


def mark_failed(msg_id, error):
    with outbox_cursor() as cur:
        cur.execute('SELECT retry_count, max_retries FROM outbox WHERE msg_id=?', (msg_id,))
        row = cur.fetchone()
    if not row:
        return
    retry = row[0] + 1
    maxr = row[1]
    with outbox_cursor(commit=True) as cur:
        if retry >= maxr:
            cur.execute("UPDATE outbox SET status='dead', last_error=?, completed_at=? WHERE msg_id=?", (error, datetime.now().isoformat(), msg_id))
        else:
            delay = 4 ** (retry - 1)
            next_at = (datetime.now() + timedelta(seconds=delay)).isoformat()
            cur.execute("UPDATE outbox SET retry_count=?, next_retry_at=?, last_error=? WHERE msg_id=?", (retry, next_at, error, msg_id))


def get_pending_count():
    with outbox_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM outbox WHERE status IN ('pending','sending')")
        return cur.fetchone()[0]





