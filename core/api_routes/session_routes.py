"""Session event read API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.auth_service import SECRET_KEY
from core.db import db_cursor
from core.services import session_event_service

router = APIRouter(prefix="/sessions", tags=["sessions"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


def _owns(user_id: int, conversation_id: int) -> bool:
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
        return cur.fetchone() is not None


@router.get("/{conversation_id}/events")
def events(
    conversation_id: int,
    after_seq: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    backfill: bool = Query(False),
    user_id: int = Depends(_user),
):
    if not _owns(user_id, conversation_id):
        raise HTTPException(status_code=404, detail="session not found")
    if backfill:
        session_event_service.backfill(conversation_id)
    return {
        "session_id": conversation_id,
        "latest_seq": session_event_service.latest_seq(conversation_id),
        "events": session_event_service.list_events(conversation_id, after_seq, limit),
    }
