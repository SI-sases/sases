# core/api_routes/search_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..db import db_cursor

router = APIRouter(prefix="/search", tags=["search"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/all")
async def global_search(q: str, user_id: int = Depends(get_current_user)):
    """全局搜索：用户、智能体、知识库"""
    query = f"%{q}%"

    with db_cursor() as cur:
        # 搜索用户
        cur.execute("""
            SELECT id, username, sases_id FROM users
            WHERE username LIKE ? OR sases_id LIKE ?
            LIMIT 10
        """, (query, query))
        users = [dict(row) for row in cur.fetchall()]

        # 搜索智能体（公开的或好友的）
        cur.execute("""
            SELECT mc.id, mc.name, mc.provider, mc.model_name, mc.model_type, u.username as owner_name
            FROM model_configs mc
            JOIN users u ON mc.user_id = u.id
            WHERE (mc.is_shared = 1 OR mc.visibility = 'public')
              AND (mc.name LIKE ? OR mc.provider LIKE ? OR mc.model_name LIKE ?)
            LIMIT 10
        """, (query, query, query))
        agents = [dict(row) for row in cur.fetchall()]

        # 搜索知识库（全局）
        cur.execute("""
            SELECT id, task, solution, verified FROM knowledge_base
            WHERE task LIKE ? OR solution LIKE ?
            LIMIT 10
        """, (query, query))
        knowledge = [dict(row) for row in cur.fetchall()]

    return {
        "users": users,
        "agents": agents,
        "knowledge": knowledge
    }
