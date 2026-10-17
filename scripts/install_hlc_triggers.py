# scripts/install_hlc_triggers.py
"""
为 12 张表安装 HLC 触发器。
AFTER INSERT 时，如果 hlc_ts IS NULL，自动填充：
  - hlc_ts = 当前毫秒时间戳.000000.n001
  - origin_node = 'n001'

幂等：重复执行不报错。
"""
import os
import sqlite3

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "users.db")
NODE_ID = "n001"

TABLES = [
    "conversations", "group_members", "group_messages", "groups",
    "interaction_patterns", "knowledge_base", "messages",
    "project_docs", "safety_memory", "space_nodes",
    "task_feedback", "users",
]

# SQLite 计算当前毫秒：julianday → Unix 天数 → 毫秒
HLC_EXPR = (
    "printf('%013d.%06d.%s', "
    "CAST((julianday('now') - 2440587.5) * 86400000 AS INTEGER), "
    "0, "
    f"'{NODE_ID}')"
)

def install():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    installed = 0
    try:
        for table in TABLES:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cur.fetchone():
                print(f"[trigger] {table}: 表不存在，跳过")
                continue

            trigger_name = f"trg_{table}_hlc"
            cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name=?", (trigger_name,))
            if cur.fetchone():
                print(f"[trigger] {table}: 触发器已存在，跳过")
                continue

            cur.execute(f"""
                CREATE TRIGGER {trigger_name}
                AFTER INSERT ON {table}
                WHEN NEW.hlc_ts IS NULL
                BEGIN
                    UPDATE {table} SET
                        hlc_ts = {HLC_EXPR},
                        origin_node = '{NODE_ID}'
                    WHERE rowid = NEW.rowid;
                END;
            """)
            installed += 1
            print(f"[trigger] {table}: 触发器已创建")
        conn.commit()
        print(f"\n[trigger] ✅ 完成，新建 {installed} 个触发器")
    except Exception as e:
        conn.rollback()
        print(f"[trigger] ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    return 0

def verify():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_%_hlc'")
    triggers = [r[0] for r in cur.fetchall()]
    print(f"[trigger] 已安装 {len(triggers)} 个触发器")
    for t in triggers:
        print(f"  - {t}")
    conn.close()

if __name__ == "__main__":
    import sys
    sys.exit(install())
