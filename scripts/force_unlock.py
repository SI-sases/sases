import sqlite3, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(ROOT, "users.db")
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE swarm_pending_tasks SET status='cancelled' WHERE status IN ('pending', 'running')")
    cur.execute("UPDATE supervisor_runs SET status='interrupted' WHERE status IN ('running', 'pending')")
    conn.commit()
    print("OK 数据库状态已强制清空 (cancelled/interrupted)")
except Exception as e:
    print(f"FAIL 清锁失败: {e}")
