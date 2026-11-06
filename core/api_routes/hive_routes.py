from fastapi import Request
"""蜂群节点信息路由（阶段 1）"""
from fastapi import APIRouter
from .. import config

router = APIRouter(prefix="/hive", tags=["hive"])


@router.get("/info")
def hive_info():
    return {
        "node_id": config.HIVE_NODE_ID or "unknown",
        "mode": config.HIVE_MODE,
        "peers": config.HIVE_PEERS,
        "version": "1.0"
    }


@router.get("/ping")
def hive_ping():
    return {"ok": True}


@router.post("/sync/message")
async def sync_message(body: dict):
    """接收 peer 的群消息，写本地影子群消息。global_msg_id 去重。"""
    from ..db import db_cursor
    _gid = body.get('global_group_id')
    _msg_id = body.get('global_msg_id')
    _content = body.get('content')
    _sender_sases = body.get('sender_sases_id')
    _sender_agent = body.get('sender_agent_id')
    _origin = body.get('origin_node')
    if not _gid or not _msg_id or _content is None:
        return {'ok': False, 'error': 'missing params'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_messages WHERE global_msg_id=?", (_msg_id,))
        if cur.fetchone():
            return {'ok': True, 'skipped': True}
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_gid,))
        _g = cur.fetchone()
        if not _g:
            return {'ok': False, 'error': 'group not found'}
        _local_gid = _g['id']
        _sender_uid = None
        if _sender_sases:
            cur.execute("SELECT id FROM users WHERE sases_id=?", (_sender_sases,))
            _u = cur.fetchone()
            if _u:
                _sender_uid = _u['id']
    try:
        with db_cursor(commit=True) as cur2:
            cur2.execute(
                "INSERT INTO group_messages (group_id, sender_id, sender_agent_id, content, global_msg_id, origin_node) VALUES (?, ?, ?, ?, ?, ?)",
                (_local_gid, _sender_uid, _sender_agent, _content, _msg_id, _origin)
            )
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    try:
        from .ws_routes import broadcast_to_group
        await broadcast_to_group(_gid, {
            'type': 'message',
            'content': _content,
            'sender_sases_id': _sender_sases,
            'sender_agent_id': _sender_agent,
            'origin_node': _origin,
        })
    except Exception as _e:
        print('[ws] sync push failed:', _e)
    # 修复：这里原代码有个未定义的 _owner_uid 会导致崩溃，直接删掉
    return {'ok': True, 'created': True}


@router.post("/sync/member")
def sync_member(body: dict):
    """接收 peer 的成员邀请通知，写本地影子群成员"""
    from ..db import db_cursor
    _gid = body.get('global_group_id')
    _sases_id = body.get('member_sases_id')
    _role = body.get('role') or 'member'
    if not _gid or not _sases_id:
        return {'ok': False, 'error': 'missing params'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_gid,))
        _g = cur.fetchone()
        if not _g:
            return {'ok': False, 'error': 'group not found locally'}
        _local_gid = _g['id']
        cur.execute("SELECT id FROM users WHERE sases_id=?", (_sases_id,))
        _u = cur.fetchone()
        if not _u:
            return {'ok': False, 'error': 'user not found locally'}
        _uid = _u['id']
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (_local_gid, _uid))
        if cur.fetchone():
            return {'ok': True, 'skipped': True}
    try:
        with db_cursor(commit=True) as cur2:
            cur2.execute("INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)", (_local_gid, _uid, _role))
        return {'ok': True, 'created': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@router.post("/sync/member-remove")
def sync_member_remove(body: dict):
    """接收 peer 的成员移除通知"""
    from ..db import db_cursor
    _gid = body.get('global_group_id')
    _sases_id = body.get('member_sases_id')
    if not _gid or not _sases_id:
        return {'ok': False, 'error': 'missing params'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_gid,))
        _g = cur.fetchone()
        if not _g:
            return {'ok': False, 'error': 'group not found'}
        _local_gid = _g['id']
        cur.execute("SELECT id FROM users WHERE sases_id=?", (_sases_id,))
        _u = cur.fetchone()
        if not _u:
            return {'ok': True, 'skipped': True}
        _uid = _u['id']
    try:
        with db_cursor(commit=True) as cur2:
            cur2.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (_local_gid, _uid))
        return {'ok': True, 'removed': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@router.post("/sync/group")
async def sync_group(body: dict):
    """接收 peer 的群创建通知，写本地影子群 + 写群主为成员"""
    from ..db import db_cursor
    _gid = body.get('global_group_id')
    _origin = body.get('origin_node')
    _name = body.get('name') or '未命名群'
    _owner_sases = body.get('owner_sases_id')
    if not _gid:
        return {'ok': False, 'error': 'missing global_group_id'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_gid,))
        if cur.fetchone():
            return {'ok': True, 'skipped': True}
    _owner_uid = None
    if _owner_sases:
        with db_cursor() as cur2:
            cur2.execute("SELECT id FROM users WHERE sases_id=?", (_owner_sases,))
            _u = cur2.fetchone()
            if _u:
                _owner_uid = _u['id']
    try:
        with db_cursor(commit=True) as cur3:
            _oid = _owner_uid if _owner_uid else 1
            cur3.execute(
                "INSERT INTO groups (name, owner_id, mode, global_group_id, origin_node) VALUES (?, ?, 'normal', ?, ?)",
                (_name, _oid, _gid, _origin)
            )
            _local_gid = cur3.lastrowid
            if _owner_uid:
                cur3.execute(
                    "INSERT INTO group_members (group_id, user_id, role, origin_node, user_sases_id) VALUES (?, ?, 'owner', ?, ?)",
                    (_local_gid, _owner_uid, _origin, _owner_sases)
                )
        return {'ok': True, 'created': True, 'global_group_id': _gid, 'owner_added': _owner_uid is not None}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@router.post("/relay")
