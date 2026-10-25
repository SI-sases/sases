# core/api_routes/seed_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import seed_service

router = APIRouter(prefix="/seeds", tags=["seeds"])
security = HTTPBearer()


class SeedCreateRequest(BaseModel):
    description: str
    domain: Optional[str] = None
    difficulty: str = "medium"


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/list")
async def list_seeds(user_id: int = Depends(get_current_user)):
    seeds = seed_service.list_seed_tasks(user_id)
    return {"seeds": seeds}


@router.post("/create")
async def create_seed(body: SeedCreateRequest, user_id: int = Depends(get_current_user)):
    task_id = seed_service.create_seed_task(
        description=body.description,
        domain=body.domain,
        difficulty=body.difficulty,
        user_id=user_id
    )
    return {"task_id": task_id, "status": "created"}


@router.get("/{task_id}")
async def get_seed(task_id: str, user_id: int = Depends(get_current_user)):
    seed = seed_service.get_seed_task(task_id)
    if not seed:
        raise HTTPException(status_code=404, detail="种子不存在")
    return seed
