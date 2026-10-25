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
def sync_group(body: dict):
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
