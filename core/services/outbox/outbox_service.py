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
