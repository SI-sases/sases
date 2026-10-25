import os
import sys
import pytest

# 确保可以导入 core 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import auth
from core import db

@pytest.fixture
def temp_db(tmp_path):
    """使用临时数据库，避免污染真实 users.db"""
    db_file = tmp_path / "test_users.db"
    # 修改 core.db 使用的数据库路径
    db.DB_FILE = str(db_file)
    # 重新初始化数据库
    db.init_db()
    return auth

def test_create_user_and_initial_state(temp_db):
    success, msg = auth.create_user("alice", "alice@example.com", "password123")
    assert success is True
    user = auth.authenticate_user("alice", "password123")
    assert user is not None
    assert user["credits"] == 0
    assert auth.verify_user_integrity(user["id"]) is True

def test_add_credits_updates_balance_and_signature(temp_db):
    auth.create_user("bob", "bob@example.com", "password123")
    user = auth.authenticate_user("bob", "password123")
    uid = user["id"]

    auth.add_credits(uid, 30, "首次配置本地模型")
    user_after = auth.get_user_by_id(uid)
    assert user_after["credits"] == 30
    assert auth.verify_user_integrity(uid) is True

    ledger = auth.get_credit_ledger(uid)
    assert len(ledger) == 1
    assert ledger[0]["amount"] == 30
    assert ledger[0]["reason"] == "首次配置本地模型"

def test_deduct_credits_fails_when_insufficient(temp_db):
    auth.create_user("charlie", "charlie@example.com", "password123")
    user = auth.authenticate_user("charlie", "password123")
    uid = user["id"]

    success, msg = auth.deduct_credits(uid, 2, "仅查询不回流")
    assert success is False
    assert "积分不足" in msg
    assert auth.get_user_by_id(uid)["credits"] == 0

def test_deduct_credits_success_and_signature(temp_db):
    auth.create_user("dave", "dave@example.com", "password123")
    user = auth.authenticate_user("dave", "password123")
    uid = user["id"]
    auth.add_credits(uid, 10, "测试")

    success, msg = auth.deduct_credits(uid, 3, "仅查询不回流")
    assert success is True
    user_after = auth.get_user_by_id(uid)
    assert user_after["credits"] == 7
    assert auth.verify_user_integrity(uid) is True

def test_tamper_detection(temp_db):
    auth.create_user("eve", "eve@example.com", "password123")
    user = auth.authenticate_user("eve", "password123")
    uid = user["id"]

    import sqlite3
    conn = sqlite3.connect(db.DB_FILE)
    conn.execute("UPDATE users SET credits = 9999 WHERE id = ?", (uid,))
    conn.commit()
    conn.close()

    assert auth.verify_user_integrity(uid) is False
    tampered_ids = auth.check_all_users_integrity()
    assert uid in tampered_ids

def test_state_signature_functions(temp_db):
    uid = 123
    credits = 500
    sig = auth.sign_state(uid, credits)
    assert auth.verify_state(uid, credits, sig) is True
    assert auth.verify_state(uid, 501, sig) is False
