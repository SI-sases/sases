# core/bootstrap.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
import asyncio

from .db import init_db, db_cursor
from .services import memory_service
from .services import debug_service
from .services import rescue_service
from .services import swarm_service
from .services import supervisor_service
from .services import executor_service
from .services import cleanup_service
from .services import pattern_service
from .services import pattern_service
from . import backup_service
from .api_routes import (
    ws_routes,
    supervisor_routes,
    upload_routes,
    auth_routes,
    seed_routes,
    credit_routes,
    harness_routes,
    agi_routes,
    space_routes,
    group_routes,
    model_routes,
    agent_routes,
    chat_routes,
    message_routes,
    knowledge_routes,
    stats_routes,
    search_routes,
    hive_routes,
    ai_circle_routes,
    export_routes,
    market_routes,
    wisdom_space_routes,
    transfer_routes,
    user_routes,
    memory_routes,
    work_routes,
    pollination_routes,
    commander_routes,
    quality_routes,
    rescue_routes,
    pet_routes,
    base_routes,
    backup_routes,
    onboarding_routes,
    compute_routes,
    yunchong_routes,
    swarm_routes,
    hive_task_routes,
)


async def periodic_summary_task():
    while True:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT id FROM users")
                user_ids = [row["id"] for row in cur.fetchall()]

            for uid in user_ids:
                try:
                    memory_service.summarize_work_logs(uid, hours=6)
                except Exception as e:
                    print(f"用户 {uid} 定期总结失败: {e}")
        except Exception as e:
            print(f"定期总结任务异常: {e}")

        await asyncio.sleep(6 * 3600)




async def periodic_git_push():
    """每小时把本地提交推送到 GitHub"""
    import subprocess
    import os as _os
    await asyncio.sleep(300)
    repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    while True:
        try:
            r = subprocess.run(
                "git push origin main",
                shell=True, cwd=repo, capture_output=True,
                encoding="utf-8", errors="replace", timeout=120
            )
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                if "Everything up-to-date" in out:
                    print("[git-push] 无新提交")
                else:
                    print(f"[git-push] 推送成功: {out.strip()[:200]}")
            else:
                print(f"[git-push] 推送失败: {out.strip()[:200]}")
        except Exception as e:
            print(f"[git-push] 异常: {e}")
        await asyncio.sleep(3600)



async def periodic_pattern_finalize():
    """每小时检查一次，把 24 小时前的 tentative pattern 转为 active"""
    while True:
        try:
            activated = pattern_service.finalize_patterns(hours=24)
            if activated:
                print(f"[pattern] finalize: {activated} 条转为 active")
        except Exception as e:
            print(f"[pattern] finalize 异常: {e}")
        await asyncio.sleep(3600)



async def periodic_syntax_check():
    """每 10 分钟检查 core/ 下 .py 语法，发现错误就告警"""
    import ast as _ast
    import os as _os
    await asyncio.sleep(60)
    while True:
        try:
            _bad = []
            for _root, _dirs, _files in _os.walk('core'):
                _dirs[:] = [d for d in _dirs if d not in ('__pycache__',)]
                for _f in _files:
                    if not _f.endswith('.py'):
                        continue
                    _fp = _os.path.join(_root, _f)
                    try:
                        with open(_fp, 'r', encoding='utf-8') as _fh:
                            _ast.parse(_fh.read())
                    except SyntaxError as _se:
                        _bad.append(_fp + ' (line ' + str(_se.lineno) + ')')
                    except Exception:
                        pass
            if _bad:
                print('[syntax-check] 发现语法错误: ' + ' | '.join(_bad))
                print('[syntax-check] 建议: 运行 git log 查看最近提交，必要时 git reset --hard HEAD~N 回滚')
        except Exception as _e:
            print('[syntax-check] 异常: ' + str(_e))
        await asyncio.sleep(600)



async def periodic_rescue_maintenance():
    """每 5 分钟回收超时任务"""
    while True:
        try:
            reclaim_result = await asyncio.to_thread(rescue_service.reclaim_expired_tasks, 30)
            if reclaim_result.get("reclaimed", 0) > 0:
                print(f"[解救任务] 回收超时任务 {reclaim_result['reclaimed']} 个")
        except Exception as e:
            print(f"[解救任务] 维护异常: {e}")

        await asyncio.sleep(5 * 60)


