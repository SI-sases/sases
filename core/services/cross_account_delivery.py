# core/services/cross_account_delivery.py
import json
import asyncio
from core.db import db_cursor
from datetime import datetime
from ..db import db_cursor

async def deliver_to_linked_accounts(user_id, conversation_id, content, sender_agent_id, msg_type='standard', attachments=None):
    try:
        _att_str = json.dumps(attachments) if attachments else None
        _target_uid = None
        _target_conv_id = None
        _msg_id = None
        _sender_mode = 'normal'
        _target_mode = 'normal'
        _target_agent = None
        _is_remote = False
        _payload_to_send = None

        with db_cursor(commit=True) as cur:
            # 1. 查发送方模式
            cur.execute("SELECT friend_mode FROM conversations WHERE id=?", (conversation_id,))
            _s_row = cur.fetchone()
            if _s_row and _s_row["friend_mode"]:
                _sender_mode = _s_row["friend_mode"]

            # 2. 查找对方的 user_id
            cur.execute("SELECT target_user_id FROM conversations WHERE id=?", (conversation_id,))
            _t_row = cur.fetchone()
            if _t_row and _t_row["target_user_id"]:
                _target_uid = _t_row["target_user_id"]
                
                # 校验好友关系
                cur.execute("SELECT 1 FROM agent_friendships WHERE status='accepted' AND ((user_id=? AND target_user_id=?) OR (user_id=? AND target_user_id=?))", (user_id, _target_uid, _target_uid, user_id))
                if not cur.fetchone():
                    raise ValueError(f"拦截：用户 {user_id} 与 {_target_uid} 尚未成为好友，拒绝投递。")

                # 查对方用户信息判断是否跨网
                cur.execute("SELECT username, sases_id FROM users WHERE id=?", (_target_uid,))
                _target_info = cur.fetchone()
                if _target_info:
                    _target_sases = _target_info["sases_id"]
                    _target_name = _target_info["username"] or ""
                    if _target_name.startswith("remote_") or "shadow" in str(_target_name):
                        _is_remote = True

                # 3. 查对方的会话信息（仅用于获取模式和 agent）
                cur.execute("SELECT id, friend_mode, agent_id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (_target_uid, user_id))
                _t_conv = cur.fetchone()
                if _t_conv:
                    _target_conv_id = _t_conv["id"]
                    _target_mode = _t_conv["friend_mode"] if _t_conv["friend_mode"] else 'normal'
                    _target_agent = _t_conv["agent_id"]

                if _is_remote:
                    # 跨网：准备 HTTP 请求 Payload
                    cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
                    _sender_sases = cur.fetchone()["sases_id"]
                    _payload_to_send = {
                        "target_sases_id": _target_sases, 
                        "content": content, 
                        "sender_sases_id": _sender_sases, 
                        "sender_agent_id": sender_agent_id, 
                        "msg_type": msg_type, 
                        "attachments": attachments
                    }
                else:
                    # 本地用户：直接写库
                    if _target_conv_id:
                        cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?)", (_target_conv_id, 'friend', content, sender_agent_id, msg_type, _att_str))
                        _msg_id = cur.lastrowid
                        cur.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (_target_conv_id,))

        # ==========================================
        # 事务提交后，执行网络请求或 A2A 判定
        # ==========================================
        
        # 【核心修复】跨网发送必须在事务外面执行！
        if _is_remote and _payload_to_send:
            import httpx, os
            from ..broadcast.node_relay import hive_headers
            _master_url = os.environ.get("HIVE_MASTER", "http://47.96.87.147:8001")
            print(f"[跨网投递] 准备发往云端: {_master_url}, 目标: {_payload_to_send['target_sases_id']}")
            try:
                async with httpx.AsyncClient(timeout=5, trust_env=False, headers=hive_headers()) as client:
                    resp = await client.post(f"{_master_url}/hive/sync/friend_message", json=_payload_to_send)
                    print(f"[跨网投递] HTTP 发往云端: {resp.status_code}, 返回: {resp.text}")
            except Exception as e:
                print(f"[跨网投递] 💥 发送失败: {e}")

        # 只有本地用户才有 _msg_id，才需要走后续的 WS 广播和 A2A
        if _target_uid and _target_conv_id and _msg_id:
            is_task = False
            if _sender_mode == 'free' and _target_mode == 'free':
                if sender_agent_id or _target_agent:
                    if content.startswith('#') or ' #' in content:
                        is_task = True
                        print(f"[A2A] 检测到 # 号，强制视为任务！")
                    else:
                        try:
                            from .. import intent_service
                            _is_greeting = intent_service._is_obvious_chat(content)
                            if not _is_greeting and not content.startswith("[IMAGE]:") and not content.startswith("[FILE]:"):
                                is_task = await intent_service.is_task_intent(content)
                        except Exception as e:
                            print(f"[A2A] 意图识别失败: {e}")

                if is_task:
                    from core.services.supervisor_service import create_proposed_run
                    try:
                        _proposed_id = create_proposed_run(
                            user_id=_target_uid,
                            conversation_id=_target_conv_id,
                            supervisor_id=sender_agent_id if sender_agent_id else _target_agent,
                            goal=content,
                            task_type='unknown'
                        )
                        print(f"[A2A] 双方自由，已生成黄卡: {_proposed_id}")
                    except Exception as e:
                        print(f"[A2A] 生成黄卡失败: {e}")
            else:
                if sender_agent_id or _target_agent or content.startswith("#"):
                    print(f"[A2A] 非双自由模式，拦截执行。A:{_sender_mode}, B:{_target_mode}")
                    with db_cursor(commit=True) as cur_warn:
                        _warn_msg = "[系统提示] 必须双方都在自由模式，才能执行智能体指令。"
                        cur_warn.execute(
                            "INSERT INTO messages (conversation_id, sender, content, msg_type) VALUES (?, ?, ?, ?)",
                            (conversation_id, 'assistant', _warn_msg, 'standard')
                        )

            # WebSocket 广播
            try:
                from core.api_routes.ws_routes import broadcast_to_user
                payload = {
                    "type": "sases_new_message",
                    "sender": "friend",
                    "conversation_id": _target_conv_id,
                    "message_id": _msg_id,
                    "content": content,
                    "sender_agent_id": sender_agent_id
                }
                if 'is_task' in locals() and is_task and '_proposed_id' in locals() and _proposed_id:
                    payload["proposed_run_id"] = _proposed_id
                await broadcast_to_user(_target_uid, payload)
                print(f"[投递成功] 已推送给用户 {_target_uid}")
            except Exception as ex:
                print(f"[投递广播失败] {ex}")
                
    except Exception as e:
        print(f"[message] 跨账号投递失败: {e}")


async def deliver_via_relay(sender_sases_id, target_sases_id, content, sender_agent_id=None, msg_type='standard', attachments=None):
    try:
        import httpx
        from ... import config
        if not getattr(config, 'HIVE_PEERS', None):
            return
        peer = config.HIVE_PEERS[0]
        payload = {
            "sender_sases_id": sender_sases_id,
            "target_sases_id": target_sases_id,
            "content": content,
            "sender_agent_id": sender_agent_id,
            "msg_type": msg_type,
            "attachments": attachments
        }
        async with httpx.AsyncClient() as client:
            await client.post(f"{peer}/hive/relay", json=payload, timeout=5.0)
    except Exception as e:
        print(f"[relay] error: {e}")
