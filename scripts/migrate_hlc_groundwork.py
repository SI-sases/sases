# scripts/migrate_hlc_groundwork.py
"""
B2 地基迁移脚本 v2 —— 一次性为 12 张表加 HLC 相关字段

v2 修复：用 rowid 代替 id，自动检测时间列

字段：
  - hlc_ts TEXT
  - origin_node TEXT
  - shard_key TEXT DEFAULT ''

幂等：可重复执行
事务：一个事务内完成，失败自动回滚
"""
import os
import sys
import sqlite3
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "users.db")

TABLES = [
    "conversations",
    "group_members",
    "group_messages",
    "groups",
    "interaction_patterns",
    "knowledge_base",
    "messages",
    "project_docs",
    "safety_memory",
    "space_nodes",
    "task_feedback",
    "users",
]

DEFAULT_NODE = "n000"

# 可能的时间列名
TIME_COLUMNS = ["created_at", "updated_at", "imported_at", "last_hit_at", "timestamp", "refreshed_at"]


def _iso_to_hlc(created_at_str):
    """ISO 时间字符串 → HLC 格式：{13位毫秒}.{6位补零}.{节点ID}"""
    if not created_at_str:
        return f"{0:013d}.{0:06d}.{DEFAULT_NODE}"
    try:
        s = str(created_at_str).strip().replace("Z", "").replace(" ", "T")
        if "." in s:
            s = s.split(".")[0]
        dt = datetime.fromisoformat(s)
        ts_ms = int(dt.timestamp() * 1000)
        return f"{ts_ms:013d}.{0:06d}.{DEFAULT_NODE}"
    except Exception:
        return f"{0:013d}.{0:06d}.{DEFAULT_NODE}"


def _table_exists(cur, table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _table_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _index_exists(cur, index_name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cur.fetchone() is not None


def _detect_time_column(cols):
    """从列清单里找时间列"""
    for candidate in TIME_COLUMNS:
        if candidate in cols:
            return candidate
    return None


def migrate():
    print(f"[migrate] 目标数据库: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"[migrate] 错误：数据库不存在")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    stats = {
        "tables_processed": 0,
        "tables_skipped": 0,
        "columns_added": 0,
        "rows_backfilled": 0,
        "indexes_created": 0,
    }

    try:
        conn.execute("BEGIN")

        for table in TABLES:
            if not _table_exists(cur, table):
                print(f"[migrate] {table}: 表不存在，跳过")
                stats["tables_skipped"] += 1
                continue

            print(f"\n[migrate] 处理表: {table}")
            cols = _table_columns(cur, table)

            # 1. 加字段
            for col, col_def in [
                ("hlc_ts", "TEXT"),
                ("origin_node", "TEXT"),
                ("shard_key", "TEXT DEFAULT ''"),
            ]:
                if col in cols:
                    print(f"  - 字段 {col}: 已存在，跳过")
                else:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                    stats["columns_added"] += 1
                    print(f"  - 字段 {col}: 已添加")
                    cols.append(col)  # 更新列清单

            # 2. 回填（用 rowid）
            time_col = _detect_time_column(cols)
            print(f"  - 时间列: {time_col or '(无，用当前时间)'}")

            # 读所有需要回填的行（用 rowid 作为唯一标识）
            # 注意：rowid 必须用别名，否则 sqlite3.Row 无法通过 key 访问
            select_cols = "rowid AS _rowid, hlc_ts, origin_node, shard_key"
            if time_col:
                select_cols += f", {time_col}"
            cur.execute(f"SELECT {select_cols} FROM {table}")
            rows = cur.fetchall()

            now_hlc = _iso_to_hlc(datetime.now().isoformat())
            backfill_count = 0

            for row in rows:
                rowid = row["_rowid"]
                need_update = False
                updates = {}

                if row["hlc_ts"] is None:
                    if time_col and row[time_col]:
                        updates["hlc_ts"] = _iso_to_hlc(row[time_col])
                    else:
                        updates["hlc_ts"] = now_hlc
                    need_update = True
                if row["origin_node"] is None:
                    updates["origin_node"] = DEFAULT_NODE
                    need_update = True
                if row["shard_key"] is None:
                    updates["shard_key"] = ""
                    need_update = True

                if need_update:
                    set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
                    cur.execute(f"UPDATE {table} SET {set_clause} WHERE rowid=?", list(updates.values()) + [rowid])
                    backfill_count += 1

            if backfill_count:
                stats["rows_backfilled"] += backfill_count
                print(f"  - 回填: {backfill_count} 条")
            else:
                print(f"  - 回填: 无需回填")

            # 3. 索引
            idx_hlc = f"idx_{table}_hlc"
            idx_shard = f"idx_{table}_shard"
            if not _index_exists(cur, idx_hlc):
                cur.execute(f"CREATE INDEX {idx_hlc} ON {table}(hlc_ts)")
                stats["indexes_created"] += 1
                print(f"  - 索引 {idx_hlc}: 已创建")
            else:
                print(f"  - 索引 {idx_hlc}: 已存在")
            if not _index_exists(cur, idx_shard):
                cur.execute(f"CREATE INDEX {idx_shard} ON {table}(shard_key)")
                stats["indexes_created"] += 1
                print(f"  - 索引 {idx_shard}: 已创建")
            else:
                print(f"  - 索引 {idx_shard}: 已存在")

            stats["tables_processed"] += 1

        conn.commit()
        print(f"\n[migrate] ✅ 迁移完成")
        print(f"  - 处理表: {stats['tables_processed']}")
        print(f"  - 跳过表: {stats['tables_skipped']}")
        print(f"  - 新增字段: {stats['columns_added']}")
        print(f"  - 回填行数: {stats['rows_backfilled']}")
        print(f"  - 新增索引: {stats['indexes_created']}")
        return 0

    except Exception as e:
        conn.rollback()
        print(f"\n[migrate] ❌ 迁移失败，已回滚: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(migrate())
