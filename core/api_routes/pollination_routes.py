# core/api_routes/pollination_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import pollination_service

router = APIRouter(prefix="/pollination", tags=["pollination"])
security = HTTPBearer()


class PollinationSubmitRequest(BaseModel):
    task_description: str
    solution: str
    source: Optional[str] = "manual"


class FalsifySubmitRequest(BaseModel):
    result_id: str
    evidence: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/submit")
async def submit_pollination(body: PollinationSubmitRequest, user_id: int = Depends(get_current_user)):
    result = pollination_service.submit_pollination(
        user_id=user_id,
        task_description=body.task_description,
        solution=body.solution,
        source=body.source
    )
    return result


@router.post("/falsify")
async def submit_falsify(body: FalsifySubmitRequest, user_id: int = Depends(get_current_user)):
    result = pollination_service.submit_falsify(
        user_id=user_id,
        result_id=body.result_id,
        evidence=body.evidence
    )
    return result
