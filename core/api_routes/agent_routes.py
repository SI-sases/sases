# core/api_routes/agent_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import agent_service
from ..db import db_cursor

router = APIRouter(prefix="/agents", tags=["agents"])
security = HTTPBearer()

class FriendRequest(BaseModel):
    agent_id: str

class CallAgentRequest(BaseModel):
    agent_id: str
    query: str

class AcceptRequest(BaseModel):
    request_id: int

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.get("/list")
async def list_my_agents(user_id: int = Depends(get_current_user)):
    agents = agent_service.list_my_agents(user_id)
    return {"agents": agents}

@router.get("/friends")
async def list_friend_agents(user_id: int = Depends(get_current_user)):
    friends = agent_service.list_friend_agents(user_id)
    return {"friends": friends}

@router.get("/search")
async def search_agents(q: str, include_self: bool = False, user_id: int = Depends(get_current_user)):
    results = agent_service.search_agents(user_id, q, include_self)
    return {"results": results}

@router.post("/friend-request")
async def send_friend_request(body: FriendRequest, user_id: int = Depends(get_current_user)):
    try:
        agent_service.send_friend_request(user_id, body.agent_id)
        return {"status": "request_sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/friend-requests")
async def get_received_friend_requests(user_id: int = Depends(get_current_user)):
    requests = agent_service.get_received_friend_requests(user_id)
    return {"requests": requests}

@router.post("/friend-requests/accept")
async def accept_friend_request(body: AcceptRequest, user_id: int = Depends(get_current_user)):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT sender_id, receiver_id FROM agent_friend_requests WHERE id=? AND receiver_id=? AND status='pending'", (body.request_id, user_id))
            row = cur.fetchone()
            if not row:
                raise PermissionError("好友请求不存在或无权处理")
            sender_id = row[0]
            receiver_id = row[1]
            cur.execute("UPDATE agent_friendships SET status='accepted' WHERE user_id=? AND friend_user_id=?", (sender_id, receiver_id))
            cur.execute("UPDATE agent_friendships SET status='accepted' WHERE user_id=? AND friend_user_id=?", (receiver_id, sender_id))
            cur.execute("UPDATE agent_friend_requests SET status='accepted' WHERE id=?", (body.request_id,))
            cur.execute("SELECT 1 FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (sender_id, receiver_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO conversations (user_id, target_user_id, is_friend_chat) VALUES (?, ?, 1)", (sender_id, receiver_id))
            cur.execute("SELECT 1 FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (receiver_id, sender_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO conversations (user_id, target_user_id, is_friend_chat) VALUES (?, ?, 1)", (receiver_id, sender_id))
        return {"status": "accepted"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/friend-requests/reject")
async def reject_friend_request(body: AcceptRequest, user_id: int = Depends(get_current_user)):
    try:
        agent_service.reject_friend_request(user_id, body.request_id)
        return {"status": "rejected"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/call")
async def call_agent(body: CallAgentRequest, user_id: int = Depends(get_current_user)):
    try:
        result = agent_service.call_agent(user_id, body.agent_id, body.query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/chat")
async def api_suggest_reply(body: CallAgentRequest, user_id: int = Depends(get_current_user)):
    """根据智能体生成建议回复（不入库）"""
    from ..services import chat_service
    try:
        reply = await chat_service.call_agent_chat(user_id, body.agent_id, body.query)
        return {"response": reply}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chat")
async def api_suggest_reply(body: CallAgentRequest, user_id: int = Depends(get_current_user)):
    """根据智能体生成建议回复（不入库）"""
    from ..services import chat_service
    try:
        reply = await chat_service.call_agent_chat(user_id, body.agent_id, body.query)
        return {"response": reply}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ================= 好友代理模式切换 =================
class FriendModeRequest(BaseModel):
    target_user_id: int
    mode: str

@router.post("/friend-mode")
async def set_friend_mode(body: FriendModeRequest, user_id: int = Depends(get_current_user)):
    if body.mode not in ('normal', 'free'):
        raise HTTPException(status_code=400, detail="模式必须是 normal 或 free")
    
    try:
        with db_cursor(commit=True) as cur:
            # 检查好友关系
            cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND target_user_id=? AND status='accepted'", (user_id, body.target_user_id))
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="你们还不是好友")
                
            # 更新模式
            cur.execute("UPDATE agent_friendships SET friend_mode=? WHERE user_id=? AND target_user_id=?", (body.mode, user_id, body.target_user_id))
            
            # 同步更新会话模式
            cur.execute("UPDATE conversations SET friend_mode=? WHERE user_id=? AND is_friend_chat=1", (body.mode, user_id))
            
        return {"status": "ok", "mode": body.mode}
    except Exception as e:
        print(f"[friend-mode 报错] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
