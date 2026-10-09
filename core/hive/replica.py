"""core/hive/replica.py —— 只读副本同步。

副本模式（REPLICA_MODE=true）：
  - 中间件拦截写操作
  - 定期从主节点拉取核心业务表
"""
import asyncio

from core.hive.client import hive_headers
from core.hive.config import HIVE_ROLE, HIVE_MASTERS, SYNC_INTERVAL

# 核心业务表（B1.2-A 只同步这些）
REPLICA_TABLES = [
    "users",
    "conversations",
    "messages",
    "groups",
    "group_members",
    "group_messages",
    "pets",
    "game_resources",
    "base_facilities",
    "transactions",
    "contribution_log",
]


def export_replica():
    """主节点调用：返回核心表的全量数据。"""
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        out = {}
        for table in REPLICA_TABLES:
            try:
                cur.execute(f"SELECT * FROM {table}")
                cols = [d[0] for d in cur.description]
                rows = [list(r) for r in cur.fetchall()]
                out[table] = {"columns": cols, "rows": rows}
            except Exception as e:
                out[table] = {"columns": [], "rows": [], "error": str(e)}
        return out
    finally:
        conn.close()


def apply_replica(tables_data):
    """副本节点调用：全量覆盖本地核心表。"""
    from core.db import db_cursor
    results = {}
    with db_cursor(commit=True) as cur:
        for table, data in tables_data.items():
            cols = data.get("columns", [])
            rows = data.get("rows", [])
            if not cols:
                results[table] = 0
                continue
            try:
                cur.execute(f"PRAGMA table_info({table})")
                local_cols = [r[1] for r in cur.fetchall()]
                common = [c for c in cols if c in local_cols]
                if not common:
                    results[table] = 'no common cols'
                    continue
                col_idx = [cols.index(c) for c in common]
                cur.execute(f"DELETE FROM {table}")
                placeholders = ",".join(["?"] * len(common))
                col_list = ",".join(common)
                for row in rows:
                    vals = [row[i] for i in col_idx]
                    cur.execute(
                        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                        tuple(vals),
                    )
                results[table] = len(rows)
            except Exception as e:
                results[table] = f"error: {e}"
    return results


async def sync_replica_from_master():
    """副本节点：从主节点拉取核心表。"""
    if HIVE_ROLE != "slave" or not HIVE_MASTERS:
        return
    import httpx

    await asyncio.sleep(15)
    while True:
        try:
            data = None
            async with httpx.AsyncClient(timeout=30, trust_env=False, headers=hive_headers()) as client:
                for m in HIVE_MASTERS:
                    try:
                        r = await client.get(f"{m}/hive/replica/export")
                        if r.status_code == 200:
                            data = r.json().get("tables", {})
                            if data:
                                break
                    except Exception:
                        continue
            if data:
                results = apply_replica(data)
                total = sum(v for v in results.values() if isinstance(v, int))
                print(f"[replica] synced {total} rows from master")
            else:
                print("[replica] no data from master")
        except Exception as e:
            print(f"[replica] error: {e}")
        await asyncio.sleep(SYNC_INTERVAL)
