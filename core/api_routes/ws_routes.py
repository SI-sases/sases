"""core/api_routes/ws_routes.py —— WebSocket 端点（适配层）。"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.broadcast import ws_hub
from core.broadcast.ws_hub import broadcast_to_group, broadcast_to_user  # noqa

router = APIRouter(tags=["websocket"])


def make_group_token_sender(global_group_id: str, msg_id: str = "", sender_name: str = "",
                            sender_agent_id=None):
    """构造 on_token 回调：把 LLM 增量 token 推给群 WS 客户端。

    返回的协程函数签名与 agent_loop._stream_completion 的 on_token(piece) 一致，
    可直接作为 on_token 传入 run_agent / run_service。
    推送事件 type='token'，前端按 msg_id 增量追加，最终 message 事件到达时按 msg_id 去重。
    """
    async def _on_token(piece):
        if not piece:
            return
        try:
            await broadcast_to_group(global_group_id, {
                "type": "token",
                "msg_id": msg_id,
                "delta": piece,
                "sender_name": sender_name,
                "sender_agent_id": sender_agent_id,
            })
        except Exception as _e:
            print("[ws] group token push failed: " + str(_e))

    return _on_token


def make_a2a_progress_sender(global_group_id: str, task_id=None, msg_id: str = "",
                             sender_name: str = "", sender_agent_id=None):
    """构造 A2A progress 的 on_token 回调：token 走 progress 通道推送。

    事件 type='agent_progress'，stage='token'，与既有 agent_progress 事件兼容；
    前端识别 stage='token' 时增量追加，其余 stage 仍走 thinking 提示。
    """
    async def _on_token(piece):
        if not piece:
            return
        try:
            await broadcast_to_group(global_group_id, {
                "type": "agent_progress",
                "stage": "token",
                "task_id": task_id,
                "msg_id": msg_id,
                "delta": piece,
                "sender_name": sender_name,
                "sender_agent_id": sender_agent_id,
            })
        except Exception as _e:
            print("[ws] a2a token push failed: " + str(_e))

    return _on_token

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
