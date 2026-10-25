# core/services/api_key_service.py
from ..db import db_cursor

def add_api_key(user_id, provider, api_key_encrypted, priority=1):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO api_keys (user_id, provider, api_key_encrypted, priority)
            VALUES (?, ?, ?, ?)
        """, (user_id, provider, api_key_encrypted, priority))
        return cur.lastrowid

def list_api_keys(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM api_keys WHERE user_id=?", (user_id,))
        return [dict(row) for row in cur.fetchall()]

def delete_api_key(user_id, api_key_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (api_key_id, user_id))

def set_api_key_priority(user_id, api_key_id, priority):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE api_keys SET priority=? WHERE id=? AND user_id=?", (priority, api_key_id, user_id))

def get_active_api_keys(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM api_keys WHERE user_id=? AND is_active=1 ORDER BY priority", (user_id,))
        return [dict(row) for row in cur.fetchall()]
