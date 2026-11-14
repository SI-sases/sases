import os
import shutil
from datetime import datetime

TARGET = "core/db.py"
MARKER = "# ===== P2.6: 定时任务表 ====="

SQL_BLOCK = '''
        # ===== P2.6: 定时任务表 =====
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cron_expr TEXT NOT NULL,
                timezone TEXT DEFAULT 'Asia/Shanghai',
                task_template TEXT NOT NULL,
                task_params TEXT,
                enabled INTEGER DEFAULT 1,
                missed_policy TEXT DEFAULT 'catch_up',
                failure_count INTEGER DEFAULT 0,
                paused_reason TEXT,
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sched_due ON scheduled_tasks(enabled, next_run_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sched_user ON scheduled_tasks(user_id, enabled)")
        print("[db] scheduled_tasks 表就绪")
        # ===== P2.6 end =====
'''

def main():
    if not os.path.exists(TARGET):
        print("no file")
        return
    content = open(TARGET, "r", encoding="utf-8").read()
    if MARKER in content:
        print("already patched")
        return
    anchor = "if __name__ == '__main__':"
    if anchor not in content:
        print("no anchor")
        return
    backup = TARGET + ".bak_p2_6_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, backup)
    print("backup:", backup)
    idx = content.rfind(anchor)
    new_content = content[:idx] + SQL_BLOCK + "\n" + content[idx:]
    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched:", TARGET)

if __name__ == "__main__":
    main()