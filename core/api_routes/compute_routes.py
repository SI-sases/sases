# core/api_routes/compute_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import compute_service

router = APIRouter(prefix="/compute", tags=["compute"])
security = HTTPBearer()


class RechargeRequest(BaseModel):
    package: int  # 充值套餐金额（10/50/100）
    payment_method: Optional[str] = "mock"  # 支付方式（当前为模拟）


class ExchangeRequest(BaseModel):
    credits_amount: int


class ConsumeRequest(BaseModel):
    service_key: str
    detail: Optional[str] = ""


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
    """获取算力余额"""
    return compute_service.get_balance_detail(user_id)


@router.get("/services")
async def list_services(user_id: int = Depends(get_current_user)):
    """列出所有官方算力服务"""
    services = compute_service.list_services()
    return {"services": services}


@router.get("/pricing")
async def get_pricing(user_id: int = Depends(get_current_user)):
    """获取算力定价信息"""
    return compute_service.get_pricing_info()


@router.post("/recharge")
async def recharge(body: RechargeRequest, user_id: int = Depends(get_current_user)):
    """
    充值算力（当前为模拟支付）。
    前端调用后直接到账，接入真实支付后再替换。
    """
    packages = {10: 100, 50: 720, 100: 2250}
    if body.package not in packages:
        raise HTTPException(status_code=400, detail="无效的充值套餐")

    compute_amount = packages[body.package]
    result = compute_service.add_compute(
        user_id=user_id,
        amount=compute_amount,
        detail=f"充值 ¥{body.package} 获得 {compute_amount} 算力"
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return {
        "success": True,
        "paid": body.package,
        "compute_gained": compute_amount,
        "balance": result["balance"],
        "message": f"充值成功，获得 {compute_amount} 算力"
    }


@router.post("/exchange")
async def exchange(body: ExchangeRequest, user_id: int = Depends(get_current_user)):
    """用种子积分兑换算力"""
    result = compute_service.exchange_credits_for_compute(user_id, body.credits_amount)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/consume")
async def consume(body: ConsumeRequest, user_id: int = Depends(get_current_user)):
    """扣减算力（消费官方服务）"""
    service = compute_service.get_service(body.service_key)
    if not service:
        raise HTTPException(status_code=404, detail="服务不存在")

    result = compute_service.deduct_compute(
        user_id=user_id,
        amount=service["unit_cost"],
        service_key=body.service_key,
        detail=body.detail or f"使用 {service['service_name']}"
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return {
        "success": True,
        "service": service["service_name"],
        "consumed": result["amount"],
        "balance": result["balance"]
    }


@router.get("/transactions")
async def get_transactions(limit: int = 50, user_id: int = Depends(get_current_user)):
    """获取算力交易记录"""
    transactions = compute_service.get_transactions(user_id, limit)
    return {"transactions": transactions}
