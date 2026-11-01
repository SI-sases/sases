# -*- coding: utf-8 -*-
"""用户公开信息路由（只读）"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import db_cursor
from .auth_routes import get_current_user

router = APIRouter(tags=["user"])


@router.get("/u/{sases_id}")
async def get_user_card(sases_id: str):
    """公开名片页：根据 sases_id 返回用户名、handle、display_name。"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT sases_id, handle, display_name FROM users WHERE sases_id = ?",
            (sases_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "sases_id": row["sases_id"],
        "handle": row["handle"],
        "display_name": row["display_name"],
    }


# ================= 个人资料相关接口 =================

class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    gender: Optional[str] = None
    region: Optional[str] = None
    signature: Optional[str] = None

@router.get("/user/profile")
async def get_user_profile(user_id: int = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT id, username, sases_id, handle, display_name, gender, region, signature, credits FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        return dict(row)

@router.put("/user/profile")
async def update_user_profile(body: UpdateProfileRequest, user_id: int = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        if body.nickname is not None:
            cur.execute("UPDATE users SET display_name=? WHERE id=?", (body.nickname, user_id))
        if body.gender is not None:
            cur.execute("UPDATE users SET gender=? WHERE id=?", (body.gender, user_id))
        if body.region is not None:
            cur.execute("UPDATE users SET region=? WHERE id=?", (body.region, user_id))
        if body.signature is not None:
            cur.execute("UPDATE users SET signature=? WHERE id=?", (body.signature, user_id))
    return {"status": "updated"}
