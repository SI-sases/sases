"""core/broadcast/ws_hub.py —— WS 连接池与广播（无 FastAPI 依赖）。"""
from typing import Dict, Set

_group_connections: Dict[str, Set] = {}
_user_connections: Dict[int, Set] = {}


def register_group(global_group_id: str, ws):
    if global_group_id not in _group_connections:
        _group_connections[global_group_id] = set()
    _group_connections[global_group_id].add(ws)


def unregister_group(global_group_id: str, ws):
    _group_connections.get(global_group_id, set()).discard(ws)


def register_user(user_id: int, ws):
    if user_id not in _user_connections:
        _user_connections[user_id] = set()
    _user_connections[user_id].add(ws)


def unregister_user(user_id: int, ws):
    _user_connections.get(user_id, set()).discard(ws)


async def broadcast_to_group(global_group_id: str, message: dict):
    conns = _group_connections.get(global_group_id, set())
    dead = []
    for ws in list(conns):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        conns.discard(ws)


async def broadcast_to_user(user_id: int, message: dict):
    conns = _user_connections.get(user_id, set())
    dead = []
    for ws in list(conns):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        conns.discard(ws)


def stats():
    return {
        "group_count": len(_group_connections),
        "group_total": sum(len(s) for s in _group_connections.values()),
        "user_count": len(_user_connections),
        "user_total": sum(len(s) for s in _user_connections.values()),
    }