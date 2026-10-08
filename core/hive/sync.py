"""core/hive/sync.py —— 从主节点同步账本（阶段 1 单向）。

阶段 3 时扩展为双向：
  - slave 角色时：从 master 拉
  - peer 角色时：双向对比 + 合并
"""
from core.hive.client import hive_headers
import asyncio

from core.hive.config import (
    HIVE_ROLE, HIVE_MASTERS, NODE_ID, SYNC_INTERVAL,
)
from core.hive.ledger import LEDGER_TABLES


async def sync_from_master():
    """slave 模式：从主节点拉取账本，写入本地。"""
    if HIVE_ROLE != "slave" or not HIVE_MASTERS:
        return
    import httpx

    await asyncio.sleep(10)
    while True:
        try:
            ledger = {}
            async with httpx.AsyncClient(timeout=10, trust_env=False, headers=hive_headers()) as client:
                for m in HIVE_MASTERS:
                    try:
                        r = await client.get(f"{m}/hive/ledger")
                        data = r.json().get("ledger", {})
                        if data:
                            ledger = data
                            break
                    except Exception:
                        continue
        except Exception as e:
            print(f"[hive-sync] fetch failed: {e}")
            await asyncio.sleep(SYNC_INTERVAL)
            continue

        if not ledger:
            await asyncio.sleep(SYNC_INTERVAL)
            continue

        try:
            from core.db import db_cursor
            with db_cursor(commit=True) as cur:
                for table, cols in LEDGER_TABLES:
                    rows = ledger.get(table, [])
                    if not rows:
                        continue
                    # 全量替换：先删后插（数据量小，简化逻辑）
                    cur.execute(f"DELETE FROM {table}")
                    placeholders = ",".join(["?"] * len(cols))
                    col_list = ",".join(cols)
                    for row in rows:
                        cur.execute(
                            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                            tuple(row),
                        )
            print(f"[hive-sync] synced from master, {sum(len(v) for v in ledger.values())} rows")
        except Exception as e:
            print(f"[hive-sync] write failed: {e}")

        await asyncio.sleep(SYNC_INTERVAL)


async def sync_from_authority(authority_url):
    """轻量主节点专用：从权威节点同步账本（保持镜像一致）。"""
    import httpx
    from core.hive.ledger import LEDGER_TABLES
    from core.hive.config import SYNC_INTERVAL

    await asyncio.sleep(15)
    while True:
        try:
            async with httpx.AsyncClient(timeout=10, trust_env=False, headers=hive_headers()) as client:
                r = await client.get(f'{authority_url}/hive/ledger')
                ledger = r.json().get('ledger', {})
            if ledger:
                from core.db import db_cursor
                with db_cursor(commit=True) as cur:
                    for table, cols in LEDGER_TABLES:
                        rows = ledger.get(table, [])
                        if not rows:
                            continue
                        cur.execute(f'DELETE FROM {table}')
                        placeholders = ','.join(['?'] * len(cols))
                        col_list = ','.join(cols)
                        for row in rows:
                            cur.execute(
                                f'INSERT INTO {table} ({col_list}) VALUES ({placeholders})',
                                tuple(row),
                            )
                total = sum(len(v) for v in ledger.values())
                print(f'[hive-master-sync] synced from authority, {total} rows')
        except Exception as e:
            print(f'[hive-master-sync] error: {e}')
        await asyncio.sleep(SYNC_INTERVAL)



async def periodic_sync_task():
    """启动同步任务（仅 slave 生效）。"""
    if HIVE_ROLE == "slave":
        await sync_from_master()