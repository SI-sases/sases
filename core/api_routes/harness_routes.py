# core/api_routes/harness_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import harness_service

router = APIRouter(prefix="/harness", tags=["harness"])
security = HTTPBearer()


class ExecuteRequest(BaseModel):
    module_id: str
    params: Dict[str, Any] = {}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/modules")
async def get_modules(user_id: int = Depends(get_current_user)):
    modules = harness_service.list_modules()
    return {"modules": modules}


@router.post("/execute")
async def execute(body: ExecuteRequest, user_id: int = Depends(get_current_user)):
    # ===== P0-E: /harness/execute 门禁（防未付费用户绕过 #1~#4 直调 API）=====
    try:
        from core.services.license_service import get_cached_exec_token, verify_exec_token
        _tok = get_cached_exec_token()
        if not verify_exec_token(_tok):
            raise HTTPException(status_code=403, detail="exec_token_invalid")
        import json as _j_lic
        try:
            _p = _j_lic.loads(_tok)["payload"]
            _tok_uid = int(_p.get("uid", -1))
        except Exception:
            raise HTTPException(status_code=403, detail="token_parse_error")
        try:
            if isinstance(user_id, dict):
                _req_uid = int(user_id.get("id") or user_id.get("user_id") or -1)
            else:
                _req_uid = int(user_id)
        except Exception:
            _req_uid = -1
        if _req_uid != _tok_uid:
            raise HTTPException(status_code=403, detail="token_user_mismatch")
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="license_service_missing")
    # ===== P0-E end =====
    try:
        result = harness_service.execute_module(body.module_id, body.params)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
