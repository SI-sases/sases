import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.db as db

@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_users.db"
    monkeypatch.setattr(db, "DB_FILE", str(db_file))
    db.init_db()

    from core.auth_service import create_user
    create_user("admin", "admin@example.com", "password123")
    create_user("testuser", "test@example.com", "password123")

    from app_full import app
    client = TestClient(app)
    return client

def get_token(client, username, password):
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_register_and_login(client):
    res = client.post("/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "pass123"
    })
    assert res.status_code == 200
    token = get_token(client, "newuser", "pass123")
    assert token

def test_chat_endpoint(client):
    token = get_token(client, "testuser", "password123")
    from core.knowledge_base import add_to_kb
    tasks = [
        "写一个函数判断素数",
        "写一个函数计算两个数的最大公约数",
        "写一个函数反转字符串",
        "写一个函数统计列表中元素个数",
    ]
    for task in tasks:
        add_to_kb(task=task, branch_a="", branch_b="", synthesis="def func(): pass", user_id="testuser")

    res = client.post("/chat", json={"query": "写一个函数判断素数"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data

def test_submit_seed(client):
    token = get_token(client, "testuser", "password123")
    res = client.post("/submit_seed", json={
        "description": "写一个Python函数，判断一个整数是否为偶数",
        "test_cases": [{"input": 4, "expected_output": True}]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    from core.seed_store import list_external_seeds
    seeds = list_external_seeds()
    assert any(seed["description"] == "写一个Python函数，判断一个整数是否为偶数" for seed in seeds)

def test_api_key_crud(client):
    token = get_token(client, "testuser", "password123")
    res = client.post("/api_keys", json={"provider": "deepseek", "key": "sk-test123456", "priority": 1}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    res = client.get("/api_keys", headers={"Authorization": f"Bearer {token}"})
    keys = res.json()
    assert len(keys) == 1
    assert keys[0]["provider"] == "deepseek"
    assert keys[0]["priority"] == 1
    key_id = keys[0]["id"]
    res = client.patch("/api_keys/priority", json={"key_id": key_id, "priority": 2}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    res = client.delete(f"/api_keys/{key_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    keys = client.get("/api_keys", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(keys) == 0

def test_space_nodes_and_invoke(client):
    token = get_token(client, "testuser", "password123")
    # 检查节点列表
    res = client.get("/space/nodes")
    assert res.status_code == 200
    nodes = res.json()
    assert isinstance(nodes, list)
    # 调用一个不存在的节点，接口本身应返回 200（内部 success 可能为 false）
    res = client.post("/space/invoke", json={"node_id": "nonexistent-node", "params": {}}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "success" in data

def test_leaderboard_and_contrib(client):
    res = client.get("/leaderboard")
    assert res.status_code == 200
    res = client.get("/contrib_leaderboard")
    assert res.status_code == 200
