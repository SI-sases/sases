# core/api_routes/chat_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import chat_service

router = APIRouter(prefix="/agent", tags=["chat"])
security = HTTPBearer()


class ChatRequest(BaseModel):
    query: str
    agent_id: Optional[str] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/chat")
async def chat(body: ChatRequest, user_id: int = Depends(get_current_user)):
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="消息不能为空")

    try:
        if body.agent_id:
            reply = await chat_service.call_agent_chat(user_id, body.agent_id, query)
        else:
            reply = await chat_service.call_default_agent_chat(user_id, query)
        return {"response": reply}
    except PermissionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
