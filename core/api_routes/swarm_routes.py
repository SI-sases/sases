# core/api_routes/swarm_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..db import db_cursor
from ..services import swarm_service

router = APIRouter(prefix="/swarm", tags=["swarm"])
security = HTTPBearer()


class SwarmPlanRequest(BaseModel):
    conversation_id: int
    user_input: str
    commander_id: Optional[str] = None
    executor_id: Optional[str] = None
    timeout: int = 30
    require_confirmation: bool = False


class SwarmConfirmRequest(BaseModel):
    task_id: str
    edited_steps: Optional[List[Dict[str, Any]]] = None


class SwarmCancelRequest(BaseModel):
    task_id: str


class SwarmFeedbackRequest(BaseModel):
    task_id: Optional[str] = None
    original_input: Optional[str] = ""
    feedback_type: Optional[str] = "false_positive"
    note: Optional[str] = ""


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/plan")
async def plan(body: SwarmPlanRequest, user_id: int = Depends(get_current_user)):
    if not body.user_input.strip():
        raise HTTPException(status_code=400, detail="用户输入不能为空")
    result = await swarm_service.plan_task(
        user_id=user_id,
        conversation_id=body.conversation_id,
        user_input=body.user_input.strip(),
        commander_id=body.commander_id,
        executor_id=body.executor_id,
        timeout=body.timeout,
        require_confirmation=body.require_confirmation
    )
    return result


@router.post("/confirm")
async def confirm(body: SwarmConfirmRequest, user_id: int = Depends(get_current_user)):
    """用户确认或编辑草稿任务后，下发执行"""
    if not body.task_id:
        raise HTTPException(status_code=400, detail="task_id 不能为空")
    result = swarm_service.confirm_task(
        task_id=body.task_id,
        user_id=user_id,
        edited_steps=body.edited_steps
    )
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=result.get("message", "任务不存在"))
    if result.get("status") == "forbidden":
        raise HTTPException(status_code=403, detail=result.get("message", "无权操作"))
    return result


@router.post("/cancel")
async def cancel(body: SwarmCancelRequest, user_id: int = Depends(get_current_user)):
    result = swarm_service.cancel_task(body.task_id, user_id)
    return result


@router.post("/feedback")
async def feedback(body: SwarmFeedbackRequest, user_id: int = Depends(get_current_user)):
    result = swarm_service.submit_feedback(
        user_id=user_id,
        task_id=body.task_id,
        original_input=body.original_input or "",
        feedback_type=body.feedback_type or "false_positive",
        note=body.note or ""
    )
    return result


@router.get("/reviews")
async def list_reviews(
    limit: int = 50,
    task_id: Optional[str] = None,
    user_id: int = Depends(get_current_user)
):
    """查询审核日志：只返回当前用户所属会话的记录"""
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    with db_cursor() as cur:
        if task_id:
            cur.execute(
                """
                SELECT r.id, r.task_id, r.conversation_id, r.step_id,
                       r.command, r.exec_status, r.review_result,
                       r.review_reason, r.output_preview, r.created_at
                FROM swarm_reviews r
                JOIN conversations c ON r.conversation_id = c.id
                WHERE c.user_id = ? AND r.task_id = ?
                ORDER BY r.id DESC LIMIT ?
                """,
                (user_id, task_id, limit)
            )
        else:
            cur.execute(
                """
                SELECT r.id, r.task_id, r.conversation_id, r.step_id,
                       r.command, r.exec_status, r.review_result,
                       r.review_reason, r.output_preview, r.created_at
                FROM swarm_reviews r
                JOIN conversations c ON r.conversation_id = c.id
                WHERE c.user_id = ?
                ORDER BY r.id DESC LIMIT ?
                """,
                (user_id, limit)
            )
        rows = [dict(r) for r in cur.fetchall()]

    return {"reviews": rows, "count": len(rows)}


@router.get("/reviews/stats")
async def review_stats(user_id: int = Depends(get_current_user)):
    """审核统计：按 exec_status 和 review_result 聚合"""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT r.exec_status, COUNT(*) as cnt
            FROM swarm_reviews r
            JOIN conversations c ON r.conversation_id = c.id
            WHERE c.user_id = ?
            GROUP BY r.exec_status
            """,
            (user_id,)
        )
        by_status = {row["exec_status"]: row["cnt"] for row in cur.fetchall()}

        cur.execute(
            """
            SELECT r.review_result, COUNT(*) as cnt
            FROM swarm_reviews r
            JOIN conversations c ON r.conversation_id = c.id
            WHERE c.user_id = ?
            GROUP BY r.review_result
            """,
            (user_id,)
        )
        by_review = {row["review_result"]: row["cnt"] for row in cur.fetchall()}

        cur.execute(
            """
            SELECT r.command, COUNT(*) as cnt
            FROM swarm_reviews r
            JOIN conversations c ON r.conversation_id = c.id
            WHERE c.user_id = ? AND r.review_result = 'retry'
            GROUP BY r.command
            ORDER BY cnt DESC
            LIMIT 10
            """,
            (user_id,)
        )
        top_failed = [
            {"command": row["command"], "count": row["cnt"]}
            for row in cur.fetchall()
        ]

    return {
        "by_exec_status": by_status,
        "by_review_result": by_review,
        "top_failed_commands": top_failed
    }
