# core/api_routes/feedback_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])
security = HTTPBearer()


class FeedbackSubmitRequest(BaseModel):
    task_id: str
    rating: str  # up / down / neutral
    reason_tag: Optional[str] = None
    reason_text: Optional[str] = None
    task_source: Optional[str] = "swarm"
    conversation_id: Optional[int] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/submit")
async def submit(body: FeedbackSubmitRequest, user_id: int = Depends(get_current_user)):
    result = feedback_service.submit_explicit(
        user_id=user_id,
        task_id=body.task_id,
        rating=body.rating,
        reason_tag=body.reason_tag,
        reason_text=body.reason_text,
        task_source=body.task_source or "swarm",
        conversation_id=body.conversation_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "提交失败"))
    return result


@router.get("/my")
async def my_feedback(
    limit: int = 50,
    offset: int = 0,
    user_id: int = Depends(get_current_user)
):
    if limit < 1 or limit > 200:
        limit = 50
    if offset < 0:
        offset = 0
    return {"items": feedback_service.get_user_feedback(user_id, limit, offset)}


@router.get("/by_task")
async def by_task(task_id: str, user_id: int = Depends(get_current_user)):
    return {"items": feedback_service.get_feedback_by_task(task_id)}


@router.get("/stats")
async def stats(range: str = "7d", user_id: int = Depends(get_current_user)):
    range_days = 7
    try:
        if range.endswith("d"):
            range_days = int(range[:-1])
    except Exception:
        range_days = 7
    if range_days < 1 or range_days > 90:
        range_days = 7
    return {
        "range_days": range_days,
        "stats": feedback_service.get_stats(user_id, range_days),
    }