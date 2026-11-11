from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..db import db_cursor
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/auth/license", tags=["License"])

class ActivateRequest(BaseModel):
    key_code: str
    device_fingerprint: str
    user_id: int

@router.post("/activate")
async def activate(req: ActivateRequest):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT status, duration_days FROM license_keys WHERE key_code=?", (req.key_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="卡密不存在")
        if row['status'] != 'unused':
            raise HTTPException(status_code=400, detail="卡密已被使用或已封禁")
        
        expire_at = (datetime.now() + timedelta(days=row['duration_days'])).isoformat()
        
        cur.execute("INSERT OR REPLACE INTO device_bindings (user_id, device_fingerprint, activated_at, expire_at) VALUES (?, ?, ?, ?)",
                    (req.user_id, req.device_fingerprint, datetime.now().isoformat(), expire_at))
        
        cur.execute("UPDATE license_keys SET status='active' WHERE key_code=?", (req.key_code,))
        
    return {"status": "ok", "expire_at": expire_at, "token": str(uuid.uuid4())}

@router.get("/heartbeat")
async def heartbeat(user_id: int, device_fingerprint: str):
    with db_cursor() as cur:
        cur.execute("SELECT expire_at FROM device_bindings WHERE user_id=? AND device_fingerprint=?", (user_id, device_fingerprint))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=403, detail="该设备未激活，请购买卡密")
        if datetime.fromisoformat(row['expire_at']) < datetime.now():
            raise HTTPException(status_code=403, detail="授权已过期")
    return {"status": "ok"}
