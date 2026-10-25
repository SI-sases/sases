# core/api_routes/message_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import message_service

router = APIRouter(prefix="/messages", tags=["messages"])
security = HTTPBearer()


class SendMessageRequest(BaseModel):
    msg_type: Optional[str] = "standard"
    attachments: Optional[list] = None
    conversation_id: Optional[int] = None
    agent_id: Optional[str] = None
    content: str
    sender_agent_id: Optional[str] = None
    mode: Optional[str] = "normal"  # normal / free / swarm
    max_steps: Optional[int] = None  # -1=不限，None=默认8


class ConversationCreateRequest(BaseModel):
    agent_id: Optional[str] = None
    title: Optional[str] = "新会话"


class PinRequest(BaseModel):
    pinned: bool


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/conversations")
async def list_conversations(user_id: int = Depends(get_current_user)):
    conversations = message_service.list_conversations(user_id)
    return {"conversations": conversations}


@router.post("/conversations")
async def create_conversation(body: ConversationCreateRequest, user_id: int = Depends(get_current_user)):
    conv_id = message_service.create_conversation(user_id, body.agent_id, body.title)
    return {"conversation_id": conv_id, "title": body.title, "agent_id": body.agent_id}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    after_id: Optional[int] = None,
    user_id: int = Depends(get_current_user)
):
    messages = message_service.get_messages(user_id, conversation_id, limit, offset, after_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"messages": messages}


@router.post("/send")
async def send_message(body: SendMessageRequest, user_id: int = Depends(get_current_user)):
    result = await message_service.send_message(
        user_id=user_id,
        conversation_id=body.conversation_id,
        agent_id=body.agent_id,
        content=body.content,
        sender_agent_id=body.sender_agent_id,
        mode=body.mode,
        max_steps=body.max_steps,
        msg_type=body.msg_type,
        attachments=body.attachments
    )
    try:
        from .ws_routes import broadcast_to_user
        await broadcast_to_user(user_id, {
            'type': 'new_message',
            'conversation_id': result.get('conversation_id'),
            'user_message': result.get('user_message'),
            'assistant_reply': result.get('assistant_reply'),
            'agent_id': result.get('agent_id'),
            'sender_agent_id': result.get('sender_agent_id'),
        })
    except Exception as _e:
        print('[ws] send push failed:', _e)

    # v0.38.0: 返回 write_hlc 供前端读己之写
    try:
        from ..db import db_cursor as _dbc
        _cid_hlc = result.get('conversation_id') if isinstance(result, dict) else None
        if _cid_hlc:
            with _dbc() as _cur_hlc:
                _cur_hlc.execute(
                    "SELECT hlc_ts FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1",
                    (_cid_hlc,)
                )
                _row_hlc = _cur_hlc.fetchone()
                if _row_hlc and _row_hlc["hlc_ts"]:
                    result['write_hlc'] = _row_hlc["hlc_ts"]
    except Exception as _e_hlc:
        print('[hlc] write_hlc 附加失败:', _e_hlc)

    return result


@router.post("/{conversation_id}/read")
async def mark_read(conversation_id: int, user_id: int = Depends(get_current_user)):
    message_service.mark_conversation_read(user_id, conversation_id)
    return {"status": "read"}


@router.post("/{conversation_id}/pin")
async def toggle_pin(conversation_id: int, body: PinRequest, user_id: int = Depends(get_current_user)):
    message_service.toggle_pin_conversation(user_id, conversation_id, body.pinned)
    return {"status": "updated"}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: int, user_id: int = Depends(get_current_user)):
    message_service.delete_conversation(user_id, conversation_id)
    return {"status": "deleted"}
