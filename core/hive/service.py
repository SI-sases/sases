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
    from core.hive.anchor import periodic_anchor_task
    from core.hive.heartbeat import heartbeat_check
    from core.hive.majority import majority_vote_check
    from core.hive.sync import periodic_sync_task

    tasks = [
        asyncio.create_task(periodic_anchor_task()),
        asyncio.create_task(heartbeat_check()),
        asyncio.create_task(majority_vote_check()),
    ]
    if HIVE_ROLE == "slave":
        tasks.append(asyncio.create_task(periodic_sync_task()))
    return tasks