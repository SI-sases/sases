from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
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
def generate_keys(req: GenerateKeysRequest):
    keys = []
    with db_cursor(commit=True) as cur:
        # 本地测试，暂不校验身份，直接发卡
        for _ in range(req.count):
            k = generate_key()
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
