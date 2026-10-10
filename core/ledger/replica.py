"""core/hive/replica.py —— 只读副本同步。

副本模式（REPLICA_MODE=true）：
  - 中间件拦截写操作
  - 定期从主节点拉取核心业务表
"""
import asyncio

from core.node.client import hive_headers
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


async def do_one_sync():
    """单次同步核心表。返回 (success: bool, total_rows: int)。"""
    if HIVE_ROLE != "slave" or not HIVE_MASTERS:
        return False, 0
    import httpx

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
            return True, total
        return False, 0
    except Exception as e:
        print(f"[replica] do_one_sync error: {e}")
        return False, 0



async def sync_replica_from_master():
    """副本节点：从主节点拉取核心表。"""
    if HIVE_ROLE != "slave" or not HIVE_MASTERS:
        return
    import httpx

    consecutive_fails = 0
    await asyncio.sleep(15)
    while True:
        ok, total = await do_one_sync()
        if ok:
            print(f"[replica] synced {total} rows from master")
            consecutive_fails = 0
        else:
            consecutive_fails += 1
            print(f"[replica] no data from master (fails={consecutive_fails})")
            # 连续失败 3 次后，尝试从 registry 重新找 master
            if consecutive_fails >= 3:
                await _refresh_master_from_registry()
        backoff = min(SYNC_INTERVAL * (2 ** min(consecutive_fails, 4)), 600)
        await asyncio.sleep(backoff)


async def _refresh_master_from_registry():
    """从 node_registry 查找活跃 master，更新 HIVE_MASTERS。"""
    try:
        from core.node.registry import list_nodes
        import core.hive.config as _cfg
        nodes = list_nodes()
        masters = [n for n in nodes if n.get('role') == 'master' and n.get('status') == 'active']
        new_masters = [m['url'] for m in masters if m.get('url')]
        # 排除自己
        import os
        my_port = os.environ.get('SASES_PORT', '8001')
        new_masters = [u for u in new_masters if f':{my_port}' not in u]
        if new_masters and new_masters != _cfg.HIVE_MASTERS:
            print(f"[replica] switching masters: {_cfg.HIVE_MASTERS} -> {new_masters}")
            _cfg.HIVE_MASTERS = new_masters
    except Exception as e:
        print(f"[replica] refresh master failed: {e}")
