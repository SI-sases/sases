"""core/hive/standalone.py —— 轻量节点独立入口。

用法（slave 模式）：
    set HIVE_ROLE=slave
    set SASES_PORT=9001
    set SASES_NODE_ID=node-01
    set HIVE_MASTER=http://127.0.0.1:8001
    python -m core.hive.standalone
"""
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


def _prepare_lite_env(node_id):
    os.environ.setdefault("HIVE_ROLE", "slave")
    os.environ.setdefault("ENABLE_HIVE", "true")
    node_dir = os.path.join("hive-nodes", node_id)
    os.makedirs(node_dir, exist_ok=True)
    db_path = os.path.join(node_dir, "hive.db")
    os.environ["SASES_DB_PATH"] = db_path
    return db_path


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from core.hive.service import start_background_tasks
    tasks = start_background_tasks()
    yield
    for t in tasks:
        t.cancel()


def create_lite_app():
    from core.db import init_db
    init_db()

    from core.hive.api import router
    app = FastAPI(title="SASES Hive Lite", version="0.1.0", lifespan=_lifespan)
    app.include_router(router)
    return app


def main():
    port = int(os.environ.get("SASES_PORT", "9001"))
    node_id = os.environ.get("SASES_NODE_ID", "node-01")
    db_path = _prepare_lite_env(node_id)
    print(f"[hive-lite] {node_id} on port {port}, db={db_path}")
    app = create_lite_app()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()