"""core/api_routes/ws_routes.py —— WebSocket 端点（适配层）。"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.broadcast import ws_hub
from core.broadcast.ws_hub import broadcast_to_group, broadcast_to_user  # noqa

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/group/{global_group_id}")
async def ws_group(websocket: WebSocket, global_group_id: str):
    await websocket.accept()
    ws_hub.register_group(global_group_id, websocket)
    print(f"[ws] client connected to group {global_group_id}")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_hub.unregister_group(global_group_id, websocket)
        print(f"[ws] client disconnected from group {global_group_id}")


@router.websocket("/ws/user/{user_id}")
async def ws_user(websocket: WebSocket, user_id: int):
    await websocket.accept()
    ws_hub.register_user(user_id, websocket)
    print(f"[ws] user {user_id} connected")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_hub.unregister_user(user_id, websocket)
        print(f"[ws] user {user_id} disconnected")