async def hive_relay(request: Request):
    import asyncio
    try:
        body = await request.json()
        from ..db import db_cursor
        import datetime
        from ..broadcast.ws_hub import broadcast_to_user
        target_sases_id = body.get("target_sases_id")
        sender_sases_id = body.get("sender_sases_id")
        content = body.get("content", "")
        sender_agent_id = body.get("sender_agent_id")
        msg_type = body.get("msg_type", "standard")
        
        with db_cursor() as cur:
            cur.execute("SELECT id FROM users WHERE sases_id=?", (target_sases_id,))
            u = cur.fetchone()
            if not u:
                return {"success": False, "error": "user not found"}
            uid = u["id"]
            cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? LIMIT 1", (uid, sender_sases_id))
            conv = cur.fetchone()
            if not conv:
                cur.execute("INSERT INTO conversations (user_id, target_user_id, title, updated_at) VALUES (?, ?, ?, ?)", (uid, sender_sases_id, f"好友 {sender_sases_id}", datetime.datetime.now().isoformat()))
                conv_id = cur.lastrowid
            else:
                conv_id = conv["id"]
                cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.datetime.now().isoformat(), conv_id))
            
            cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type) VALUES (?, 'friend', ?, ?, ?)", (conv_id, content, sender_agent_id, msg_type))
            msg_id = cur.lastrowid
            
        asyncio.create_task(broadcast_to_user(uid, {"type": "sases_new_message", "message": {"id": msg_id, "sender": "friend", "content": content, "msg_type": msg_type, "conversation_id": conv_id}}))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/sync/friend_message")
