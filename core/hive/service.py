"""core/hive/service.py —— 挂到主应用的入口。"""
import asyncio

from core.hive.config import ENABLE_HIVE, HIVE_ROLE


def register_routes(app):
    if not ENABLE_HIVE:
        return
    from core.hive.api import router, router_public
    app.include_router(router)
    app.include_router(router_public)
    print(f"[hive] routes registered (node={__import__('core.hive.config', fromlist=['NODE_ID']).NODE_ID}, role={HIVE_ROLE})")


def start_background_tasks():
    if not ENABLE_HIVE:
        return []
    from core.ledger.anchor import periodic_anchor_task
    from core.node.heartbeat import heartbeat_check
    from core.node.majority import majority_vote_check
    from core.ledger.sync import periodic_sync_task
    from core.node.register_client import periodic_register_task
    from core.node.election import periodic_election_check
    from core.ledger.replica import sync_replica_from_master

    tasks = [
        asyncio.create_task(periodic_anchor_task()),
        asyncio.create_task(heartbeat_check()),
        asyncio.create_task(majority_vote_check()),
        asyncio.create_task(periodic_register_task()),
        asyncio.create_task(periodic_election_check()),
    ]
    if HIVE_ROLE == "slave":
        tasks.append(asyncio.create_task(periodic_sync_task()))
        from core.hive.config import REPLICA_MODE
        if REPLICA_MODE:
            tasks.append(asyncio.create_task(sync_replica_from_master()))
    return tasks
