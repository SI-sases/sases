import os
import sqlite3
from contextlib import contextmanager

OUTBOX_DB_PATH = os.environ.get("SASES_OUTBOX_DB_PATH") or os.path.join(os.getcwd(), "outbox.db")


@contextmanager
def outbox_cursor(commit=False):
    conn = sqlite3.connect(OUTBOX_DB_PATH, timeout=10)
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    finally:
        cur.close()
        conn.close()


def ensure_outbox_table():
    with outbox_cursor(commit=True) as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT UNIQUE NOT NULL, target_url TEXT NOT NULL, payload TEXT NOT NULL, headers TEXT, status TEXT NOT NULL DEFAULT 'pending', retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 5, next_retry_at TEXT NOT NULL, last_error TEXT, created_at TEXT NOT NULL, completed_at TEXT)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_due ON outbox(status, next_retry_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_msg ON outbox(msg_id)")

