# core/api_routes/rescue_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import rescue_service

router = APIRouter(prefix="/rescue", tags=["rescue"])
security = HTTPBearer()


class GenerateRequest(BaseModel):
    limit: int = 10


class AcceptRequest(BaseModel):
    task_id: int
    agent_id: Optional[str] = None


class AnalyzeRequest(BaseModel):
    task_id: int
    agent_id: Optional[str] = None
    previous_failure: Optional[str] = None


class VerifyRequest(BaseModel):
    task_id: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/generate")
async def generate_tasks(body: GenerateRequest, user_id: int = Depends(get_current_user)):
    """从质量保障层生成解救任务"""
    report = rescue_service.generate_rescue_tasks_from_issues(limit=body.limit)
    return report


@router.get("/tasks")
async def list_tasks(limit: int = 50, user_id: int = Depends(get_current_user)):
    """获取所有可接取的任务"""
    tasks = rescue_service.list_available_tasks(limit=limit)
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task(task_id: int, user_id: int = Depends(get_current_user)):
    """获取单个任务详情"""
    task = rescue_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/accept")
async def accept_task(body: AcceptRequest, user_id: int = Depends(get_current_user)):
    """接取任务"""
    result = rescue_service.accept_task(
        task_id=body.task_id,
        user_id=user_id,
        agent_id=body.agent_id
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/analyze")
async def analyze_task(body: AnalyzeRequest, user_id: int = Depends(get_current_user)):
    """智能体分析任务，生成方案（支持申诉重试）"""
    result = await rescue_service.analyze_task(
        task_id=body.task_id,
        user_id=user_id,
        agent_id=body.agent_id,
        previous_failure=body.previous_failure
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/verify")
async def verify_task(body: VerifyRequest, user_id: int = Depends(get_current_user)):
    """验证方案，完成解救"""
    result = await rescue_service.verify_and_complete(
        task_id=body.task_id,
        user_id=user_id
    )
    return result


@router.post("/abandon")
async def abandon_task(body: VerifyRequest, user_id: int = Depends(get_current_user)):
    """用户主动放弃任务"""
    result = rescue_service.abandon_task(body.task_id, user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/my-tasks")
async def my_tasks(limit: int = 50, user_id: int = Depends(get_current_user)):
    """获取我已完成/进行中的解救任务"""
    tasks = rescue_service.get_user_rescued_tasks(user_id=user_id, limit=limit)
    return {"tasks": tasks}


@router.get("/statistics")
async def statistics(user_id: int = Depends(get_current_user)):
    """解救任务统计"""
    return rescue_service.get_statistics()