async def sync_friend_message(body: dict):
    from ..db import db_cursor
    from ..broadcast.ws_hub import broadcast_to_user
    import json
    
    target_sases_id = body.get("target_sases_id")
    content = body.get("content")
    sender_sases_id = body.get("sender_sases_id", "unknown")
    sender_agent_id = body.get("sender_agent_id")
    msg_type = body.get("msg_type", "standard")
    attachments = body.get("attachments")
    _att_str = json.dumps(attachments) if attachments else None

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE sases_id=?", (target_sases_id,))
        target_row = cur.fetchone()
        if not target_row: return {"status": "error", "msg": "Target not found"}
        target_uid = target_row["id"]
        
        cur.execute("SELECT id FROM users WHERE sases_id=?", (sender_sases_id,))
        sender_row = cur.fetchone()
        if not sender_row:
            cur.execute("INSERT INTO users (username, password_hash, sases_id, credits) VALUES (?, 'shadow', ?, 0)", (f"remote_{sender_sases_id[-6:]}", sender_sases_id))
            sender_uid = cur.lastrowid
        else:
            sender_uid = sender_row["id"]

        cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (target_uid, sender_uid))
        conv = cur.fetchone()
        if not conv:
            cur.execute("INSERT INTO conversations (user_id, target_user_id, title, is_friend_chat) VALUES (?, ?, ?, 1)", (target_uid, sender_uid, f"与 {sender_sases_id[-6:]} 聊天"))
            conv_id = cur.lastrowid
        else:
            conv_id = conv["id"]
            
        cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'friend', ?, ?, ?, ?)", (conv_id, content, sender_agent_id, msg_type, _att_str))
        msg_id = cur.lastrowid
        cur.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (conv_id,))
        
        try:
            await broadcast_to_user(target_uid, {"type": "sases_new_message", "message_id": msg_id, "conversation_id": conv_id, "sender": "friend", "content": content, "sender_agent_id": sender_agent_id, "msg_type": msg_type, "attachments": attachments})
        except Exception as e:
            print(f"[sync_friend_message] WS 广播失败: {e}")
            
    return {"status": "ok", "msg_id": msg_id}


@router.post("/sync/friend_request")
async def sync_friend_request(body: dict):
    from ..db import db_cursor
    from ..broadcast.ws_hub import broadcast_to_user
    
    target_sases_id = body.get("target_sases_id")
    sender_sases_id = body.get("sender_sases_id")
    
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE sases_id=?", (target_sases_id,))
        target_row = cur.fetchone()
        if not target_row: return {"status": "error", "msg": "Target not found"}
        target_uid = target_row["id"]
        
        cur.execute("SELECT id FROM users WHERE sases_id=?", (sender_sases_id,))
        sender_row = cur.fetchone()
        if not sender_row:
            shadow_username = "remote_" + str(sender_sases_id)[-6:]
            cur.execute("INSERT INTO users (username, password_hash, sases_id, credits) VALUES (?, 'shadow', ?, 0)", (shadow_username, sender_sases_id))
            sender_uid = cur.lastrowid
        else:
            sender_uid = sender_row["id"]
            
        # 修复：处理已存在的请求，防止 req_id 未定义引发 500 崩溃
        cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND target_user_id=?", (sender_uid, target_uid))
        existing = cur.fetchone()
        if existing:
            req_id = existing["id"]
        else:
            cur.execute("INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status, friend_mode) VALUES (?, 'dummy', ?, 'pending', 'normal')", (sender_uid, target_uid))
            req_id = cur.lastrowid
            try:
                await broadcast_to_user(target_uid, {"type": "new_friend_request"})
            except Exception: pass
            
    return {"status": "ok", "req_id": req_id}


@router.get("/sync/pull_messages")
async def pull_messages(sases_id: str):
    from ..db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute('''
            SELECT m.id, m.content, m.sender_agent_id, m.msg_type, m.attachments, m.created_at,
                   u.sases_id as sender_sases
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            JOIN users u ON c.target_user_id = u.id
            WHERE c.user_id = (SELECT id FROM users WHERE sases_id=?) 
              AND m.sender = 'friend'
              AND m.id > COALESCE((SELECT last_pulled_id FROM users WHERE sases_id=?), 0)
        ''', (sases_id, sases_id))
        msgs = cur.fetchall()
        
        if msgs:
            max_id = max(m["id"] for m in msgs)
            cur.execute("UPDATE users SET last_pulled_id=? WHERE sases_id=?", (max_id, sases_id))
            
        return {"messages": [dict(m) for m in msgs]}


@router.get("/sync/pull_group_messages")
async def pull_group_messages(sases_id: str):
    from ..db import db_cursor
    with db_cursor(commit=True) as cur:
        # 查询发给该用户所在群的新消息
        cur.execute('''
            SELECT m.id, m.group_id, m.content, m.sender_agent_id, m.msg_type, m.attachments, m.created_at,
                   u.sases_id as sender_sases, g.global_group_id
            FROM group_messages m
            JOIN groups g ON m.group_id = g.id
            JOIN users u ON m.sender_id = u.id
            WHERE m.group_id IN (
                SELECT group_id FROM group_members WHERE user_id = (SELECT id FROM users WHERE sases_id=?)
            )
            AND m.id > COALESCE((SELECT last_pulled_group_id FROM users WHERE sases_id=?), 0)
        ''', (sases_id, sases_id))
        msgs = cur.fetchall()

        if msgs:
            max_id = max(m["id"] for m in msgs)
            cur.execute("UPDATE users SET last_pulled_group_id=? WHERE sases_id=?", (max_id, sases_id))

        return {"messages": [dict(m) for m in msgs]}


