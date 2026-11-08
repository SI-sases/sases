from fastapi import Request
# core/api_routes/agent_routes.py
from fastapi import APIRouter, Depends, HTTPException, Depends, HTTPException
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
    target_sases_id: Optional[str] = None
    agent_id: Optional[str] = None

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
    # 1. 如果传了 target_sases_id，说明是加真人好友
    if body.target_sases_id:
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("SELECT id, username FROM users WHERE sases_id=?", (body.target_sases_id,))
                target = cur.fetchone()
                if not target:
                    # 跨服兜底：自动在本地创建影子账号
                    shadow_username = f"remote_{body.target_sases_id[-6:]}"
                    try:
                        cur.execute("INSERT INTO users (username, password_hash, sases_id, credits) VALUES (?, 'shadow', ?, 0)", (shadow_username, body.target_sases_id))
                    except Exception:
                        pass # 防止并发重复创建报错
                    cur.execute("SELECT id, username FROM users WHERE sases_id=?", (body.target_sases_id,))
                    target = cur.fetchone()
                    print(f"[跨服加好友] 已创建影子账号: {shadow_username}")
                
                if not target:
                    raise HTTPException(status_code=500, detail="影子账号创建失败")
                
                target_user_id = target["id"]
                if target_user_id == user_id:
                    raise HTTPException(status_code=400, detail="不能添加自己为好友")
                
                _target_username = target["username"] if target["username"] else ""
                
                # 本地留底（防止因重复添加报错导致后续不执行）
                cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND target_user_id=?", (user_id, target_user_id))
                exist = cur.fetchone()
                if not exist:
                    cur.execute("INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status, friend_mode) VALUES (?, 'dummy', ?, 'pending', 'normal')", (user_id, target_user_id))
                
                # 强制创建会话，确保前端列表能看到
                cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (user_id, target_user_id))
                if not cur.fetchone():
                    cur.execute("INSERT INTO conversations (user_id, target_user_id, title, is_friend_chat, friend_mode) VALUES (?, ?, ?, 1, 'normal')", (user_id, target_user_id, _target_username))

                # 判断是否是远端影子用户
                if _target_username.startswith("remote_") or "shadow" in str(_target_username):
                    import httpx, os
                    from ..broadcast.node_relay import hive_headers
                    _master_url = os.environ.get("HIVE_MASTER", "http://47.96.87.147:8001")
                    
                    cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
                    _sender_sases = cur.fetchone()["sases_id"]
                    
                    _payload = {
                        "target_sases_id": body.target_sases_id,
                        "sender_sases_id": _sender_sases
                    }
                    
                    print(f"[跨网加好友] 准备向 {_master_url} 发送请求, payload={_payload}")
                    try:
                        resp = httpx.post(f"{_master_url}/hive/sync/friend_request", json=_payload, headers=hive_headers(), timeout=5, trust_env=False)
                        print(f"[跨网加好友] 发送成功! HTTP {resp.status_code}, 返回: {resp.text}")
                    except Exception as e:
                        print(f"[跨网加好友] 💥 发送失败! 异常信息: {e}")
                        
            return {"status": "request_sent"}
        except HTTPException:
            raise
        except Exception as e:
            print(f"[send_friend_request 异常] {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 2. 如果传了 agent_id，说明是原有的加智能体功能
    elif body.agent_id:
        try:
            agent_service.send_friend_request(user_id, body.agent_id)
            return {"status": "request_sent"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    else:
        raise HTTPException(status_code=400, detail="必须提供 target_sases_id 或 agent_id")

@router.get("/friend-requests")
async def get_received_friend_requests(user_id: int = Depends(get_current_user)):
    requests = agent_service.get_received_friend_requests(user_id)
    return {"requests": requests}

@router.post("/friend-requests/accept")
async def accept_friend_request(body: AcceptRequest, user_id: int = Depends(get_current_user)):
    try:
        with db_cursor(commit=True) as cur:
            # 1. 查真实的好友请求
            cur.execute("SELECT user_id, target_user_id FROM agent_friendships WHERE id=? AND status='pending'", (body.request_id,))
            row = cur.fetchone()
            if not row:
                raise PermissionError("好友请求不存在或已处理")
            
            sender_id = row["user_id"]       # 发起请求的人
            receiver_id = row["target_user_id"]     # 同意请求的人 (当前用户)
            
            # 2. 更新好友关系为 accepted
            cur.execute("UPDATE agent_friendships SET status='accepted' WHERE id=?", (body.request_id,))

            # [修复] 建立反向好友关系
            cur.execute("SELECT 1 FROM agent_friendships WHERE user_id=? AND target_user_id=?", (receiver_id, sender_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status, friend_mode) VALUES (?, 'dummy', ?, 'accepted', 'normal')", (receiver_id, sender_id))

            # 3. 为发起者建会话 (如果不存在)
            cur.execute('SELECT username FROM users WHERE id=?', (receiver_id,))
            _recv_row = cur.fetchone()
            _recv_name = _recv_row["username"] if _recv_row and _recv_row["username"] else f'User{receiver_id}'

            cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (sender_id, receiver_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO conversations (user_id, target_user_id, title, is_friend_chat, friend_mode) VALUES (?, ?, ?, 1, 'normal')", (sender_id, receiver_id, _recv_name))
                
            # 4. 为接收者建会话 (如果不存在)
            cur.execute('SELECT username FROM users WHERE id=?', (sender_id,))
            _send_row = cur.fetchone()
            _send_name = _send_row["username"] if _send_row and _send_row["username"] else f'User{sender_id}'

            cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (receiver_id, sender_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO conversations (user_id, target_user_id, title, is_friend_chat, friend_mode) VALUES (?, ?, ?, 1, 'normal')", (receiver_id, sender_id, _send_name))
                
            cur.execute("SELECT username, sases_id FROM users WHERE id=?", (sender_id,))
            _sender = cur.fetchone()
            if _sender:
                import httpx, os
                _master_url = os.environ.get("HIVE_MASTER", "http://47.96.87.147:8001")
                cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
                _my_sases = cur.fetchone()["sases_id"]
                try:
                    httpx.post(_master_url + "/hive/sync/accept_friend", json={"sender_sases_id": _sender["sases_id"], "target_sases_id": _my_sases}, timeout=3)
                except Exception: pass
        return {"status": "accepted"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

# ================= 好友代理模式切换 =================
from typing import Optional

class FriendModeRequest(BaseModel):
    target_user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    mode: str

@router.post("/friend-mode")
async def set_friend_mode(body: FriendModeRequest, user_id: int = Depends(get_current_user)):
    if body.mode not in ('normal', 'free'):
        raise HTTPException(status_code=400, detail="模式必须是 normal 或 free")
    
    try:
        with db_cursor(commit=True) as cur:
            real_target_id = body.target_user_id
            if body.conversation_id:
                cur.execute("SELECT target_user_id FROM conversations WHERE id=? AND user_id=?", (body.conversation_id, user_id))
                row = cur.fetchone()
                if row:
                    real_target_id = row["target_user_id"]
            
            if not real_target_id:
                raise HTTPException(status_code=400, detail="缺少目标用户ID或会话ID")

            # 检查好友关系
            cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND target_user_id=? AND status='accepted'", (user_id, real_target_id))
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="你们还不是好友")
                
            # 更新好友关系表
            cur.execute("UPDATE agent_friendships SET friend_mode=? WHERE user_id=? AND target_user_id=?", (body.mode, user_id, real_target_id))
            
            # 精确更新会话模式
            cur.execute("UPDATE conversations SET friend_mode=? WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (body.mode, user_id, real_target_id))
            
        return {"status": "ok", "mode": body.mode}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[friend-mode 报错] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class SessionAgentRequest(BaseModel):
    conversation_id: int
    agent_id: str

@router.post("/bind-session-agent")
async def bind_session_agent(body: SessionAgentRequest, user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE conversations SET agent_id=? WHERE id=? AND user_id=?", (body.agent_id, body.conversation_id, user_id))
    return {"status": "ok"}

@router.delete("/friends/{friendship_id}")
async def delete_friend(friendship_id: int, user_id: int = Depends(get_current_user)):
    from ..services import agent_service
    success, msg = agent_service.delete_friend(user_id, friendship_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok", "msg": msg}
