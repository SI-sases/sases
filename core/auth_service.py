# core/auth_service.py
from .db import db_cursor
from .security import *
from .services.api_key_service import *

# ========== 用户管理 ==========
def create_user(username, password):
    password_hash = hash_password(password)
    sases_id = generate_sases_id()
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, sases_id) VALUES (?, ?, ?)",
                (username, password_hash, sases_id)
            )
            return cur.lastrowid
    except Exception:
        return None

def get_user_by_id(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT id, username, sases_id, credits FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None

def get_user_by_username(username):
    with db_cursor() as cur:
        cur.execute("SELECT id, username, password_hash, sases_id, credits FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None

def authenticate_user(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    if verify_password(password, user["password_hash"]):
        return user
    return None

def update_user_username(user_id, new_username):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET username=? WHERE id=?", (new_username, user_id))

def update_user_password(user_id, new_password):
    password_hash = hash_password(new_password)
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))

def delete_user(user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))

def update_user_credits(user_id, amount):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET credits = credits + ? WHERE id=?", (amount, user_id))

def add_credits(user_id, amount):
    return update_user_credits(user_id, amount)

def deduct_credits(user_id, amount):
    return update_user_credits(user_id, -amount)

def ensure_sases_id(user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        sases_id = row["sases_id"] if row else None
        if not sases_id:
            sases_id = generate_sases_id()
            cur.execute("UPDATE users SET sases_id=? WHERE id=?", (sases_id, user_id))
        return sases_id

# ========== 用户设置 ==========
def get_user_settings(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT id, username, sases_id, credits FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None

def update_user_settings(user_id, settings: dict):
    # 仅更新允许的字段
    allowed = ['username', 'sases_id']
    updates = {k: v for k, v in settings.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
    values = list(updates.values()) + [user_id]
    with db_cursor(commit=True) as cur:
        cur.execute(f"UPDATE users SET {set_clause} WHERE id=?", values)
    return True

def get_all_user_settings():
    with db_cursor() as cur:
        cur.execute("SELECT id, username, sases_id, credits FROM users")
        return [dict(row) for row in cur.fetchall()]

def update_all_user_settings(settings_map: dict):
    # settings_map: {user_id: {field: value, ...}}
    with db_cursor(commit=True) as cur:
        for user_id, settings in settings_map.items():
            for field, value in settings.items():
                if field in ['username', 'sases_id']:
                    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    return True

# ========== 排行榜 ==========
def get_leaderboard(limit=50):
    with db_cursor() as cur:
        cur.execute("SELECT username, sases_id, credits FROM users ORDER BY credits DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

# ========== 信用账本 ==========
def get_credit_ledger(user_id=None, limit=100):
    with db_cursor() as cur:
        if user_id:
            cur.execute("SELECT * FROM contribution_log WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
        else:
            cur.execute("SELECT * FROM contribution_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

# ========== 系统消息 ==========
def add_system_message(user_id, content):
    with db_cursor(commit=True) as cur:
        # 如果表不存在，先创建
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("INSERT INTO system_messages (user_id, content) VALUES (?, ?)", (user_id, content))
        return cur.lastrowid

def get_system_messages(user_id):
    with db_cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS system_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("SELECT * FROM system_messages WHERE user_id=? ORDER BY id DESC", (user_id,))
        return [dict(row) for row in cur.fetchall()]

def mark_messages_read(user_id, message_ids):
    if not message_ids:
        return
    with db_cursor(commit=True) as cur:
        for mid in message_ids:
            cur.execute("UPDATE system_messages SET is_read=1 WHERE id=? AND user_id=?", (mid, user_id))

# ========== 完整性校验 ==========
def verify_user_integrity(user_id):
    # 简单校验用户存在
    user = get_user_by_id(user_id)
    return user is not None

def check_all_users_integrity():
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        return {"total_users": cur.fetchone()["cnt"]}

# ========== 管理员 ==========
def is_admin(user_id):
    # 假设用户表中有 is_admin 字段，如果没有则默认用户 ID 1 为管理员
    with db_cursor() as cur:
        try:
            cur.execute("SELECT is_admin FROM users WHERE id=?", (user_id,))
            row = cur.fetchone()
            return bool(row["is_admin"]) if row else False
        except:
            return user_id == 1

def set_admin(user_id, admin_status):
    with db_cursor(commit=True) as cur:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except:
            pass
        cur.execute("UPDATE users SET is_admin=? WHERE id=?", (1 if admin_status else 0, user_id))

# ========== 知识库导出 ==========
def export_kb(user_id=None):
    with db_cursor() as cur:
        if user_id:
            cur.execute("SELECT * FROM knowledge_base WHERE user_id=? ORDER BY id DESC", (user_id,))
        else:
            cur.execute("SELECT * FROM knowledge_base ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]

# ========== 状态签名（兼容旧） ==========
generate_state_signature = sign_state
verify_state_signature = verify_state

def log_tamper_event(message):
    # 简单记录到日志文件
    with open("tamper.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")
