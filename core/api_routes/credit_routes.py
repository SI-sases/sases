# core/api_routes/credit_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import credit_service

router = APIRouter(prefix="/credits", tags=["credits"])
security = HTTPBearer()


class ExchangeRequest(BaseModel):
    credits: float


class StakeRequest(BaseModel):
    credits: float
    duration_days: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/balance")
async def get_balance(user_id: int = Depends(get_current_user)):
    balance = credit_service.get_balance(user_id)
    if balance is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"balance": balance}


@router.get("/history")
async def get_history(limit: int = 50, user_id: int = Depends(get_current_user)):
    history = credit_service.get_history(user_id, limit)
    return {"history": history}


@router.post("/exchange")
async def exchange_credits(body: ExchangeRequest, user_id: int = Depends(get_current_user)):
    credits = body.credits
    if credits <= 0:
        raise HTTPException(status_code=400, detail="积分数量必须大于0")
    # 规则：5积分 = 1算力
    compute_power = credits / 5.0
    success = credit_service.add_credit(user_id, -credits, "积分兑换算力", f"兑换 {compute_power} 算力")
    if not success:
        raise HTTPException(status_code=500, detail="兑换失败")
    return {"status": "success", "credits_spent": credits, "compute_power": compute_power}


@router.post("/stake")
async def stake_credits(body: StakeRequest, user_id: int = Depends(get_current_user)):
    credits = body.credits
    days = body.duration_days
    if credits <= 0:
        raise HTTPException(status_code=400, detail="积分数量必须大于0")
    # 简单计算收益（年化10%）
    reward = credits * (0.1 * days / 365.0)
    success = credit_service.add_credit(user_id, -credits, "积分质押", f"质押 {credits} 积分 {days} 天")
    if not success:
        raise HTTPException(status_code=500, detail="质押失败")
    return {"status": "success", "staked": credits, "duration_days": days, "expected_reward": reward}