@router.post("/sync/register")
async def sync_register(body: dict):
    """接收来自本地客户端的跨节点注册信息"""
    from ..db import db_cursor
    _username = body.get('username')
    _password_hash = body.get('password_hash')
    _sases_id = body.get('sases_id')
    if not _username or not _sases_id:
        return {"ok": False, "error": "missing params"}
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE username=?", (_username,))
        if cur.fetchone():
            return {"ok": True, "skipped": True}
        cur.execute(
            "INSERT INTO users (username, password_hash, sases_id) VALUES (?, ?, ?)",
            (_username, _password_hash, _sases_id)
        )
        print(f"[跨网注册] 成功同步云端账号: {_username} ({_sases_id})")
    return {"ok": True}


@router.get("/sync/pull_friend_requests")
async def pull_friend_requests(sases_id: str):
    """供本地客户端轮询拉取发给自己的好友请求"""
    from ..db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE sases_id=?", (sases_id,))
        target_row = cur.fetchone()
        if not target_row:
            return {"requests": []}
        target_uid = target_row["id"]

        cur.execute("""
            SELECT af.id as req_id, u.sases_id as sender_sases, u.username as sender_name
            FROM agent_friendships af
            JOIN users u ON af.user_id = u.id
            WHERE af.target_user_id = ? AND af.status = 'pending'
        """, (target_uid,))
        reqs = cur.fetchall()

        if reqs:
            req_ids = [r["req_id"] for r in reqs]
            placeholders = ','.join('?' for _ in req_ids)
            cur.execute(f"UPDATE agent_friendships SET status='pulled' WHERE id IN ({placeholders})", req_ids)

        return {"requests": [dict(r) for r in reqs]}


@router.post("/sync/accept_friend")
async def sync_accept_friend(body: dict):
    from ..db import db_cursor
    _sender = body.get("sender_sases_id")
    _target = body.get("target_sases_id")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE sases_id=?", (_sender,))
        s_row = cur.fetchone()
        cur.execute("SELECT id FROM users WHERE sases_id=?", (_target,))
        t_row = cur.fetchone()
        if s_row and t_row:
            cur.execute("UPDATE agent_friendships SET status='accepted' WHERE user_id=? AND target_user_id=?", (s_row["id"], t_row["id"]))
            cur.execute("INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status) SELECT ?, 'dummy', ?, 'accepted' WHERE NOT EXISTS (SELECT 1 FROM agent_friendships WHERE user_id=? AND target_user_id=?)", (t_row["id"], s_row["id"], t_row["id"], s_row["id"]))
    return {"status": "ok"}


@router.get("/sync/pull_friend_status")
async def pull_friend_status(sases_id: str):
    """供本地客户端轮询，拉取最新的好友关系状态"""
    from ..db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE sases_id=?", (sases_id,))
        target_row = cur.fetchone()
        if not target_row: return {"friends": []}
        target_uid = target_row["id"]

        # 查所有跟我有关，且已经被同意的好友关系
        cur.execute("""
            SELECT u.sases_id as friend_sases, u.username as friend_name
            FROM agent_friendships af
            JOIN users u ON af.user_id = u.id
            WHERE af.target_user_id = ? AND af.status = 'accepted'
        """, (target_uid,))
        friends = cur.fetchall()
        return {"friends": [dict(f) for f in friends]}