async def periodic_airdrop():
    """每天 0:30 执行空投"""
    from .services import airdrop_service
    while True:
        try:
            from datetime import datetime, timedelta
            dt = datetime.utcnow()
            next_run = dt.replace(hour=0, minute=30, second=0, microsecond=0)
            if next_run <= dt:
                next_run += timedelta(days=1)
            wait_sec = (next_run - dt).total_seconds()
            print(f'[airdrop] next run in {int(wait_sec)}s')
            await asyncio.sleep(wait_sec)
            result = await asyncio.to_thread(airdrop_service.run_daily_airdrop)
            print(f'[airdrop] {result}')
        except Exception as e:
            print(f'[airdrop] error: {e}')
            await asyncio.sleep(3600)


async def periodic_task_repush():
    """每小时重播超过 12 小时未完成的任务"""
    from .services import group_task_service
    while True:
        try:
            await asyncio.sleep(3600)
            repushed = await asyncio.to_thread(group_task_service.repush_pending_tasks, 12)
            if repushed:
                print(f'[task-repush] 重播 {len(repushed)} 个任务: {repushed}')
        except Exception as e:
            print(f'[task-repush] error: {e}')
            await asyncio.sleep(3600)


async def periodic_group_red_packet():
    """每分钟检查群红包时间，到点自动发群福利手气红包"""
    from .services import group_red_packet_service
    from .db import db_cursor
    from datetime import datetime
    while True:
        try:
            now = datetime.utcnow()
            today = now.strftime('%Y-%m-%d')
            cur_hour = now.hour
            with db_cursor() as cur:
                cur.execute(
                    "SELECT id, owner_id, credits, staked_credits, red_packet_hour, last_red_packet_date FROM groups WHERE red_packet_hour=? AND (last_red_packet_date IS NULL OR last_red_packet_date != ?) AND (COALESCE(credits, 0) + COALESCE(staked_credits, 0)) >= 1000",
                    (cur_hour, today)
                )
                rows = cur.fetchall()
            for g in rows:
                try:
                    amount = round((g['credits'] or 0) * 0.1, 2)
                    if amount < 1:
                        amount = 1.0
                    if amount > (g['credits'] or 0):
                        amount = g['credits']
                    ok, res = group_red_packet_service.create_packet(
                        g['id'], g['owner_id'], amount, 5,
                        message='每日群福利', source_type='group_pool', packet_type='lucky'
                    )
                    if ok:
                        with db_cursor(commit=True) as cur:
                            cur.execute('UPDATE groups SET last_red_packet_date=? WHERE id=?', (today, g['id']))
                        print(f'[group-rp] group {g["id"]} sent {amount}')
                        # WS 广播
                        try:
                            import json as _json_g
                            from .api_routes.ws_routes import broadcast_to_group as _bcg
                            with db_cursor() as _cg:
                                _cg.execute('SELECT global_group_id FROM groups WHERE id=?', (g['id'],))
                                _rg = _cg.fetchone()
                            if _rg and _rg['global_group_id']:
                                _payload = _json_g.dumps({
                                    'packet_id': res.get('packet_id') if isinstance(res, dict) else None,
                                    'sender_id': g['owner_id'],
                                    'total_amount': amount,
                                    'total_count': 5,
                                    'message': '每日群福利',
                                    'source_type': 'group_pool',
                                    'packet_type': 'lucky'
                                }, ensure_ascii=False)
                                await _bcg(_rg['global_group_id'], {
                                    'type': 'message',
                                    'content': '[RED_PACKET]:' + _payload,
                                    'sender_id': None,
                                    'sender_agent_id': None,
                                    'sender_name': '系统'
                                })
                        except Exception as _bge:
                            print(f'[group-rp] ws broadcast failed: {_bge}')
                except Exception as e:
                    print(f'[group-rp] failed group {g["id"]}: {e}')
        except Exception as e:
            print(f'[group-rp] error: {e}')
        await asyncio.sleep(60)


