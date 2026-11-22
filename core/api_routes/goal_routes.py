# core/api_routes/goal_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from ..auth_service import SECRET_KEY
from ..db import db_cursor
from ..services import goal_runner

router = APIRouter(prefix="/goals", tags=["goals"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


class GoalRequest(BaseModel):
    goal: str
    conversation_id: int = 0
    max_rounds: int = 10
    budget_tokens: int = 200000


@router.get("")
async def list_goals(user_id: int = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM agent_goals WHERE user_id=? ORDER BY id DESC LIMIT 50",
                    (user_id,))
        return {"goals": [dict(r) for r in cur.fetchall()]}


@router.post("")
async def create_goal(body: GoalRequest, user_id: int = Depends(get_current_user)):
    gid = goal_runner.create_goal(user_id, body.conversation_id, body.goal,
                                  max_rounds=max(1, int(body.max_rounds)),
                                  budget_tokens=max(1000, int(body.budget_tokens)))
    return {"goal_id": gid, "status": "active"}


@router.post("/{goal_id}/pause")
async def pause_goal(goal_id: int, user_id: int = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE agent_goals SET status='paused', updated_at=datetime('now') "
                    "WHERE id=? AND user_id=?", (int(goal_id), user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="goal not found")
    return {"ok": True, "goal_id": goal_id, "status": "paused"}


@router.post("/{goal_id}/cancel")
async def cancel_goal(goal_id: int, user_id: int = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE agent_goals SET status='cancelled', updated_at=datetime('now') "
                    "WHERE id=? AND user_id=?", (int(goal_id), user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="goal not found")
    return {"ok": True, "goal_id": goal_id, "status": "cancelled"}
