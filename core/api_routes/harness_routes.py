# core/api_routes/harness_routes.py
from fastapi import APIRouter
from ..services.license_service import get_cached_exec_token, verify_exec_token, Depends, HTTPException
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

    # ===== L3 执行层门禁 =====
    _tok = get_cached_exec_token()
    if not verify_exec_token(_tok):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="exec_token_invalid")
    # =======================

# ===== P0-E: /harness/execute 门禁（防未付费用户绕过 #1~#4 直调 API）=====
    try:
        result = harness_service.execute_module(body.module_id, body.params)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