@router.post("/sync/transfer")
async def sync_transfer(body: dict):
    """接收 peer 转账。idempotency_key 去重。自动创建影子用户。"""
    from ..db import db_cursor
    from ..broadcast.ws_hub import broadcast_to_user
    from datetime import datetime
    _idem = body.get("idempotency_key")
    _ss = body.get("sender_sases_id")
    _ts = body.get("target_sases_id")
    _amt = body.get("amount")
    _ct = body.get("credit_type", "credits")
    _msg = body.get("message", "")

    if not _idem or not _ss or not _ts or _amt is None:
        return {"status": "error", "msg": "missing params"}
    if _amt <= 0:
        return {"status": "error", "msg": "amount must be positive"}
    if _ct not in ("credits", "compute"):
        return {"status": "error", "msg": "invalid credit_type"}
    if _ss == _ts:
        return {"status": "error", "msg": "cannot transfer to self"}

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM transactions WHERE idempotency_key=?", (_idem,))
        _exist = cur.fetchone()
        if _exist:
            return {"status": "ok", "skipped": True, "tx_id": _exist["id"]}
        try:
            cur.execute("INSERT INTO sync_received (idempotency_key, received_at) VALUES (?, ?)", (_idem, datetime.now().isoformat()))
        except Exception as e:
            return {"status": "error", "msg": "Duplicate key locked"}

        cur.execute("SELECT id FROM transactions WHERE idempotency_key=?", (_idem,))
        _exist = cur.fetchone()
        if _exist:
            return {"status": "ok", "skipped": True, "tx_id": _exist["id"]}
        cur.execute("SELECT id FROM users WHERE sases_id=?", (_ts,))
        _t = cur.fetchone()
        if _t:
            _tuid = _t["id"]
        else:
            cur.execute("INSERT INTO users (username, password_hash, sases_id, credits) VALUES (?, 'shadow', ?, 0)", ("remote_"+_ts[-6:], _ts))
            _tuid = cur.lastrowid
        cur.execute("SELECT id FROM users WHERE sases_id=?", (_ss,))
        _s = cur.fetchone()
        if _s:
            _suid = _s["id"]
        else:
            cur.execute("INSERT INTO users (username, password_hash, sases_id, credits) VALUES (?, 'shadow', ?, 0)", ("remote_"+_ss[-6:], _ss))
            _suid = cur.lastrowid

        if _ct == "compute":
            cur.execute("SELECT balance FROM user_compute_balance WHERE user_id=?", (_suid,))
            _b = cur.fetchone()
            if not _b or _b["balance"] < _amt:
                return {"status": "error", "msg": "insufficient compute"}
            cur.execute("UPDATE user_compute_balance SET balance = balance - ? WHERE user_id=?", (_amt, _suid))
            cur.execute("INSERT INTO user_compute_balance (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", (_tuid, _amt, _amt))
        else:
            cur.execute("SELECT credits FROM users WHERE id=?", (_suid,))
            _b = cur.fetchone()
            if not _b or _b["credits"] < _amt:
                return {"status": "error", "msg": "insufficient credits"}
            cur.execute("UPDATE users SET credits = credits - ? WHERE id=?", (_amt, _suid))
            cur.execute("UPDATE users SET credits = credits + ? WHERE id=?", (_amt, _tuid))

        cur.execute("INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, status, message, completed_at, credit_type, idempotency_key, receiver_node_id) VALUES (?, ?, ?, 'transfer', 'completed', ?, ?, ?, ?, 'cloud')", (_suid, _tuid, _amt, _msg, datetime.now().isoformat(), _ct, _idem))
        _tx = cur.lastrowid
    try:
        await broadcast_to_user(_tuid, {"type": "balance_update", "reason": "transfer_in", "amount": _amt, "credit_type": _ct, "tx_id": _tx})
        await broadcast_to_user(_suid, {"type": "balance_update", "reason": "transfer_out", "amount": _amt, "credit_type": _ct, "tx_id": _tx})
    except Exception as _e:
        print("[sync_transfer] WS 广播失败: " + str(_e))
    try:
        with db_cursor(commit=True) as cur_msg:
            cur_msg.execute("SELECT id FROM conversations WHERE user_id=? AND is_friend_chat=1 LIMIT 1", (_tuid,))
            conv = cur_msg.fetchone()
            if conv:
                _payload = {"tx_id": _tx, "amount": _amt, "credit_type": _ct, "message": _msg or "转账"}
                import json as _json
                msg_content = "[TRANSFER]:" + _json.dumps(_payload, ensure_ascii=False)
                cur_msg.execute("INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, 'friend', ?, datetime('now', 'localtime'))", (conv["id"], msg_content))
    except Exception as e:
        print("[sync_transfer] write msg error:", e)
    return {"status": "ok", "tx_id": _tx, "created": True}
