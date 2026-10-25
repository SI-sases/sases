"""standalone_master.py —— 轻量主节点入口。

功能：
  - 只跑 hive 模块（不跑完整 SASES 业务）
  - 从权威主节点（HIVE_AUTHORITY）同步官方账本
  - 对外提供 /hive/anchor /hive/ledger /hive/hash

用法：
    set HIVE_ROLE=master
    set SASES_PORT=8002
    set SASES_NODE_ID=node-B
    set HIVE_AUTHORITY=http://127.0.0.1:8001
    python -m core.hive.standalone_master
"""
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


def _prepare_env(node_id):
    os.environ.setdefault('HIVE_ROLE', 'master')
    os.environ.setdefault('ENABLE_HIVE', 'true')
    os.environ['SASES_DISABLE_FK'] = 'true'
    node_dir = os.path.join('hive-nodes', node_id)
    os.makedirs(node_dir, exist_ok=True)
    db_path = os.path.join(node_dir, 'hive.db')
    os.environ['SASES_DB_PATH'] = db_path
    return db_path


@asynccontextmanager
async def _lifespan(app: FastAPI):
    import asyncio
    from core.ledger.anchor import periodic_anchor_task
    from core.node.heartbeat import heartbeat_check
    from core.node.majority import majority_vote_check
    from core.ledger.sync import sync_from_authority
    from core.node.register_client import periodic_register_task

    tasks = [
        asyncio.create_task(periodic_anchor_task()),
        asyncio.create_task(heartbeat_check()),
        asyncio.create_task(majority_vote_check()),
        asyncio.create_task(periodic_register_task()),
    ]
    authority = os.environ.get('HIVE_AUTHORITY', '')
    if authority:
        tasks.append(asyncio.create_task(sync_from_authority(authority)))
    yield
    for t in tasks:
        t.cancel()


def create_app():
    from core.db import init_db
    init_db()
    from core.hive.api import router
    app = FastAPI(title='SASES Hive Master Lite', version='0.1.0', lifespan=_lifespan)
    app.include_router(router)
    return app


def main():
    port = int(os.environ.get('SASES_PORT', '8002'))
    node_id = os.environ.get('SASES_NODE_ID', 'node-B')
    db_path = _prepare_env(node_id)
    authority = os.environ.get('HIVE_AUTHORITY', '')
    print(f'[hive-master] {node_id} on :{port}, db={db_path}, authority={authority or "none"}')
    app = create_app()
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')


if __name__ == '__main__':
    main()
