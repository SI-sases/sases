# fix.py
code = '''from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
import httpx

from ..auth_service import SECRET_KEY
from ..db import db_cursor

router = APIRouter(prefix="/api/user-api", tags=["User APIs"])
security = HTTPBearer()

# 手动解析 Token 获取用户 ID（完全兼容你现有的 transfer_routes.py）
def _get_uid(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

class ApiConfigCreate(BaseModel):
    api_name: str
    api_desc: Optional[str] = ""
    endpoint: str
    method: str = "GET"
    auth_type: str = "none"
    auth_key: Optional[str] = ""
    auth_header_name: str = "Authorization"
    params_example: Optional[str] = ""
    response_path: Optional[str] = ""
    capability_tags: Optional[str] = ""

@router.get("/list")
async def list_apis(uid: str = Depends(_get_uid)):
    with db_cursor() as cur:
        cur.execute("SELECT id, api_name, api_desc, endpoint, method, auth_type, status FROM user_api_configs WHERE user_id = ?", (uid,))
        rows = cur.fetchall()
        return {"apis": [dict(r) for r in rows]}

@router.post("/add")
async def add_api(config: ApiConfigCreate, uid: str = Depends(_get_uid)):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO user_api_configs 
            (user_id, api_name, api_desc, endpoint, method, auth_type, auth_key_encrypted, auth_header_name, params_example, response_path, capability_tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (uid, config.api_name, config.api_desc, config.endpoint, config.method, config.auth_type, config.auth_key, config.auth_header_name, config.params_example, config.response_path, config.capability_tags))
    return {"status": "ok", "message": "API added"}

@router.delete("/{api_id}")
async def delete_api(api_id: int, uid: str = Depends(_get_uid)):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM user_api_configs WHERE id = ? AND user_id = ?", (api_id, uid))
    return {"status": "ok"}

@router.post("/test")
async def test_api(endpoint: str, uid: str = Depends(_get_uid)):
    if "127.0.0.1" in endpoint or "localhost" in endpoint:
        raise HTTPException(status_code=400, detail="禁止调用内网地址")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(endpoint)
            return {"status": "ok", "code": resp.status_code, "preview": resp.text[:500]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
'''

with open('core/api_routes/user_api_routes.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("✅ user_api_routes.py 鉴权已完美修复！请重启服务！")
