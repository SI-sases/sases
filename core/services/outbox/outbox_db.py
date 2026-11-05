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
