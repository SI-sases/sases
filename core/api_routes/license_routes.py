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
from .. import node_identity as ni

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
    ed25519_pubkey: str | None = None
    wg_pubkey: str | None = None


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
        if row["status"] == "banned":
            raise HTTPException(status_code=400, detail="卡密已被封禁")
        if row["status"] not in ("unused", "active", "used"):
            raise HTTPException(status_code=400, detail=f"卡密状态异常: {row['status']}")

        # 一次性卡密：先看该卡是否已经绑定过设备
        cur.execute(
            "SELECT user_id, device_fingerprint, expire_at FROM device_bindings WHERE license_key=? LIMIT 1",
            (req.key_code,),
        )
        bind = cur.fetchone()
        if bind:
            same_device = (int(bind["user_id"]) == int(req.user_id)
                           and str(bind["device_fingerprint"]) == str(req.device_fingerprint))
            if not same_device:
                raise HTTPException(status_code=400, detail="卡密已激活（一次性），不能绑定其他设备或账号")
            # 同一设备重装客户端：允许补发，沿用原到期时间
            expire_at = bind["expire_at"] or (now + timedelta(days=row["duration_days"])).isoformat()
        else:
            if row["status"] == "used":
                raise HTTPException(status_code=400, detail="卡密已使用，无法再次激活")
            expire_at = (now + timedelta(days=row["duration_days"])).isoformat()

        # 覆盖绑定：同一 user+fp 只留一条
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
            "UPDATE license_keys SET status='used', used_at=?, used_by=?, device_fp=? WHERE key_code=?",
            (now.isoformat(), req.user_id, req.device_fingerprint, req.key_code),
        )

    sig = _sign_license(req.user_id, req.device_fingerprint, expire_at)

    license_json = {
        "user_id": req.user_id,
        "device_fp": req.device_fingerprint,
        "expire_at": expire_at,
        "key_code": req.key_code,
        "sig": sig,
    }

    node_identity = None
    if req.ed25519_pubkey:
        try:
            node = ni.get_node_by_pubkey(req.ed25519_pubkey)
            if node and int(node["user_id"]) != int(req.user_id):
                raise HTTPException(status_code=409, detail="节点公钥已绑定其他账号")
            if not node:
                node = ni.get_node_by_device(req.user_id, req.device_fingerprint)
                if node:
                    if node.get("status") != "active":
                        raise HTTPException(status_code=403, detail="设备节点已被吊销")
                    ni.update_node_pubkey(node["node_id"], req.ed25519_pubkey)
                else:
                    node = ni.create_node(
                        user_id=req.user_id,
                        profile=ni.PROFILE_EDGE,
                        ed25519_pubkey=req.ed25519_pubkey,
                        wg_pubkey=req.wg_pubkey,
                        device_fingerprint=req.device_fingerprint,
                    )
            if req.wg_pubkey:
                ni.bind_node_wg(node["node_id"], req.wg_pubkey, req.device_fingerprint)
            manifest = ni.issue_manifest(node["node_id"], ttl_minutes=10080)
            node_identity = {
                "node_id": node["node_id"],
                "profile": node["profile"],
                "manifest": manifest,
                "issuer_public_key": ni.issuer_public_key(),
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"节点身份创建失败: {exc}") from exc

    return {"status": "ok", "license_json": license_json, "node_identity": node_identity}


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