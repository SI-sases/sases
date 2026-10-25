# core/api_routes/market_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import market_service

router = APIRouter(prefix="/market", tags=["market"])
security = HTTPBearer()


class OrderCreateRequest(BaseModel):
    order_type: str   # buy_compute 或 sell_compute
    description: str
    price: float


class OrderAcceptRequest(BaseModel):
    order_id: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/orders")
async def list_orders(status: Optional[str] = None, user_id: int = Depends(get_current_user)):
    orders = market_service.list_orders(status=status)
    return {"orders": orders}


@router.post("/orders")
async def create_order(body: OrderCreateRequest, user_id: int = Depends(get_current_user)):
    if body.price <= 0:
        raise HTTPException(status_code=400, detail="价格必须大于0")
    if body.order_type not in ("buy_compute", "sell_compute"):
        raise HTTPException(status_code=400, detail="订单类型仅支持买算力或卖算力")
    try:
        order_id = market_service.create_order(user_id, body.order_type, body.description, body.price)
        return {"order_id": order_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/accept")
async def accept_order(body: OrderAcceptRequest, user_id: int = Depends(get_current_user)):
    try:
        result = market_service.accept_order(user_id, body.order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
