from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from core.api_routes import auth_routes, seed_routes, credit_routes, harness_routes, agi_routes, space_routes
from core.space_service import space_service
from core import config
from core.discovery import NodeDiscovery

# mDNS 发现服务（延迟创建，确保可配置）
discovery = NodeDiscovery(on_peer_discovered=lambda peer_url: space_service.sync_from_peer(peer_url))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动后台线程
    space_service.start_auto_sync(interval=300)
    space_service.start_health_check(interval=60)
    # 如果启用了 mDNS，启动发现服务
    if config.ENABLE_MDNS:
        discovery.start()
    yield
    # 停止后台任务
    if config.ENABLE_MDNS:
        discovery.stop()
    space_service.stop_auto_sync()
    space_service.stop_health_check()

def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(title="SASES Full Web Service", version="0.12.0", lifespan=lifespan)

    # 挂载静态文件
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # 注册路由
    app.include_router(auth_routes.router)
    app.include_router(seed_routes.router)
    app.include_router(credit_routes.router)
    app.include_router(harness_routes.router)
    app.include_router(agi_routes.router)
    app.include_router(space_routes.router)

    @app.get("/")
    async def root():
        return {"message": "SASES Full Web Service is running. Visit /static/index.html for UI."}

    return app
