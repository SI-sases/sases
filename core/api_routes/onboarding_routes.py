# core/api_routes/onboarding_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
security = HTTPBearer()


class CompleteStepRequest(BaseModel):
    action: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/status")
async def get_status(user_id: int = Depends(get_current_user)):
    """获取当前新手引导状态"""
    return onboarding_service.get_user_onboarding(user_id)


@router.post("/complete-step")
async def complete_step(body: CompleteStepRequest, user_id: int = Depends(get_current_user)):
    """上报完成某个动作，系统会自动检查是否匹配当前引导任务"""
    if not body.action.strip():
        raise HTTPException(status_code=400, detail="action 不能为空")
    return onboarding_service.complete_onboarding_step(user_id, body.action.strip())


@router.post("/reset")
async def reset(user_id: int = Depends(get_current_user)):
    """重置引导（测试用）"""
    return onboarding_service.reset_onboarding(user_id)
