# core/api_routes/model_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..db import db_cursor
from ..auth_service import SECRET_KEY
from ..services import model_service  # 导入 service

router = APIRouter(prefix="/models", tags=["models"])
security = HTTPBearer()

class AddApiKeyRequest(BaseModel):
    name: str
    provider: str
    api_key: str
    priority: int = 1

class AddLocalModelRequest(BaseModel):
    name: str
    node_url: str
    model_name: str
    capabilities: Optional[str] = None

class UpdateShareRequest(BaseModel):
    is_shared: int
    visibility: str
    price: float

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.post("/api-key")
async def add_api_key(body: AddApiKeyRequest, user_id: int = Depends(get_current_user)):
    model_id = model_service.create_api_key_model(
        user_id=user_id,
        name=body.name,
        provider=body.provider,
        api_key=body.api_key,
        priority=body.priority
    )
    return {"model_id": model_id, "name": body.name, "provider": body.provider}

@router.post("/local")
async def add_local_model(body: AddLocalModelRequest, user_id: int = Depends(get_current_user)):
    model_id = model_service.create_local_model(
        user_id=user_id,
        name=body.name,
        node_url=body.node_url,
        model_name=body.model_name,
        capabilities=body.capabilities
    )
    return {"model_id": model_id, "name": body.name, "model_name": body.model_name}

@router.get("/list")
async def list_models(user_id: int = Depends(get_current_user)):
    models = model_service.get_user_models(user_id)
    return {"models": models}

@router.patch("/{model_id}/share")
async def update_share_settings(model_id: str, body: UpdateShareRequest, user_id: int = Depends(get_current_user)):
    model_service.update_model_share(
        user_id=user_id,
        model_id=model_id,
        is_shared=body.is_shared,
        visibility=body.visibility,
        price=body.price
    )
    return {"status": "updated"}

@router.delete("/{model_id}")
async def delete_model(model_id: str, user_id: int = Depends(get_current_user)):
    model_service.delete_model(user_id, model_id)
    return {"status": "deleted"}