async def periodic_red_packet_expire():
    """每小时检查过期红包并退款"""
    from .services import group_red_packet_service
    while True:
        try:
            await asyncio.sleep(3600)
            expired = await asyncio.to_thread(group_red_packet_service.expire_packets)
            if expired:
                print(f'[rp-expire] 退回 {len(expired)} 个过期红包: {expired}')
        except Exception as e:
            print(f'[rp-expire] error: {e}')
            await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(supervisor_service.resume_restart_pending_runs())
    init_db()

    # 启动时清理中断的 run 和任务（v0.18.0）
    try:
        from .db import db_cursor as _dbc
        with _dbc(commit=True) as _c:
            _c.execute("UPDATE supervisor_runs SET status='interrupted', finished_at=datetime('now') WHERE status='running' AND (created_at IS NULL OR created_at < datetime('now', '-30 minutes'))")
            _r1 = _c.rowcount
            _c.execute("UPDATE swarm_pending_tasks SET status='interrupted' WHERE status IN ('pending', 'running') AND created_at < datetime('now', '-30 minutes')")
            _r2 = _c.rowcount
        if _r1 or _r2:
            print(f"[bootstrap] 清理中断状态: runs={_r1}, tasks={_r2}")
    except Exception as _e:
        print(f"[bootstrap] 清理中断状态失败: {_e}")


    try:
        backup_result = backup_service.create_backup()
        if backup_result["success"]:
            print(f"[备份] 启动备份成功: {backup_result['filename']}")
    except Exception as e:
        print(f"[备份] 启动备份异常: {e}")

    from .services import state_service as _state_svc

    # 蜂巢模块（环境变量控制）
    try:
        from core.hive.service import register_routes as _hive_register
        _hive_register(app)
    except Exception as _hive_e:
        print(f'[hive] register failed: {_hive_e}')

    # 分组启动所有后台任务
    _background_tasks = []

    # 【秒级】
    _background_tasks.append(asyncio.create_task(executor_service.start_background_executor()))
    _background_tasks.append(asyncio.create_task(periodic_syntax_check()))

    # 【分钟级】
    _background_tasks.append(asyncio.create_task(periodic_rescue_maintenance()))
    _background_tasks.append(asyncio.create_task(periodic_group_red_packet()))
    _background_tasks.append(asyncio.create_task(periodic_red_packet_expire()))

    # 【小时级】
    _background_tasks.append(asyncio.create_task(periodic_summary_task()))
    _background_tasks.append(asyncio.create_task(debug_service.periodic_debug_scan(interval_hours=6, sample_limit=20)))
    _background_tasks.append(asyncio.create_task(periodic_pattern_finalize()))
    _background_tasks.append(asyncio.create_task(periodic_git_push()))
    _background_tasks.append(asyncio.create_task(periodic_task_repush()))
    # 【日级】
    _background_tasks.append(asyncio.create_task(backup_service.periodic_backup_task()))
    _background_tasks.append(asyncio.create_task(cleanup_service.periodic_cleanup(interval_hours=24)))
    _background_tasks.append(asyncio.create_task(_state_svc.periodic_state_sync(interval_hours=24)))
    _background_tasks.append(asyncio.create_task(periodic_airdrop()))


    # 【hive 蜂巢任务】
    try:
        from core.hive.service import start_background_tasks as _hive_tasks
        _background_tasks.extend(_hive_tasks())
    except Exception as _hive_e:
        print(f'[hive] tasks failed: {_hive_e}')

    print(f"[bootstrap] 已启动 {len(_background_tasks)} 个后台任务")


    async def _periodic_restart_watch():
        import os as _os_w
        _root = _os_w.path.dirname(_os_w.path.dirname(_os_w.path.abspath(__file__)))
        _fp = _os_w.path.join(_root, 'restart_signal.txt')
        await asyncio.sleep(5)
        while True:
            try:
                if _os_w.path.exists(_fp):
                    print('[bootstrap] restart_signal detected, exiting for wrapper to restart')
                    _os_w._exit(0)
            except Exception as _e_w:
                print('[bootstrap] restart watch err: ' + str(_e_w))
            await asyncio.sleep(3)

    _restart_watch_task = asyncio.create_task(_periodic_restart_watch())


    yield

    summary_task.cancel()
    debug_task.cancel()
    rescue_task.cancel()
    backup_task.cancel()
    executor_task.cancel()
    cleanup_task.cancel()
    _state_task.cancel()

    if '_restart_watch_task' in dir():
        _restart_watch_task.cancel()
    pattern_task.cancel()
    git_push_task.cancel()
    syntax_check_task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="SASES", version="0.15.4", lifespan=lifespan)

    # 统一错误返回格式（兼容 error / message 两种前端读取方式）
    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={'error': exc.detail, 'message': exc.detail, 'code': exc.status_code},
        )

    @app.exception_handler(Exception)
    async def _global_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={'error': str(exc), 'message': str(exc), 'code': 500},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _replica_read_only_middleware(request, call_next):
        """副本拦截 + 主节点验签。"""
        from core.hive.config import REPLICA_MODE, FORWARD_MODE, HIVE_ROLE
        from fastapi.responses import JSONResponse

        # ========== 主节点：转发请求验证 ==========
        if HIVE_ROLE == "master" and request.headers.get("X-Hive-Forwarded") == "true":
            from core.hive.forwarder import verify_forward_signature, check_and_record_request
            ok, err = verify_forward_signature(request.headers)
            if not ok:
                return JSONResponse({"error": "forward verification failed", "reason": err}, status_code=401)
            request_id = request.headers.get("X-Hive-Request-Id")
            node_id = request.headers.get("X-Hive-From-Node")
            if request_id and check_and_record_request(request_id, node_id):
                return JSONResponse({"error": "duplicate request"}, status_code=409)
            return await call_next(request)

        # ========== 副本：拦截写操作并转发 ==========
        if not REPLICA_MODE:
            return await call_next(request)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            path = request.url.path
            if not (path.startswith("/token")
                    or path.startswith("/auth")
                    or path.startswith("/hive")):
                if FORWARD_MODE == "auto":
                    from core.hive.forwarder import forward_request
                    body = await request.body()
                    status, resp = await forward_request(
                        request.method, path, body,
                        dict(request.headers), request.url.query
                    )
                    if status is not None:
                        return JSONResponse(resp, status_code=status)
                return JSONResponse(
                    {"error": "read-only replica",
                     "message": "本节点为只读副本，写操作请到主节点",
                     "code": 403},
                    status_code=403,
                )
        return await call_next(request)

    app.include_router(auth_routes.router)
    app.include_router(seed_routes.router)
    app.include_router(credit_routes.router)
    app.include_router(harness_routes.router)
    app.include_router(agi_routes.router)
    app.include_router(space_routes.router)
    app.include_router(group_routes.router)
    app.include_router(model_routes.router)
    app.include_router(agent_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(message_routes.router)
    app.include_router(knowledge_routes.router)
    app.include_router(stats_routes.router)
    app.include_router(search_routes.router)
    app.include_router(ai_circle_routes.router)
    app.include_router(export_routes.router)
    app.include_router(market_routes.router)
    app.include_router(wisdom_space_routes.router)
    app.include_router(transfer_routes.router)
    app.include_router(user_routes.router)
    app.include_router(memory_routes.router)
    app.include_router(work_routes.router)
    app.include_router(pollination_routes.router)
    app.include_router(commander_routes.router)
    app.include_router(quality_routes.router)
    app.include_router(rescue_routes.router)
    app.include_router(pet_routes.router)
    app.include_router(base_routes.router)
    app.include_router(backup_routes.router)
    app.include_router(onboarding_routes.router)
    app.include_router(compute_routes.router)
    app.include_router(yunchong_routes.router)
    app.include_router(swarm_routes.router)
    app.include_router(upload_routes.router)
    app.include_router(supervisor_routes.router)
    app.include_router(hive_routes.router)
    app.include_router(ws_routes.router)
    app.include_router(hive_task_routes.router)

    @app.get("/static/index.html", response_class=HTMLResponse)
    async def serve_index():
        return FileResponse("static/index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory="static"), name="static")
    import os as _os
    _os.makedirs('uploads', exist_ok=True)
    app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')
    import os as _os
    _os.makedirs('uploads', exist_ok=True)
    app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')

    @app.get("/")
    async def index():
        return FileResponse("static/index.html", media_type="text/html")

    @app.get("/favicon.ico")
    async def favicon():
        return FileResponse("static/favicon.svg", media_type="image/svg+xml")

    return app
