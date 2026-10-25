import json
import re
import uuid
import datetime
from core.db import get_db

def _row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    # 将 verified 字段转为布尔
    if "verified" in d:
        d["verified"] = bool(d["verified"])
    if d.get("test_cases"):
        try:
            d["test_cases"] = json.loads(d["test_cases"])
        except:
            d["test_cases"] = []
    else:
        d["test_cases"] = []
    return d

def load_kb():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM kb_entries ORDER BY timestamp ASC").fetchall()
        return [_row_to_dict(row) for row in rows]

def save_kb(entries):
    """全量保存（已弃用，保留空实现避免调用错误）"""
    print("警告：save_kb 已弃用，请使用 add_to_kb 逐个添加")

def add_to_kb(task, branch_a, branch_b, synthesis, model_id="unknown", user_id="system", backtrack_count=0, test_cases=None):
    entry_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO kb_entries (id, task, branch_a, branch_b, solution, verified, model_id, user_id, timestamp, backtrack_count, test_cases)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (
            entry_id, task, branch_a, branch_b, synthesis, model_id, user_id, timestamp, backtrack_count,
            json.dumps(test_cases) if test_cases is not None else None
        ))

def tokenize(text):
    return re.findall(r"\w+", text.lower())

def load_shared_ids():
    with get_db() as conn:
        rows = conn.execute("SELECT kb_id FROM shared_pollinate_log").fetchall()
        return {row["kb_id"] for row in rows}

def add_shared_id(kb_id):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO shared_pollinate_log (kb_id, timestamp) VALUES (?, ?)",
                     (kb_id, datetime.datetime.now(datetime.timezone.utc).isoformat()))

def find_pending_pollinate(user_id):
    kb = load_kb()
    shared_ids = load_shared_ids()
    for entry in reversed(kb):
        if entry.get("model_id") != "manual_pollinate":
            continue
        if entry.get("id") not in shared_ids and entry.get("user_id") == user_id:
            return entry
    return None
