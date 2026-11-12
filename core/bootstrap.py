from core.services.outbox.outbox_worker import outbox_worker

async def poll_cross_network_messages():
    import asyncio, httpx, os
    from core.db import db_cursor
    from core.broadcast.ws_hub import broadcast_to_user

    _master_url = os.environ.get("HIVE_MASTER", "http://47.96.87.147:8001")
    
    while True:
        try:
            await asyncio.sleep(1) # 刚才说的改成1秒，提高实时性
            
            with db_cursor() as cur:
                cur.execute("SELECT id, sases_id FROM users WHERE username NOT LIKE 'remote_%'")
                user = cur.fetchone()
                if not user: 
                    continue
                user_id = user["id"]
                sases_id = user["sases_id"]

            url = f"{_master_url}/hive/sync/pull_messages?sases_id={sases_id}"
            
            headers = {}
            try:
                from core.broadcast.node_relay import hive_headers
                headers = hive_headers()
            except:
                pass
                
            async with httpx.AsyncClient(timeout=5, trust_env=False, headers=headers) as client:
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    msgs = data.get("messages", [])
                    
                    for m in msgs:
                        try:
                            conv_id = None
                            local_msg_id = None
                            
                            with db_cursor(commit=True) as cur:
                                cur.execute("SELECT id FROM users WHERE sases_id=?", (m["sender_sases"],))
                                sender_row = cur.fetchone()
                                if not sender_row: 
                                    continue
                                sender_uid = sender_row["id"]

                                cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (user_id, sender_uid))
                                conv = cur.fetchone()
                                if not conv: 
                                    continue
                                conv_id = conv["id"]

                                cur.execute("SELECT id FROM messages WHERE conversation_id=? AND content=? AND sender='friend'", (conv_id, m["content"]))
                                if cur.fetchone(): 
                                    continue

                                cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'friend', ?, ?, ?, ?)", (conv_id, m["content"], m["sender_agent_id"], m["msg_type"], m["attachments"]))
                                local_msg_id = cur.lastrowid

                            # 【关键修复】确保缩进正确，且字段完整
                            if conv_id and local_msg_id:
                                await broadcast_to_user(user_id, {
                                    "type": "sases_new_message", 
                                    "sender": "friend",
                                    "conversation_id": conv_id, 
                                    "message_id": local_msg_id,
                                    "content": m["content"], 
                                    "sender_agent_id": m["sender_agent_id"],
                                    "sender_name": "远端好友",
                                    "msg_type": m.get("msg_type") or "standard", 
                                    "attachments": m.get("attachments"),
                                    "timestamp": str(m.get("created_at"))
                                })
                                print(f"[跨网拉取] 🎉 成功接收云端消息: {m['content']}")
                                
                                # 刷新前端会话列表
                                await broadcast_to_user(user_id, {"type": "refresh_conversations"})
                                
                        except Exception as inner_e:
                            print(f"💥 [跨网单条消息处理异常] {inner_e}")
            # --- 拉取好友请求 ---
            req_url = f"{_master_url}/hive/sync/pull_friend_requests?sases_id={sases_id}"
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                resp_req = await client.get(req_url)
                if resp_req.status_code == 200:
                    reqs = resp_req.json().get("requests", [])
                    for r in reqs:
                        with db_cursor(commit=True) as cur:
                            # 查对方的本地 id（如果不存在就建影子）
                            cur.execute("SELECT id FROM users WHERE sases_id=?", (r["sender_sases"],))
                            sender_row = cur.fetchone()
                            if not sender_row:
                                cur.execute("INSERT INTO users (username, password_hash, sases_id) VALUES (?, 'shadow', ?)", (r["sender_name"], r["sender_sases"]))
                                sender_uid = cur.lastrowid
                            else:
                                sender_uid = sender_row["id"]

                            # 防止重复插入
                            cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND target_user_id=?", (sender_uid, user_id))
                            if not cur.fetchone():
                                cur.execute("INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status) VALUES (?, 'dummy', ?, 'pending')", (sender_uid, user_id))

                        # 推送前端刷新
                        await broadcast_to_user(user_id, {"type": "new_friend_request"})
                        print(f"[跨网好友] 收到来自 {r['sender_name']} 的请求")

            # --- 拉取群消息 ---
            group_url = f"{_master_url}/hive/sync/pull_group_messages?sases_id={sases_id}"
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                resp_g = await client.get(group_url)
                if resp_g.status_code == 200:
                    data_g = resp_g.json()
                    for m in data_g.get("messages", []):
                        with db_cursor(commit=True) as cur:
                            # 找本地群
                            cur.execute("SELECT id FROM groups WHERE global_group_id=?", (m["global_group_id"],))
                            g_row = cur.fetchone()
                            if not g_row: continue
                            local_gid = g_row["id"]

                            # 找发送者(如果本地没有则忽略)
                            cur.execute("SELECT id FROM users WHERE sases_id=?", (m["sender_sases"],))
                            s_row = cur.fetchone()
                            sender_uid = s_row["id"] if s_row else 1

                            # 去重
                            cur.execute("SELECT id FROM group_messages WHERE group_id=? AND content=? AND sender_id=?", (local_gid, m["content"], sender_uid))
                            if cur.fetchone(): continue

                            cur.execute("INSERT INTO group_messages (group_id, sender_id, sender_agent_id, content, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?)", (local_gid, sender_uid, m["sender_agent_id"], m["content"], m["msg_type"], m["attachments"]))
                            local_msg_id = cur.lastrowid

                        from core.api_routes.ws_routes import broadcast_to_group
                        await broadcast_to_group(local_gid, {"type": "message", "content": m["content"], "sender_id": sender_uid})
                        print(f"[跨网群聊] 收到群消息: {m['content']}")
        except Exception as outer_e:
            pass

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
    stats_routes,
        user_api_routes,
    ws_routes,
    supervisor_routes,
    upload_routes,
    auth_routes,
    seed_routes,
    credit_routes,
    feedback_routes,
    harness_routes,
    agi_routes,
    space_routes,
    group_routes,
    model_routes,
    agent_routes,
    chat_routes,
    message_routes,
    knowledge_routes,
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
    version_routes,
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
    import shutil as _shutil
    _debug = (_os.environ.get("DEBUG", "").lower() == "true")
    if _shutil.which("git") is None:
        if _debug:
            print("[git-push] 未检测到 git，静默跳过")
        return
    while True:
        try:
            r = subprocess.run(
                "git push origin main",
                shell=True, cwd=repo, capture_output=True,
                encoding="utf-8", errors="replace", timeout=120
            )
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                if _debug:
                    if "Everything up-to-date" in out:
                        print("[git-push] 无新提交")
                    else:
                        print(f"[git-push] 推送成功: {out.strip()[:200]}")
            else:
                if _debug:
                    print(f"[git-push] 推送失败: {out.strip()[:200]}")
        except Exception as e:
            if _debug:
                print(f"[git-push] 异常: {e}")
        await asyncio.sleep(3600)



