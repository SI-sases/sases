"""License 激活与心跳
- POST /auth/license/activate  激活卡密，返回签名版 license.json
- GET  /auth/license/heartbeat 心跳（P1 用，暂保留）
"""
import os
import json
import base64
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta

from ..db import db_cursor

router = APIRouter(prefix="/auth/license", tags=["License"])

_PRIV_PATH = os.environ.get("SASES_LICENSE_PRIV", "/root/sases/keys/license_priv.pem")


def _sign_license(user_id: int, device_fp: str, expire_at: str) -> str:
    """签 user_id|device_fp|expire_at（与 verify_license_json 的校验格式一致）"""
    from cryptography.hazmat.primitives import serialization
    with open(_PRIV_PATH, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    msg = f"{user_id}|{device_fp}|{expire_at}".encode("utf-8")
    return base64.b64encode(priv.sign(msg)).decode("utf-8")


class ActivateRequest(BaseModel):
    key_code: str
    device_fingerprint: str
    user_id: int


@router.post("/activate")
async def activate(req: ActivateRequest):
    now = datetime.utcnow()

    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT key_code, status, duration_days, banned_at FROM license_keys WHERE key_code=?",
            (req.key_code,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="卡密不存在")
        if row["banned_at"]:
            raise HTTPException(status_code=400, detail="卡密已被封禁")
        if row["status"] not in ("unused", "active"):
            raise HTTPException(status_code=400, detail=f"卡密状态异常: {row['status']}")

        expire_at = (now + timedelta(days=row["duration_days"])).isoformat()

        # 覆盖绑定：同一 user+fp 只留一条（支持重装客户端后重新激活）
        cur.execute(
            "DELETE FROM device_bindings WHERE user_id=? AND device_fingerprint=?",
            (req.user_id, req.device_fingerprint),
        )
        cur.execute(
            """
            INSERT INTO device_bindings
                (user_id, device_fingerprint, license_key, activated_at, expire_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (req.user_id, req.device_fingerprint, req.key_code, now.isoformat(), expire_at),
        )

        cur.execute(
            "UPDATE license_keys SET status='active' WHERE key_code=?",
            (req.key_code,),
        )

    sig = _sign_license(req.user_id, req.device_fingerprint, expire_at)

    license_json = {
        "user_id": req.user_id,
        "device_fp": req.device_fingerprint,
        "expire_at": expire_at,
        "key_code": req.key_code,
        "sig": sig,
    }

    return {"status": "ok", "license_json": license_json}


@router.get("/heartbeat")
async def heartbeat(user_id: int, device_fingerprint: str):
    with db_cursor() as cur:
        cur.execute(
            "SELECT expire_at FROM device_bindings WHERE user_id=? AND device_fingerprint=?",
            (user_id, device_fingerprint),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=403, detail="该设备未激活")
        if datetime.fromisoformat(row["expire_at"]) < datetime.utcnow():
            raise HTTPException(status_code=403, detail="授权已过期")
    return {"status": "ok"}