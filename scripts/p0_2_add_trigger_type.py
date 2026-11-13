# scripts/p0_2_add_trigger_type.py
import sqlite3

DB = "users.db"

def ensure_column(cur, table, column, definition):
    cur.execute("PRAGMA table_info(" + table + ")")
    cols = [r[1] for r in cur.fetchall()]
    if column not in cols:
        cur.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition)
        print("added: " + table + "." + column)
        return True
    print("exists: " + table + "." + column)
    return False

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    ensure_column(cur, "supervisor_runs", "trigger_type", "TEXT DEFAULT 'user'")
    ensure_column(cur, "supervisor_runs", "trigger_task_id", "TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_trigger ON supervisor_runs(trigger_type, trigger_task_id)")
    print("index: idx_runs_trigger")

    conn.commit()

    # 验证
    cur.execute("PRAGMA table_info(supervisor_runs)")
    cols = [r[1] for r in cur.fetchall()]
    print("")
    print("current columns: " + ", ".join(cols))

    cur.execute("SELECT trigger_type, COUNT(*) FROM supervisor_runs GROUP BY trigger_type")
    print("")
    print("trigger_type distribution:")
    for row in cur.fetchall():
        print("  " + str(row[0]) + ": " + str(row[1]))

    conn.close()
    print("")
    print("done")

if __name__ == "__main__":
    main()