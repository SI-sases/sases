"""云端付费墙授权校验接口
- POST /auth/check_exec  执行前 5 分钟 token 签发
- 真实 schema：license_keys（无 expire_at）+ device_bindings（有 expire_at, license_key）
"""
import os
import json
import time
import base64
from typing import Optional
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

try:
    from ..db import db_cursor
except ImportError:
    from core.db import db_cursor

router = APIRouter()

# ---------- 私钥懒加载 ----------
_PRIV_PATH = os.environ.get(
    "SASES_LICENSE_PRIV",
    "/root/sases/keys/license_priv.pem",
)
_priv_key = None


def _load_priv():
    global _priv_key
    if _priv_key is not None:
        return _priv_key
    from cryptography.hazmat.primitives import serialization
    with open(_PRIV_PATH, "rb") as f:
        _priv_key = serialization.load_pem_private_key(f.read(), password=None)
    return _priv_key


def _sign(payload: dict) -> str:
    """JWT-like 签名：{payload: {...}, sig: base64}"""
    msg = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig = _load_priv().sign(msg)
    return json.dumps(
        {"payload": payload, "sig": base64.b64encode(sig).decode("utf-8")},
        sort_keys=True,
    )


class CheckExecReq(BaseModel):
    user_id: int
    device_fp: str
    task_hash: Optional[str] = None


@router.post("/auth/check_exec")
def check_exec(req: CheckExecReq):
    now = datetime.utcnow()

    # ---------- 1. free_mode 检查 ----------
    try:
        with db_cursor(commit=False) as cur:
            cur.execute("SELECT value FROM system_config WHERE key='free_mode'")
            r = cur.fetchone()
            free_mode = bool(r and r["value"] == "1")
    except Exception:
        free_mode = False

    if free_mode:
        expire = int(time.time()) + 300
        return {
            "allowed": True,
            "token": _sign({"uid": req.user_id, "exp": expire, "fp": req.device_fp}),
            "expire_at": expire,
            "reason": "free_mode",
        }

    # ---------- 2. 查绑定 + 查卡密 ----------
    binding = None
    license_row = None
    try:
        with db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT expire_at, license_key
                FROM device_bindings
                WHERE user_id = ? AND device_fingerprint = ?
                LIMIT 1
                """,
                (req.user_id, req.device_fp),
            )
            binding = cur.fetchone()

            if binding and binding["license_key"]:
                cur.execute(
                    """
                    SELECT key_code, status, banned_at
                    FROM license_keys
                    WHERE key_code = ?
                    LIMIT 1
                    """,
                    (binding["license_key"],),
                )
                license_row = cur.fetchone()
    except Exception as e:
        return {"allowed": False, "reason": f"db_error:{e}"}

    # ---------- 3. 判定 ----------
    allowed = False
    reason = ""

    if not binding:
        reason = "no_binding"
    elif binding["expire_at"] and binding["expire_at"] < now.isoformat():
        reason = "expired"
    elif license_row is None:
        reason = "no_license"
    else:
        try:
            banned = license_row["banned_at"]
        except (KeyError, IndexError):
            banned = None
        if banned:
            reason = "banned"
        elif license_row["status"] != "active":
            reason = f"inactive:{license_row['status']}"
        else:
            allowed = True
            reason = "ok"

    # ---------- 4. 审计 ----------
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO exec_audit
                    (user_id, device_fp, task_hash, allowed, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    req.user_id,
                    req.device_fp,
                    req.task_hash,
                    1 if allowed else 0,
                    reason,
                    now.isoformat(),
                ),
            )
    except Exception:
        pass

    if not allowed:
        return {"allowed": False, "reason": reason}

    expire = int(time.time()) + 300
    return {
        "allowed": True,
        "token": _sign({"uid": req.user_id, "exp": expire, "fp": req.device_fp}),
        "expire_at": expire,
        "reason": "ok",
    }