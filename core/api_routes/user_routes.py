from fastapi import APIRouter, HTTPException
from core.db import get_conn

router = APIRouter()


@router.get("/u/{sases_id}")
def get_user_card(sases_id: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sases_id, handle, display_name FROM users WHERE sases_id = ?",
            (sases_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "sases_id": row[0],
        "handle": row[1],
        "display_name": row[2],
    }
