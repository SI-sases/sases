# -*- coding: utf-8 -*-
"""用户公开信息路由（只读）"""
from fastapi import APIRouter, HTTPException
from ..db import db_cursor

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