async def periodic_feedback_weekly():
    """每 7 天生成一次反馈周报（v0.40.0）"""
    import subprocess
    import sys as _sys
    import os as _os
    await asyncio.sleep(600)  # 启动后 10 分钟首跑
    repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    script = _os.path.join(repo, "scripts", "feedback_weekly.py")
    out = _os.path.join(repo, "docs", "feedback_weekly.md")
    while True:
        try:
            if not _os.path.exists(script):
                print("[feedback-weekly] 脚本不存在，跳过")
            else:
                r = subprocess.run(
                    [_sys.executable, script, "7"],
                    cwd=repo, capture_output=True,
                    encoding="utf-8", errors="replace", timeout=120
                )
                if r.returncode == 0:
                    print("[feedback-weekly] 周报已生成")
                else:
                    print(f"[feedback-weekly] 生成失败: {(r.stderr or '')[:200]}")
        except Exception as e:
            print(f"[feedback-weekly] 异常: {e}")
        await asyncio.sleep(7 * 24 * 3600)

async def periodic_hlc_health():
    """每天跑一次 HLC 健康检查，输出到 docs/hlc_health/（v0.38.0）"""
    import subprocess
    import sys as _sys
    import os as _os

    await asyncio.sleep(300)  # 启动后 5 分钟首跑，避开启动高峰
    repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    script = _os.path.join(repo, "scripts", "hlc_health.py")
    out_dir = _os.path.join(repo, "docs", "hlc_health")

    _debug = (_os.environ.get("DEBUG", "").lower() == "true")
    _profile = _os.environ.get("SASES_PROFILE", "").lower()
    if _profile == "personal" and not _debug:
        return
    while True:
        try:
            if not _os.path.exists(script):
                if _debug:
                    print("[hlc-health] 脚本不存在，跳过")
            else:
                r = subprocess.run(
                    [_sys.executable, script],
                    cwd=repo, capture_output=True,
                    encoding="utf-8", errors="replace", timeout=120
                )
                if r.returncode == 0:
                    if _debug:
                        print("[hlc-health] ✅ 健康检查通过")
                else:
                    if _debug:
                        print(f"[hlc-health] ⚠️ 健康检查有问题: {(r.stdout or '')[-500:]}")
                        if r.stderr:
                            print(f"[hlc-health] stderr: {(r.stderr or '')[:300]}")
        except subprocess.TimeoutExpired:
            if _debug:
                print("[hlc-health] 超时 120 秒")
        except Exception as e:
            if _debug:
                print(f"[hlc-health] 异常: {e}")

        # 清理 30 天前的报告
        try:
            if _os.path.isdir(out_dir):
                import time as _time
                now = _time.time()
                removed = 0
                for fname in _os.listdir(out_dir):
                    if not fname.endswith(".md"):
                        continue
                    fpath = _os.path.join(out_dir, fname)
                    try:
                        if now - _os.path.getmtime(fpath) > 30 * 24 * 3600:
                            _os.remove(fpath)
                            removed += 1
                    except Exception:
                        pass
                if removed:
                    print(f"[hlc-health] 清理旧报告 {removed} 个")
        except Exception as e:
            print(f"[hlc-health] 清理异常: {e}")

        await asyncio.sleep(24 * 3600)


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
                        print("[跨网轮询] 正在向云端拉取新消息...")
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

    # 启动时清理中断的 run 和任务（v0.18.0，v0.37.2 加强）
    try:
        from .db import db_cursor as _dbc
        with _dbc(commit=True) as _c:
            # 条件 1：超过 30 分钟的老 running
            _c.execute("UPDATE supervisor_runs SET status='interrupted', finished_at=datetime('now') WHERE status='running' AND (created_at IS NULL OR created_at < datetime('now', '-30 minutes'))")
            _r1 = _c.rowcount
            # 条件 2（新增）：history 为空的僵尸 run——plan_task 失败但 run 未结束
            _c.execute("UPDATE supervisor_runs SET status='plan_failed', finished_at=datetime('now') WHERE status IN ('running', 'running_resumed') AND (history = '[]' OR history IS NULL OR history = '')")
            _r1b = _c.rowcount
            # swarm 任务清理
            _c.execute("UPDATE swarm_pending_tasks SET status='interrupted' WHERE status IN ('pending', 'running') AND created_at < datetime('now', '-30 minutes')")
            _r2 = _c.rowcount
        _total_runs = _r1 + _r1b
        if _total_runs or _r2:
            print(f"[bootstrap] 清理中断状态: runs={_total_runs}(老={_r1},僵尸={_r1b}), tasks={_r2}")
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

    _background_tasks.append(asyncio.create_task(outbox_worker()))

    _background_tasks.append(asyncio.create_task(periodic_syntax_check()))
    _background_tasks.append(asyncio.create_task(poll_cross_network_messages()))

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
    _background_tasks.append(asyncio.create_task(periodic_hlc_health()))


    # 【预热】启动后预热一次（不参与周期）



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
                    try:
                        _os_w.remove(_fp)
                        print('[bootstrap] restart_signal removed')
                    except Exception as _e_rm:
                        print('[bootstrap] restart_signal remove err: ' + str(_e_rm))
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
    from core.migrations import ensure_schema
    ensure_schema()

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
        """副本拦截 + 主节点验签 + 业务日志黑匣子。"""
        import time, logging
        start_t = time.time()
        path = request.url.path
        # 只有这些关键业务路径和报错才会被记录，心跳和静态资源将被无视
        is_business = any(k in path for k in ["/messages/", "/commander/", "/swarm/", "/work/", "/agent/"])
        
        def _log_result(resp):
            process_t = time.time() - start_t
            if is_business or resp.status_code >= 400:
                log_msg = f"[API] {request.method} {path} - {resp.status_code} ({process_t:.3f}s)"
                print(log_msg, flush=True)
                logging.getLogger("business").info(log_msg)
            return resp

        from core.hive.config import REPLICA_MODE, FORWARD_MODE, HIVE_ROLE
        from fastapi.responses import JSONResponse

        # 动态判断当前角色（选举后可能已变更）
        try:
            from core.node.election import get_election_state
            _current_role = get_election_state().get("my_role", "slave")
        except Exception:
            from core.hive.config import HIVE_ROLE as _hr
            _current_role = _hr

        # ========== 主节点：转发请求验证 ==========
        # 当选 master：本地处理（转发请求需先验签）
        if _current_role == "master" and request.headers.get("X-Hive-Forwarded") != "true":
            try:
                response = await call_next(request)
            except Exception as e:
                logging.getLogger("business").error(f"[API ERROR] {request.method} {path} - {str(e)}")
                print(f"[API ERROR] {request.method} {path} - {str(e)}", flush=True)
                raise
            return _log_result(response)

        if _current_role == "master" and request.headers.get("X-Hive-Forwarded") == "true":
            from core.node.forwarder import verify_forward_signature, check_and_record_request
            ok, err = verify_forward_signature(request.headers)
            if not ok:
                return _log_result(JSONResponse({"error": "forward verification failed", "reason": err}, status_code=401))
            request_id = request.headers.get("X-Hive-Request-Id")
            node_id = request.headers.get("X-Hive-From-Node")
            if request_id and check_and_record_request(request_id, node_id):
                return _log_result(JSONResponse({"error": "duplicate request"}, status_code=409))
            
            try:
                response = await call_next(request)
            except Exception as e:
                logging.getLogger("business").error(f"[API ERROR] {request.method} {path} - {str(e)}")
                print(f"[API ERROR] {request.method} {path} - {str(e)}", flush=True)
                raise
            return _log_result(response)

        # ========== 副本：拦截写操作并转发 ==========
        if not REPLICA_MODE:
            try:
                response = await call_next(request)
            except Exception as e:
                logging.getLogger("business").error(f"[API ERROR] {request.method} {path} - {str(e)}")
                print(f"[API ERROR] {request.method} {path} - {str(e)}", flush=True)
                raise
            return _log_result(response)
            
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not (path.startswith("/token")
                    or path.startswith("/auth")
                    or path.startswith("/hive")):
                if FORWARD_MODE == "auto":
                    from core.node.forwarder import forward_request
                    body = await request.body()
                    status, resp = await forward_request(
                        request.method, path, body,
                        dict(request.headers), request.url.query
                    )
                    if status is not None:
                        return _log_result(JSONResponse(resp, status_code=status))
                return _log_result(JSONResponse(
                    {"error": "read-only replica",
                     "message": "本节点为只读副本，写操作请到主节点",
                     "code": 403},
                    status_code=403,
                ))
                
        try:
            response = await call_next(request)
        except Exception as e:
            logging.getLogger("business").error(f"[API ERROR] {request.method} {path} - {str(e)}")
            print(f"[API ERROR] {request.method} {path} - {str(e)}", flush=True)
            raise
        return _log_result(response)

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
    app.include_router(search_routes.router)
    app.include_router(ai_circle_routes.router)
    app.include_router(export_routes.router)
    app.include_router(market_routes.router)
    app.include_router(wisdom_space_routes.router)
    app.include_router(transfer_routes.router)
    app.include_router(user_api_routes.router)
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
    app.include_router(feedback_routes.router)
    app.include_router(version_routes.router)
    app.include_router(stats_routes.router)

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
