# core/api_routes/agent_question_routes.py
# -*- coding: utf-8 -*-
"""ask_user v2：回答后继续同一个 run。"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from ..auth_service import SECRET_KEY
from ..db import db_cursor
from ..services import agent_question_service, agent_memory, execution_gateway

router = APIRouter(prefix="/agent/questions", tags=["agent-questions"])
security = HTTPBearer()


class AnswerBody(BaseModel):
    answer: str


def _uid(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return int(jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"]).get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/{question_id}/answer")
async def answer_question(question_id: int, body: AnswerBody, user_id: int = Depends(_uid)):
    q = agent_question_service.get(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="question not found")
    if q.get("status") != "pending":
        raise HTTPException(status_code=400, detail="question already answered")
    cid = int(q["conversation_id"])
    if cid > 0:
        with db_cursor() as cur:
            cur.execute("SELECT user_id FROM conversations WHERE id=?", (cid,))
            row = cur.fetchone()
        if not row or int(row["user_id"]) != int(user_id):
            raise HTTPException(status_code=404, detail="conversation not found")

    agent_question_service.answer(question_id, body.answer)
    if cid < 0:
        try:
            gid = -cid
            with db_cursor(commit=True) as cur:
                cur.execute("INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)",
                            (gid, user_id, body.answer))
            agent_memory.append(cid, "user", body.answer)
        except Exception as e:
            print("[ask_user] 群回答落库失败: " + str(e))
    if q.get("run_id"):
        if cid > 0:
            with db_cursor(commit=True) as cur:
                cur.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                            (cid, body.answer))
                cur.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                            (datetime.now().isoformat(), cid))
            try:
                agent_memory.append(cid, "user", body.answer)
            except Exception:
                pass
            try:
                from .ws_routes import broadcast_to_user
                await broadcast_to_user(user_id, {
                    "type": "sases_new_message", "sender": "user",
                    "conversation_id": cid, "content": body.answer,
                })
            except Exception:
                pass
        asyncio.create_task(execution_gateway.resume_run(q["run_id"], body.answer))
        return {"status": "ok", "resumed": True}
    return {"status": "ok", "resumed": False}
