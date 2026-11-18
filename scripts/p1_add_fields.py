# scripts\p1_add_fields.py
import sqlite3
conn = sqlite3.connect("users.db")
cur = conn.cursor()

def add(table, col, typ):
    cur.execute("PRAGMA table_info(" + table + ")")
    cols = [r[1] for r in cur.fetchall()]
    if col in cols:
        print("[SKIP] " + table + "." + col)
        return
    cur.execute("ALTER TABLE " + table + " ADD COLUMN " + col + " " + typ)
    print("[ADD] " + table + "." + col)

add("conversations", "active_task_id", "TEXT")
add("conversations", "active_task_status", "TEXT DEFAULT 'idle'")
add("conversations", "active_task_snapshot", "TEXT")
add("supervisor_runs", "task_fingerprint", "TEXT")

conn.commit()
conn.close()
print("[OK] 字段添加完成")
