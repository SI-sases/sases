# core/api_routes/transfer_routes.py
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..db import db_cursor
from ..services import transfer_service

router = APIRouter(prefix="/transfer", tags=["transfer"])

security = HTTPBearer()


class TransferRequest(BaseModel):
    receiver_id: str
    amount: float
    message: Optional[str] = ""
    conversation_id: Optional[int] = None


class RedPacketRequest(BaseModel):
    receiver_id: str
    amount: float
    message: Optional[str] = ""
    expire_hours: Optional[int] = 24
    conversation_id: Optional[int] = None


class TxRequest(BaseModel):
    tx_id: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


def _resolve_receiver(receiver_id_str: str) -> int:
    """把 SASES ID 或数字 ID 解析为数据库 users.id"""
    receiver = (receiver_id_str or "").strip()
    if not receiver:
        raise HTTPException(status_code=400, detail="接收者不能为空")

    with db_cursor() as cur:
        if receiver.isdigit():
            cur.execute("SELECT id FROM users WHERE id=?", (int(receiver),))
        else:
            cur.execute("SELECT id FROM users WHERE sases_id=?", (receiver,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail=f"找不到用户: {receiver}")
    return row["id"]


@router.post("/transfer")
async def create_transfer(body: TransferRequest, user_id: int = Depends(get_current_user)):
    resolved_receiver = _resolve_receiver(body.receiver_id)
    if resolved_receiver == user_id:
        raise HTTPException(status_code=400, detail="不能转账给自己")

    tx_id, err = transfer_service.create_transfer(
        user_id, resolved_receiver, body.amount, body.message
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"tx_id": tx_id, "status": "completed"}


@router.post("/red-packet")
async def create_red_packet(body: RedPacketRequest, user_id: int = Depends(get_current_user)):
    resolved_receiver = _resolve_receiver(body.receiver_id)
    if resolved_receiver == user_id:
        raise HTTPException(status_code=400, detail="不能发红包给自己")

    tx_id, err = transfer_service.create_red_packet(
        user_id, resolved_receiver, body.amount, body.message, body.expire_hours
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    # 如果带了 conversation_id，往会话里插入一条红包消息
    if body.conversation_id:
        payload = {
            "tx_id": tx_id,
            "amount": body.amount,
            "message": body.message or "恭喜发财，大吉大利",
            "sender_id": user_id,
        }
        try:
            transfer_service.insert_message(
                conversation_id=body.conversation_id,
                sender="user",
                content="[RED_PACKET]:" + json.dumps(payload, ensure_ascii=False),
                sender_agent_id=None
            )
        except Exception as e:
            print(f"[transfer] 插入红包消息失败: {e}")

    return {"tx_id": tx_id, "status": "pending", "expire_hours": body.expire_hours}


@router.get("/pending")
async def get_pending_red_packets(user_id: int = Depends(get_current_user)):
    packets = transfer_service.get_pending_transfers(user_id)
    return {"packets": packets}


@router.post("/claim")
async def claim_red_packet(body: TxRequest, user_id: int = Depends(get_current_user)):
    ok, err = transfer_service.claim_red_packet(body.tx_id, user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=err or "领取失败")
    return {"status": "claimed"}


@router.get("/history")
async def get_history(limit: int = 50, user_id: int = Depends(get_current_user)):
    history = transfer_service.get_transaction_history(user_id, limit)
    return {"history": history}


@router.get("/detail/{tx_id}")
async def get_tx_detail(tx_id: int, user_id: int = Depends(get_current_user)):
    """查询红包详情（供领取页面显示发送者、金额等）"""
    tx = transfer_service.get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="红包不存在")
    if tx["sender_id"] != user_id and tx["receiver_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权查看")
    return {
        "tx_id": tx["id"],
        "sender_id": tx["sender_id"],
        "receiver_id": tx["receiver_id"],
        "amount": tx["amount"],
        "message": tx["message"],
        "status": tx["status"],
        "tx_type": tx["tx_type"],
        "created_at": tx["created_at"],
    }

@router.get("/red_packet/sent")
async def get_sent_red_packets(user_id: int = Depends(get_current_user)):
    """查询当前用户已发送的红包记录"""
    return {'records': transfer_service.get_sent_red_packets(user_id)}
