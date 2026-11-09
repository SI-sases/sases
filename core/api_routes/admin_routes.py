from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.security import get_current_user
from core.db import db_cursor
import random
import string
from datetime import datetime

router = APIRouter()

class GenerateKeysRequest(BaseModel):
    count: int
    key_type: str
    days: int

def generate_key():
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    return f"SASES-{parts[0]}-{parts[1]}-{parts[2]}"

@router.post("/admin/generate_keys")
def generate_keys(req: GenerateKeysRequest, current_user: dict = Depends(get_current_user)):
    # 1. 校验管理员权限
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="权限不足：只有系统管理员可以发卡")

    if req.count <= 0 or req.count > 1000:
        raise HTTPException(status_code=400, detail="单次发卡数量需在 1-1000 之间")

    keys = []
    with db_cursor(commit=True) as cur:
        for _ in range(req.count):
            k = generate_key()
            # 简单防重（极小概率重复）
            while True:
                cur.execute("SELECT 1 FROM license_keys WHERE key_code=?", (k,))
                if not cur.fetchone():
                    break
                k = generate_key()
            
            keys.append(k)
            cur.execute(
                "INSERT INTO license_keys (key_code, key_type, duration_days, status, created_at) VALUES (?, ?, ?, 'unused', ?)",
                (k, req.key_type, req.days, datetime.now().isoformat())
            )

    return {"status": "success", "count": len(keys), "keys": keys}