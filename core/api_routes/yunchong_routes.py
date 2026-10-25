# core/api_routes/yunchong_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import yunchong_service, rescue_service

router = APIRouter(prefix="/yunchong", tags=["yunchong"])
security = HTTPBearer()


class TaskAcceptRequest(BaseModel):
    task_id: int


class TaskAnalyzeRequest(BaseModel):
    task_id: int
    agent_id: Optional[str] = None
    previous_failure: Optional[str] = None
    use_official: bool = True


class TaskVerifyRequest(BaseModel):
    task_id: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


# ========== 地图与刷新 ==========
@router.get("/tasks")
async def list_tasks(user_id: int = Depends(get_current_user)):
    """获取当前批次的地图任务，需要时自动刷新"""
    tasks = yunchong_service.list_user_tasks(user_id)
    return {"tasks": tasks}


@router.get("/refresh-info")
async def get_refresh_info(user_id: int = Depends(get_current_user)):
    """获取刷新倒计时信息"""
    return yunchong_service.get_refresh_info(user_id)


@router.post("/refresh")
async def manual_refresh(user_id: int = Depends(get_current_user)):
    """手动刷新任务批次"""
    result = yunchong_service.refresh_user_tasks(user_id)
    return result


# ========== 任务详情 ==========
@router.get("/tasks/{task_id}")
async def get_task(task_id: int, user_id: int = Depends(get_current_user)):
    """获取任务详情"""
    task = yunchong_service.get_task_with_issue(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["owner_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权查看该任务")
    return task


# ========== 接取与放弃 ==========
@router.post("/accept")
async def accept_task(body: TaskAcceptRequest, user_id: int = Depends(get_current_user)):
    """接取任务，扣除能量（种子积分）"""
    result = yunchong_service.accept_task(body.task_id, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/abandon")
async def abandon_task(body: TaskAcceptRequest, user_id: int = Depends(get_current_user)):
    """放弃任务"""
    result = yunchong_service.abandon_task(body.task_id, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ========== 官方助手计费 ==========
@router.get("/official-agent/usage")
async def get_official_agent_usage(user_id: int = Depends(get_current_user)):
    """查询官方助手使用情况"""
    return yunchong_service.check_official_agent_usage(user_id)


# ========== 分析（调用智能体） ==========
@router.post("/analyze")
async def analyze_task(body: TaskAnalyzeRequest, user_id: int = Depends(get_current_user)):
    """分析任务，生成方案"""
    task = yunchong_service.get_task(body.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["owner_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作该任务")

    # 如果使用官方助手，扣费
    if body.use_official and not body.agent_id:
        usage = yunchong_service.consume_official_agent(user_id)
        if not usage.get("success"):
            raise HTTPException(status_code=402, detail=usage.get("message"))

    # 复用 rescue_service 的分析逻辑
    try:
        result = await rescue_service.analyze_task(
            task_id=body.task_id,
            user_id=user_id,
            agent_id=body.agent_id,
            previous_failure=body.previous_failure,
            task_source="yunchong"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    result["official_agent_usage"] = usage if (body.use_official and not body.agent_id) else None
    return result


# ========== 验证与完成 ==========
@router.post("/verify")
async def verify_task(body: TaskVerifyRequest, user_id: int = Depends(get_current_user)):
    """验证方案，完成解救"""
    task = yunchong_service.get_task(body.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["owner_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作该任务")

    result = await rescue_service.verify_and_complete(
        task_id=body.task_id,
        user_id=user_id,
        task_source="yunchong"
    )
    return result


# ========== 我的任务历史 ==========
@router.get("/my-tasks")
async def my_tasks(limit: int = 50, user_id: int = Depends(get_current_user)):
    """获取我已完成/进行中的任务"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, title, pet_level, status, distance_meters,
                   energy_cost, rescued_at, attempts, created_at
            FROM yunchong_tasks
            WHERE owner_user_id=? AND status IN ('rescued', 'in_progress')
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
    return {"tasks": [dict(row) for row in rows]}


# 需要引入 db_cursor
from ..db import db_cursor
