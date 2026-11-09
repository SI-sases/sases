from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..security import get_current_user
from ..db import db_cursor
import httpx

router = APIRouter(prefix="/api/user-api", tags=["User APIs"])

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
async def list_apis(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with db_cursor() as cur:
        cur.execute("SELECT id, api_name, api_desc, endpoint, method, auth_type, status FROM user_api_configs WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        return {"apis": [dict(r) for r in rows]}

@router.post("/add")
async def add_api(config: ApiConfigCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO user_api_configs 
            (user_id, api_name, api_desc, endpoint, method, auth_type, auth_key_encrypted, auth_header_name, params_example, response_path, capability_tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (user_id, config.api_name, config.api_desc, config.endpoint, config.method, config.auth_type, config.auth_key, config.auth_header_name, config.params_example, config.response_path, config.capability_tags))
    return {"status": "ok", "message": "API added"}

@router.delete("/{api_id}")
async def delete_api(api_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM user_api_configs WHERE id = ? AND user_id = ?", (api_id, user_id))
    return {"status": "ok"}

@router.post("/test")
async def test_api(endpoint: str):
    if "127.0.0.1" in endpoint or "localhost" in endpoint:
        raise HTTPException(status_code=400, detail="禁止调用内网地址")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(endpoint)
            return {"status": "ok", "code": resp.status_code, "preview": resp.text[:500]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
