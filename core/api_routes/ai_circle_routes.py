# core/api_routes/ai_circle_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import ai_circle_service

router = APIRouter(prefix="/ai-circle", tags=["ai-circle"])
security = HTTPBearer()


class PostCreateRequest(BaseModel):
    content: str
    agent_id: str = "default"   # 暂用默认值，后续可关联真实智能体
    post_type: str = "daily"    # daily / pollination / bounty


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/posts")
async def get_posts(user_id: int = Depends(get_current_user)):
    posts = ai_circle_service.list_posts()
    return {"posts": posts}


@router.post("/posts")
async def create_post(body: PostCreateRequest, user_id: int = Depends(get_current_user)):
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="内容不能为空")
    post_id = ai_circle_service.create_post(
        owner_user_id=user_id,
        agent_id=body.agent_id,
        content=content,
        post_type=body.post_type
    )
    return {"post_id": post_id, "status": "created"}
