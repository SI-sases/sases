# core/api_routes/transfer_routes.py
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Union, Union
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
    credit_type: Optional[str] = "credits"


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


def _resolve_receiver(receiver: str):
    # 防止异常传参（如传入 None 或 空字符串）
    if not receiver:
        return None

    with db_cursor() as cur:
        # 1. 纯数字按 users.id 查
        if str(receiver).isdigit():
            cur.execute("SELECT id FROM users WHERE id=?", (int(receiver),))
            row = cur.fetchone()
            if row: return row["id"]

        # 2. 智能体 ID 映射到其所有者
        if str(receiver).startswith('sases_api_') or str(receiver).startswith('sases_assistant_'):
            cur.execute("SELECT user_id FROM model_configs WHERE id=?", (receiver,))
            row = cur.fetchone()
            if row: return row["user_id"]
            # 如果是系统虚拟助手，默认转给管理员或者报错
            return None

        # 3. sases_id 或 username 查
        cur.execute("SELECT id FROM users WHERE sases_id=? OR username=?", (receiver, receiver))
        row = cur.fetchone()
        return row["id"] if row else None
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

    _c_type = getattr(body, 'credit_type', 'credits')
    tx_id, err = transfer_service.create_transfer(user_id, resolved_receiver, body.amount, body.message, _c_type)
    if err:
        raise HTTPException(status_code=400, detail=err)

    # 【新增】跨端投递给 B（接收方）
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM conversations WHERE (user_id=? AND target_user_id=?) OR (user_id=? AND target_user_id=?)", (resolved_receiver, user_id, user_id, resolved_receiver))
            row = cur.fetchone()
            if row:
                b_conv_id = row["id"]
                payload = {"tx_id": tx_id, "amount": body.amount, "credit_type": _c_type, "message": body.message or "转账"}
                content = "[TRANSFER]:" + json.dumps(payload, ensure_ascii=False)
                now = datetime.now().isoformat()
                cur.execute("INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, 'user', ?, ?)", (b_conv_id, content, now))
    except Exception as e:
        print("跨端转账投递失败:", e)
    if body.conversation_id:
        try:
            import json
            payload = {"tx_id": tx_id, "amount": body.amount, "credit_type": body.credit_type, "message": body.message or "转账"}
            transfer_service.insert_message(body.conversation_id, sender="user", content="[TRANSFER]:" + json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            print("插入转账气泡失败:", e)

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
